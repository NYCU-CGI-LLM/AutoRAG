from pathlib import Path
import logging, os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
# Routers are now consolidated in app.routers
from app.routers import (
    auth,
    knowledge_bases,
    chunk_variations,
    parse_variations,
    indexing_variation,
    simple_router,
    rag
    # tasks, # Assuming you might want to use this later
)

logging.basicConfig(level=logging.INFO) # Ensure logging is configured
logger = logging.getLogger(__name__) # Get logger for main.py

app = FastAPI(
    title=settings.app_name,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(knowledge_bases.router)
app.include_router(parse_variations.router)
app.include_router(chunk_variations.router)
app.include_router(indexing_variation.router)
app.include_router(rag.router)
app.include_router(simple_router.router)
# app.include_router(query.router) # This was previously commented out, keeping as is
# app.include_router(tasks.router) # This was previously commented out, keeping as is

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}


# If you want to run directly with uvicorn (e.g., for local development):
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 