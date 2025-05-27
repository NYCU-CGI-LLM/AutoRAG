#!/usr/bin/env python3
"""Reset database tables script"""

from app.core.database import engine
from sqlmodel import SQLModel

# Import all models to register them with SQLModel metadata
from app.models.user import User
from app.models.library import Library
from app.models.file import File, FileStatus
from app.models.retriever import Retriever, VectorDBRetriever, BM25Retriever
from app.models.chat import Chat
from app.models.dialog import Dialog
from app.models.parser import Parser, ParserStatus
from app.models.chunker import Chunker, ChunkerStatus
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus

def reset_database():
    """Drop and recreate all database tables"""
    print("Dropping all tables...")
    SQLModel.metadata.drop_all(engine)
    print("Tables dropped successfully")
    
    print("Creating all tables...")
    SQLModel.metadata.create_all(engine)
    print("Tables created successfully")
    print("\nDatabase reset completed with updated schema!")
    print("New tables created:")
    print("- file (with MinIO fields, extended metadata, and FileStatus enum)")
    print("- parser (with module_type string field, supported_mime array, params JSONB, and ParserStatus enum)")
    print("- chunker (with module_type, chunk_method, chunk_size, chunk_overlap, params JSONB, and ChunkerStatus enum)")
    print("- file_parse_result (for tracking parse results with bucket and JSONB metadata)")
    print("- file_chunk_result (for tracking chunk results linking parse results to chunkers)")

if __name__ == "__main__":
    reset_database() 