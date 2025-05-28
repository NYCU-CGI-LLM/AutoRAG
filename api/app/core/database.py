import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from contextlib import contextmanager

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@localhost:5432/autorag_db")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    """Create database tables"""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager to get database session"""
    with Session(engine) as session:
        yield session 