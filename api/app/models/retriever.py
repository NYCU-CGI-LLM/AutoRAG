from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from enum import Enum

if TYPE_CHECKING:
    from .library import Library
    from .chat import Chat


class ParserEnum(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"


class VectorDBTypeEnum(str, Enum):
    CHROMA = "chroma"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"


class Retriever(SQLModel, table=True):
    __tablename__ = "retriever"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    parser: str = Field(..., max_length=50)  # ENUM
    chunk_size: int = Field(...)
    library_id: UUID = Field(foreign_key="library.id", index=True)
    vectordb_id: Optional[UUID] = Field(default=None, foreign_key="vectordb_retriever.id")
    bm25_id: Optional[UUID] = Field(default=None, foreign_key="bm25_retriever.id")
    
    # Relationships
    library: "Library" = Relationship(back_populates="retrievers")
    chats: List["Chat"] = Relationship(back_populates="retriever")
    vectordb_retriever: Optional["VectorDBRetriever"] = Relationship(back_populates="retriever")
    bm25_retriever: Optional["BM25Retriever"] = Relationship(back_populates="retriever")


class VectorDBRetriever(SQLModel, table=True):
    __tablename__ = "vectordb_retriever"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    type: str = Field(..., max_length=50)  # ENUM
    collection: str = Field(..., max_length=255)
    
    # Relationships
    retriever: Optional["Retriever"] = Relationship(back_populates="vectordb_retriever")


class BM25Retriever(SQLModel, table=True):
    __tablename__ = "bm25_retriever"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    tokenizer: str = Field(..., max_length=100)
    name: str = Field(..., max_length=100)
    
    # Relationships
    retriever: Optional["Retriever"] = Relationship(back_populates="bm25_retriever") 