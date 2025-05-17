from pathlib import Path
import logging, os


logging.basicConfig(level=logging.INFO) # Ensure logging is configured
logger = logging.getLogger(__name__) # Get logger for main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router

app.include_router(auth_router)
app.include_router(projects_router)

@app.get("/")
def read_root():
    return {"message": "API is up and running."} 