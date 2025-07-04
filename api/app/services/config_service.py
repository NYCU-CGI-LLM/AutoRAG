import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select, and_, or_

from app.models.config import Config, ConfigStatus
from app.models.parser import Parser
from app.models.chunker import Chunker
from app.models.indexer import Indexer
from app.models.retriever import Retriever, RetrieverStatus

logger = logging.getLogger(__name__)


class ConfigService:
    """Configuration management service"""
    
    def __init__(self):
        self.logger = logger

    def get_config_by_id(self, session: Session, config_id: UUID) -> Optional[Config]:
        """Get config by ID"""
        return session.get(Config, config_id)

    def get_active_configs(self, session: Session, limit: int = 50) -> List[Config]:
        """Get all active configurations"""
        statement = select(Config).where(Config.status == ConfigStatus.ACTIVE).limit(limit)
        return session.exec(statement).all()

    def get_or_create_config(
        self,
        session: Session,
        parser_id: UUID,
        chunker_id: UUID,
        indexer_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Config:
        """
        Get existing config for the component combination, or create new one
        
        Args:
            session: Database session
            parser_id: Parser UUID
            chunker_id: Chunker UUID  
            indexer_id: Indexer UUID
            name: Optional config name
            description: Optional config description
            params: Optional additional parameters
            
        Returns:
            Config object (existing or newly created)
        """
        # First try to find existing active config
        existing_config = self.find_config_by_components(
            session, parser_id, chunker_id, indexer_id
        )
        
        if existing_config:
            self.logger.info(f"Found existing config {existing_config.id} for components")
            return existing_config
        
        # Create new config if not found
        return self.create_config(
            session=session,
            parser_id=parser_id,
            chunker_id=chunker_id,
            indexer_id=indexer_id,
            name=name,
            description=description,
            params=params or {}
        )

    def find_config_by_components(
        self,
        session: Session,
        parser_id: UUID,
        chunker_id: UUID,
        indexer_id: UUID,
        status: ConfigStatus = ConfigStatus.ACTIVE
    ) -> Optional[Config]:
        """Find config by component combination"""
        statement = select(Config).where(
            and_(
                Config.parser_id == parser_id,
                Config.chunker_id == chunker_id,
                Config.indexer_id == indexer_id,
                Config.status == status
            )
        )
        return session.exec(statement).first()

    def create_config(
        self,
        session: Session,
        parser_id: UUID,
        chunker_id: UUID,
        indexer_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Config:
        """
        Create a new configuration
        
        Args:
            session: Database session
            parser_id: Parser UUID
            chunker_id: Chunker UUID
            indexer_id: Indexer UUID
            name: Optional config name
            description: Optional config description
            params: Optional additional parameters
            
        Returns:
            Created Config object
        """
        # Validate that components exist
        parser = session.get(Parser, parser_id)
        if not parser:
            raise ValueError(f"Parser {parser_id} not found")
        
        chunker = session.get(Chunker, chunker_id)
        if not chunker:
            raise ValueError(f"Chunker {chunker_id} not found")
        
        indexer = session.get(Indexer, indexer_id)
        if not indexer:
            raise ValueError(f"Indexer {indexer_id} not found")

        # Generate default name if not provided
        if not name:
            name = f"{parser.name}+{chunker.name}+{indexer.name}"

        # Check for duplicate config with same component combination
        existing = self.find_config_by_components(
            session, parser_id, chunker_id, indexer_id
        )
        if existing:
            raise ValueError(f"Config with same component combination already exists: {existing.id}")

        # Create new config
        config = Config(
            parser_id=parser_id,
            chunker_id=chunker_id,
            indexer_id=indexer_id,
            name=name,
            description=description,
            params=params or {},
            status=ConfigStatus.ACTIVE
        )
        
        session.add(config)
        session.commit()
        session.refresh(config)
        
        self.logger.info(f"Created new config {config.id}: {name}")
        return config

    def get_config_detail(self, session: Session, config_id: UUID) -> Dict[str, Any]:
        """Get detailed config information including component details"""
        config = self.get_config_by_id(session, config_id)
        if not config:
            raise ValueError(f"Config {config_id} not found")

        # Get component details
        parser = session.get(Parser, config.parser_id)
        chunker = session.get(Chunker, config.chunker_id)
        indexer = session.get(Indexer, config.indexer_id)

        # Get usage statistics
        usage_stats = self.get_config_usage_stats(session, config_id)

        return {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "status": config.status.value,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
            "params": config.params,
            "parser_info": {
                "id": str(parser.id),
                "name": parser.name,
                "type": parser.module_type,
                "params": parser.params,
                "status": parser.status.value
            } if parser else None,
            "chunker_info": {
                "id": str(chunker.id),
                "name": chunker.name,
                "type": chunker.module_type,
                "params": chunker.params,
                "status": chunker.status.value
            } if chunker else None,
            "indexer_info": {
                "id": str(indexer.id),
                "name": indexer.name,
                "type": indexer.index_type,
                "params": indexer.params,
                "status": indexer.status.value
            } if indexer else None,
            "usage_stats": usage_stats
        }

    def get_config_usage_stats(self, session: Session, config_id: UUID) -> Dict[str, Any]:
        """Get usage statistics for a config"""
        # Count retrievers using this config
        retriever_count_stmt = select(Retriever).where(Retriever.config_id == config_id)
        total_retrievers = len(session.exec(retriever_count_stmt).all())
        
        # Count active retrievers
        active_retriever_stmt = select(Retriever).where(
            and_(
                Retriever.config_id == config_id,
                Retriever.status == RetrieverStatus.ACTIVE
            )
        )
        active_retrievers = len(session.exec(active_retriever_stmt).all())

        # Get last used timestamp (latest usage time)
        last_used_stmt = select(Retriever.indexed_at).where(
            and_(
                Retriever.config_id == config_id,
                Retriever.indexed_at.isnot(None)
            )
        ).order_by(Retriever.indexed_at.desc()).limit(1)
        
        last_used_result = session.exec(last_used_stmt).first()
        last_used = last_used_result if last_used_result else None

        return {
            "total_retrievers": total_retrievers,
            "active_retrievers": active_retrievers,
            "last_used": last_used,
            "success_rate": (active_retrievers / total_retrievers * 100) if total_retrievers > 0 else 0.0
        }

    def update_config(
        self,
        session: Session,
        config_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        status: Optional[ConfigStatus] = None
    ) -> Config:
        """Update configuration"""
        config = self.get_config_by_id(session, config_id)
        if not config:
            raise ValueError(f"Config {config_id} not found")

        # Update fields if provided
        if name is not None:
            config.name = name
        if description is not None:
            config.description = description
        if params is not None:
            config.params = params
        if status is not None:
            config.status = status
        
        config.updated_at = datetime.utcnow()
        
        session.add(config)
        session.commit()
        session.refresh(config)
        
        return config

    def delete_config(self, session: Session, config_id: UUID) -> bool:
        """Delete configuration (soft delete by setting status to deprecated)"""
        config = self.get_config_by_id(session, config_id)
        if not config:
            return False

        # Check if any retrievers are using this config
        retriever_count_stmt = select(Retriever).where(Retriever.config_id == config_id)
        retrievers_using_config = session.exec(retriever_count_stmt).all()
        
        if retrievers_using_config:
            # Soft delete - mark as deprecated
            config.status = ConfigStatus.DEPRECATED
            config.updated_at = datetime.utcnow()
            session.add(config)
            session.commit()
            self.logger.info(f"Config {config_id} marked as deprecated (has {len(retrievers_using_config)} retrievers)")
        else:
            # Hard delete if no retrievers are using it
            session.delete(config)
            session.commit()
            self.logger.info(f"Config {config_id} deleted permanently")
        
        return True

    def list_configs(
        self,
        session: Session,
        status: Optional[ConfigStatus] = None,
        limit: int = 50
    ) -> List[Config]:
        """List configurations with optional filtering"""
        statement = select(Config)
        
        if status:
            statement = statement.where(Config.status == status)
        
        statement = statement.limit(limit)
        return session.exec(statement).all()

    def get_config_summaries(self, session: Session) -> List[Dict[str, Any]]:
        """Get config summaries with component names"""
        configs = self.get_active_configs(session)
        summaries = []
        
        for config in configs:
            parser = session.get(Parser, config.parser_id)
            chunker = session.get(Chunker, config.chunker_id)
            indexer = session.get(Indexer, config.indexer_id)
            
            # Count retrievers using this config
            retriever_count_stmt = select(Retriever).where(Retriever.config_id == config.id)
            retriever_count = len(session.exec(retriever_count_stmt).all())
            
            summaries.append({
                "id": config.id,
                "name": config.name,
                "status": config.status.value,
                "created_at": config.created_at,
                "parser_name": parser.name if parser else None,
                "chunker_name": chunker.name if chunker else None,
                "indexer_name": indexer.name if indexer else None,
                "retriever_count": retriever_count
            })
        
        return summaries 