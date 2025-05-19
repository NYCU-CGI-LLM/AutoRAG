from fastapi import APIRouter, HTTPException, status
from app.schemas.rag import (
    RetrieveRequest,
    RetrieveResponse,
    RetrievedPassage,
    GenerateRequest,
    GenerateResponse,
    RagRequest,
    RagResponse,
)

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)

@router.post(
    "/retrieve", response_model=RetrieveResponse, status_code=status.HTTP_200_OK
)
async def retrieve_rag(request: RetrieveRequest):
    """
    Retrieve top-k passages for a query after query expansion, filtering, reranking, augmenting, compressing.
    """
    # TODO: Implement retrieve pipeline
    return RetrieveResponse(passages=[])

@router.post(
    "/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK
)
async def generate_rag(request: GenerateRequest):
    """
    Generate the final answer by turning retrieved passages into a prompt and calling the generator.
    """
    # TODO: Build prompt and call generator
    return GenerateResponse(answer="")

@router.post(
    "/", response_model=RagResponse, status_code=status.HTTP_200_OK
)
async def full_rag(request: RagRequest):
    """
    Full pipeline: retrieve then generate.
    """
    # TODO: Implement full RAG pipeline
    return RagResponse(result="", retrieved_passage=[]) 