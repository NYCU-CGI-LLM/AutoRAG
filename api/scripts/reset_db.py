#!/usr/bin/env python3
"""Reset database tables script"""

import sys
import logging
from pathlib import Path

# Add the parent directory (api/) to Python path for imports
api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from app.core.database import engine
from sqlmodel import SQLModel
from sqlalchemy import text

# Import all models to register them with SQLModel metadata
from app.models.user import User
from app.models.library import Library
from app.models.file import File, FileStatus
from app.models.retriever import Retriever, RetrieverStatus
from app.models.chat import Chat
from app.models.dialog import Dialog
from app.models.parser import Parser, ParserStatus
from app.models.chunker import Chunker, ChunkerStatus
from app.models.indexer import Indexer, IndexerStatus
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.models.config import Config, ConfigStatus
from app.models.evaluation import Evaluation, BenchmarkDataset, EvaluationStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_database():
    """Drop and recreate all database tables"""
    logger.info("Starting database reset process...")
    logger.info("Dropping all tables and recreating schema...")
    
    with engine.connect() as conn:
        try:
            # Method 1: Try to drop schema and recreate (most thorough)
            logger.info("Attempting to drop and recreate public schema...")
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            conn.commit()
            logger.info("Successfully dropped and recreated public schema")
            
        except Exception as e:
            logger.warning(f"Schema recreation failed: {e}")
            conn.rollback()
            
            # Method 2: Fallback to individual table dropping with proper quoting
            try:
                logger.info("Fallback: Dropping tables individually...")
                
                # Get all table names
                result = conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                if tables:
                    logger.info(f"Found {len(tables)} tables to drop: {', '.join(tables)}")
                    
                    # Drop each table with proper quoting and CASCADE
                    for table in tables:
                        try:
                            # Use quoted identifiers to handle reserved keywords
                            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                            logger.info(f"Dropped table: {table}")
                            conn.commit()  # Commit each drop individually
                        except Exception as table_error:
                            logger.warning(f"Could not drop table {table}: {table_error}")
                            conn.rollback()  # Rollback only this operation
                            continue
                    
                    logger.info("Completed individual table dropping")
                else:
                    logger.info("No existing tables found to drop")
                    
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {fallback_error}")
                conn.rollback()

    # Create all tables using SQLModel metadata
    try:
        logger.info("Creating all tables using SQLModel metadata...")
        SQLModel.metadata.create_all(engine)
        logger.info("All tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            created_tables = [row[0] for row in result.fetchall()]
            
        logger.info("Database reset completed successfully!")
        logger.info(f"Created {len(created_tables)} tables:")
        for table in sorted(created_tables):
            logger.info(f"  ✓ {table}")
        
        logger.info("Table descriptions:")
        logger.info("- benchmark_datasets (benchmark datasets for evaluation)")
        logger.info("- chat (chat sessions)")
        logger.info("- chunker (chunking configurations)")
        logger.info("- config (general configurations)")
        logger.info("- dialog (chat messages)")
        logger.info("- embeddingstats (embedding statistics tracking)")
        logger.info("- evaluations (evaluation runs with status tracking and results storage)")
        logger.info("- file (files with MinIO integration)")
        logger.info("- file_chunk_result (chunking results)")
        logger.info("- file_parse_result (parsing results)")
        logger.info("- indexer (indexing configurations)")
        logger.info("- library (document libraries)")
        logger.info("- parser (parsing configurations)")
        logger.info("- retriever (retrieval configurations)")
        logger.info("- user (user management)")
        
    except Exception as e:
        logger.error(f"Error during table creation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    reset_database() 