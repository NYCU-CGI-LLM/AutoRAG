from pydantic import BaseModel, Field
from typing import Optional, List, Any

from .common import OrmBase

class RetrievedDocument(OrmBase):
    id: str
    content: str
    score: float
    # Potentially other metadata from the document

class QueryRequest(OrmBase):
    query_text: str
    top_k: int = Field(default=5, ge=1, le=100)
    # filters: Optional[Dict[str, Any]] = None # For future metadata filtering

class QueryResponse(OrmBase):
    answer: Optional[str] = None # If a generation step is added on top of retrieval
    retrieved_documents: List[RetrievedDocument]
    query_time_ms: Optional[float] = None

class LLMConfig(BaseModel):
    llm_name: str = Field(description="Name of the LLM model")
    llm_params: dict = Field(description="Parameters for the LLM model", default={})