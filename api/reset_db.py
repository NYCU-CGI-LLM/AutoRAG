#!/usr/bin/env python3
"""Reset database tables script"""

from app.core.database import engine
from sqlmodel import SQLModel

# Import models to register them
from app.models.library import Library
from app.models.file import File

def reset_database():
    """Drop and recreate all database tables"""
    print("Dropping all tables...")
    SQLModel.metadata.drop_all(engine)
    print("Tables dropped successfully")
    
    print("Creating all tables...")
    SQLModel.metadata.create_all(engine)
    print("Tables created successfully")

if __name__ == "__main__":
    reset_database() 