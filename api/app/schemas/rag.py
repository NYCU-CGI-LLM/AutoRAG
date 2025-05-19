from typing import List, Union, Optional, Literal
from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class RetrievedPassage(BaseModel):
    content: str
    doc_id: str
    score: float
    filepath: Optional[str] = None
    file_page: Optional[int] = None
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None


class RetrieveResponse(BaseModel):
    passages: List[RetrievedPassage]


class GenerateRequest(BaseModel):
    query: str
    retrieved_passages: List[RetrievedPassage]
    result_column: Optional[str] = "generated_texts"


class GenerateResponse(BaseModel):
    answer: Union[str, List[str]]


class RagRequest(BaseModel):
    query: str
    top_k: int = 5
    result_column: Optional[str] = "generated_texts"


class RagResponse(BaseModel):
    result: Union[str, List[str]]
    retrieved_passage: List[RetrievedPassage]


class RunResponse(BaseModel):
    result: Union[str, List[str]]
    retrieved_passage: List[RetrievedPassage]


class RetrievalResponse(BaseModel):
    passages: List[RetrievedPassage]


class StreamResponse(BaseModel):
    type: Literal["generated_text", "retrieved_passage"]
    generated_text: Optional[str] = None
    retrieved_passage: Optional[RetrievedPassage] = None
    passage_index: Optional[int] = None
