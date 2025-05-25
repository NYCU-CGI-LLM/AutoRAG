from pathlib import Path
import logging, os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
# Routers are now consolidated in app.routers
from app.routers import (
    auth,
    simple_router,
    tasks,
    library,
    retriever,
    chat,
    evaluation
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

# Include routers
app.include_router(auth.router)
app.include_router(simple_router.router)
app.include_router(tasks.router)
app.include_router(library.router)
app.include_router(retriever.router)
app.include_router(chat.router)
app.include_router(evaluation.router)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}


# If you want to run directly with uvicorn (e.g., for local development):
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 