import logging
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy import desc

from app.core.database import get_session
from app.models.library import Library as LibraryModel
from app.models.file import File as FileModel
from app.schemas.library import (
    Library, 
    LibraryCreate, 
    LibraryDetail, 
    LibraryStats,
    FileInfo
)
from app.services.minio_service import minio_service
from fastapi import HTTPException, Depends

logger = logging.getLogger(__name__)

class LibraryService:
    """Service for managing library data operations with PostgreSQL and MinIO"""
    
    def create_library(self, library_create: LibraryCreate, session: Session) -> Library:
        """Create a new library"""
        try:
            # Check if library name already exists
            statement = select(LibraryModel).where(LibraryModel.library_name == library_create.library_name)
            existing_library = session.exec(statement).first()
            
            if existing_library:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Library with name '{library_create.library_name}' already exists"
                )
            
            # Create new library without user_id for now (since user system isn't implemented)
            db_library = LibraryModel(
                library_name=library_create.library_name,
                description=library_create.description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(db_library)
            session.commit()
            session.refresh(db_library)
            
            logger.info(f"Created library: {library_create.library_name} (ID: {db_library.id})")
            
            # Convert to response schema
            return Library(
                id=db_library.id,
                library_name=db_library.library_name,
                description=db_library.description,
                created_at=db_library.created_at,
                updated_at=db_library.updated_at,
                stats=LibraryStats(file_count=0, total_size=0)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating library: {e}")
            raise HTTPException(status_code=500, detail="Failed to create library")
    
    def get_library(self, library_id: UUID, session: Session) -> Library:
        """Get a library by ID"""
        try:
            statement = select(LibraryModel).where(LibraryModel.id == library_id)
            db_library = session.exec(statement).first()
            
            if not db_library:
                raise HTTPException(
                    status_code=404,
                    detail=f"Library with ID {library_id} not found"
                )
            
            # Get file stats from database
            file_statement = select(FileModel).where(FileModel.library_id == library_id)
            db_files = session.exec(file_statement).all()
            
            # Get actual file sizes from MinIO
            minio_files = minio_service.list_library_files(library_id)
            total_size = sum(file["size"] for file in minio_files)
            
            return Library(
                id=db_library.id,
                library_name=db_library.library_name,
                description=db_library.description,
                created_at=db_library.created_at,
                updated_at=db_library.updated_at,
                stats=LibraryStats(file_count=len(db_files), total_size=total_size)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting library {library_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve library")
    
    def get_library_detail(self, library_id: UUID, session: Session) -> LibraryDetail:
        """Get detailed library information including files"""
        try:
            statement = select(LibraryModel).where(LibraryModel.id == library_id)
            db_library = session.exec(statement).first()
            
            if not db_library:
                raise HTTPException(
                    status_code=404,
                    detail=f"Library with ID {library_id} not found"
                )
            
            # Get files from database
            file_statement = select(FileModel).where(FileModel.library_id == library_id)
            db_files = session.exec(file_statement).all()
            
            # Get files from MinIO
            minio_files = minio_service.list_library_files(library_id)
            minio_file_map = {file["file_id"]: file for file in minio_files}
            
            # Combine database and MinIO information
            files = []
            total_size = 0
            
            for db_file in db_files:
                minio_file = minio_file_map.get(str(db_file.id))
                if minio_file:
                    file_info = FileInfo(
                        id=db_file.id,
                        file_name=db_file.file_name,
                        content_type=minio_file.get("content_type", "application/octet-stream"),
                        size=minio_file["size"],
                        upload_time=datetime.fromisoformat(minio_file["last_modified"]) if minio_file["last_modified"] else datetime.utcnow()
                    )
                    files.append(file_info)
                    total_size += minio_file["size"]
                else:
                    # File exists in DB but not in MinIO - create placeholder
                    file_info = FileInfo(
                        id=db_file.id,
                        file_name=db_file.file_name,
                        content_type="application/octet-stream",
                        size=0,
                        upload_time=datetime.utcnow()
                    )
                    files.append(file_info)
            
            return LibraryDetail(
                id=db_library.id,
                library_name=db_library.library_name,
                description=db_library.description,
                created_at=db_library.created_at,
                updated_at=db_library.updated_at,
                stats=LibraryStats(file_count=len(files), total_size=total_size),
                files=files
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting library detail {library_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve library details")
    
    def list_libraries(self, session: Session) -> List[Library]:
        """List all libraries"""
        try:
            statement = select(LibraryModel).order_by(desc(LibraryModel.created_at))
            db_libraries = session.exec(statement).all()
            
            libraries = []
            for db_library in db_libraries:
                # Get file count from database
                file_statement = select(FileModel).where(FileModel.library_id == db_library.id)
                db_files = session.exec(file_statement).all()
                
                # Get total size from MinIO
                try:
                    minio_files = minio_service.list_library_files(db_library.id)
                    total_size = sum(file["size"] for file in minio_files)
                except Exception as e:
                    logger.warning(f"Failed to get MinIO stats for library {db_library.id}: {e}")
                    total_size = 0
                
                library = Library(
                    id=db_library.id,
                    library_name=db_library.library_name,
                    description=db_library.description,
                    created_at=db_library.created_at,
                    updated_at=db_library.updated_at,
                    stats=LibraryStats(file_count=len(db_files), total_size=total_size)
                )
                libraries.append(library)
            
            return libraries
            
        except Exception as e:
            logger.error(f"Error listing libraries: {e}")
            raise HTTPException(status_code=500, detail="Failed to list libraries")
    
    def update_library(self, library_id: UUID, library_name: Optional[str] = None, description: Optional[str] = None, session: Session = None) -> Library:
        """Update library information"""
        try:
            statement = select(LibraryModel).where(LibraryModel.id == library_id)
            db_library = session.exec(statement).first()
            
            if not db_library:
                raise HTTPException(
                    status_code=404,
                    detail=f"Library with ID {library_id} not found"
                )
            
            # Check for name conflicts if name is being updated
            if library_name and library_name != db_library.library_name:
                name_check_statement = select(LibraryModel).where(
                    LibraryModel.library_name == library_name,
                    LibraryModel.id != library_id
                )
                existing_library = session.exec(name_check_statement).first()
                if existing_library:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Library with name '{library_name}' already exists"
                    )
            
            # Update fields
            if library_name is not None:
                db_library.library_name = library_name
            if description is not None:
                db_library.description = description
            
            db_library.updated_at = datetime.utcnow()
            
            session.add(db_library)
            session.commit()
            session.refresh(db_library)
            
            logger.info(f"Updated library {library_id}")
            
            # Get current stats
            file_statement = select(FileModel).where(FileModel.library_id == library_id)
            db_files = session.exec(file_statement).all()
            
            try:
                minio_files = minio_service.list_library_files(library_id)
                total_size = sum(file["size"] for file in minio_files)
            except Exception:
                total_size = 0
            
            return Library(
                id=db_library.id,
                library_name=db_library.library_name,
                description=db_library.description,
                created_at=db_library.created_at,
                updated_at=db_library.updated_at,
                stats=LibraryStats(file_count=len(db_files), total_size=total_size)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating library {library_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update library")
    
    def delete_library(self, library_id: UUID, session: Session) -> bool:
        """Delete a library and all its files"""
        try:
            statement = select(LibraryModel).where(LibraryModel.id == library_id)
            db_library = session.exec(statement).first()
            
            if not db_library:
                raise HTTPException(
                    status_code=404,
                    detail=f"Library with ID {library_id} not found"
                )
            
            # Delete all files from MinIO first
            try:
                minio_files = minio_service.list_library_files(library_id)
                for file_info in minio_files:
                    minio_service.delete_file(file_info["object_name"])
                logger.info(f"Deleted {len(minio_files)} files from MinIO for library {library_id}")
            except Exception as e:
                logger.warning(f"Error deleting files from MinIO for library {library_id}: {e}")
                # Continue with library deletion even if MinIO cleanup fails
            
            # Delete file records from database
            file_statement = select(FileModel).where(FileModel.library_id == library_id)
            db_files = session.exec(file_statement).all()
            for db_file in db_files:
                session.delete(db_file)
            
            # Delete library from database
            session.delete(db_library)
            session.commit()
            
            logger.info(f"Deleted library {library_id}")
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting library {library_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete library")
    
    def library_exists(self, library_id: UUID, session: Session) -> bool:
        """Check if a library exists"""
        try:
            statement = select(LibraryModel).where(LibraryModel.id == library_id)
            db_library = session.exec(statement).first()
            return db_library is not None
        except Exception:
            return False
    
    def get_library_stats(self, library_id: UUID, session: Session) -> LibraryStats:
        """Get library statistics"""
        try:
            if not self.library_exists(library_id, session):
                raise HTTPException(
                    status_code=404,
                    detail=f"Library with ID {library_id} not found"
                )
            
            # Get file count from database
            file_statement = select(FileModel).where(FileModel.library_id == library_id)
            db_files = session.exec(file_statement).all()
            file_count = len(db_files)
            
            # Get total size from MinIO
            minio_files = minio_service.list_library_files(library_id)
            total_size = sum(file["size"] for file in minio_files)
            
            return LibraryStats(file_count=file_count, total_size=total_size)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting library stats {library_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get library statistics")
    
    def create_file_record(self, library_id: UUID, file_id: UUID, file_name: str, session: Session) -> FileModel:
        """Create a file record in the database"""
        try:
            db_file = FileModel(
                id=file_id,
                library_id=library_id,
                file_name=file_name
            )
            
            session.add(db_file)
            session.commit()
            session.refresh(db_file)
            
            logger.info(f"Created file record: {file_name} (ID: {file_id}) in library {library_id}")
            
            return db_file
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating file record: {e}")
            raise HTTPException(status_code=500, detail="Failed to create file record")

# Create singleton instance
library_service = LibraryService() 