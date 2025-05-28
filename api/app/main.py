from pathlib import Path
import logging, os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.minio_init import initialize_minio_buckets
# Import models to ensure they are registered with SQLModel
from app.models.library import Library
from app.models.file import File
# Routers are now consolidated in app.routers
from app.routers import (
    # auth,
    library,
    retriever,
    chat,
    evaluation,
    utilities,
    dev
)

logging.basicConfig(level=logging.INFO) # Ensure logging is configured
logger = logging.getLogger(__name__) # Get logger for main.py

app = FastAPI(
    title=settings.app_name,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "none"
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    logger.info("Creating database tables...")
    create_db_and_tables()
    logger.info("Database tables created successfully")

    # Initialize MinIO buckets
    success = initialize_minio_buckets(
        endpoint="localhost:9000",  # Use service name when running in Docker
        access_key="adminadmin",
        secret_key="adminadmin",
        bucket_names=["rag-files", "rag-chunked-files", "rag-parsed-files"]
    )
    
    if not success:
        raise Exception("Failed to initialize MinIO buckets")

# Include routers
# app.include_router(auth.router)
app.include_router(library.router)
app.include_router(retriever.router)
app.include_router(chat.router)
app.include_router(evaluation.router)
app.include_router(utilities.router)
app.include_router(dev.router)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}


# If you want to run directly with uvicorn (e.g., for local development):
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 