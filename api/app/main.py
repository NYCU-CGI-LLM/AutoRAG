from pathlib import Path
import logging, os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.core.config import settings
# Assuming your routers are in app.routes
from app.routes import knowledge_bases, variations, query, tasks # Updated imports

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
app.include_router(knowledge_bases.router)
app.include_router(variations.router) # This handles /knowledge-bases/{kb_id}/variations
# app.include_router(query.router) # This handles /knowledge-bases/{kb_id}/variations/{variation_id}/query
# app.include_router(tasks.router)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}"}

# This is for AWS Lambda deployment, if you need it.
# If not deploying to Lambda, you can remove mangum and this handler.
handler = Mangum(app)

# If you want to run directly with uvicorn (e.g., for local development):
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 