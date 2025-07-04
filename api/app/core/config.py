import logging
import os # Added for os.getenv
from typing import List
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Explicitly load .env.dev file before Settings instantiation
env_file_path = Path(__file__).resolve().parent.parent.parent / '.env.dev'
print(f"Loading .env.dev from: {env_file_path}")
print(f"File exists: {env_file_path.exists()}")
load_dotenv(env_file_path)
print(f"OPENAI_API_KEY loaded: {os.getenv('OPENAI_API_KEY', 'NOT FOUND')[:20] if os.getenv('OPENAI_API_KEY') else 'NOT FOUND'}...")

class Settings(BaseSettings):
    # Pydantic v2 settings: load environment variables from .env.dev
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_file=str(Path(__file__).resolve().parent.parent.parent / '.env.dev'),
        env_file_encoding='utf-8'
    )

    autorag_api_env: str = "dev"
    work_dir: Path = Field(default=Path(__file__).resolve().parent.parent / "projects")
    app_name: str = "AUO-RAG API"
    app_version: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    cors_allow_origins: List[str] = ["*"]
    # database_url: str = Field(..., env="DATABASE_URL")
    secret_key: str = Field(default="your-secret-key-here")
    access_token_expire_minutes: int = 30
    
    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "adminadmin"
    minio_secret_key: str = "adminadmin"
    minio_secure: bool = False
    minio_bucket_name: str = "autorag-files"
    minio_benchmark_bucket: str = "rag-benchmarks"  # New bucket for evaluation benchmarks
    minio_evaluation_bucket: str = "rag-evaluations"  # New bucket for evaluation results
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # ChromaDB Configuration
    chroma_path: str = Field(default="./resources/chroma")
    default_embedding_model: str = Field(default="openai_embed_3_large")
    embedding_batch_size: int = Field(default=100)
    
    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

logger = logging.getLogger(__name__)
logger.info("Before Settings instantiation in config.py")
# logger.info(f"DATABASE_URL in config.py (os.getenv): {os.getenv('DATABASE_URL')}")
logger.info(f"SECRET_KEY in config.py (os.getenv): {os.getenv('SECRET_KEY')}")

settings = Settings()
logger.info("After Settings instantiation in config.py")

# Print all configuration values for debugging
logger.info("=== API SERVER CONFIGURATION ===")
logger.info(f"App Name: {settings.app_name}")
logger.info(f"App Version: {settings.app_version}")
logger.info(f"Environment: {settings.autorag_api_env}")
logger.info(f"Work Directory: {settings.work_dir}")
logger.info(f"API V1 String: {settings.API_V1_STR}")
logger.info(f"CORS Origins: {settings.cors_allow_origins}")
logger.info(f"Secret Key: {settings.secret_key[:20]}...")
logger.info(f"Token Expire Minutes: {settings.access_token_expire_minutes}")

logger.info("=== MINIO CONFIGURATION ===")
logger.info(f"MinIO Endpoint: {settings.minio_endpoint}")
logger.info(f"MinIO Access Key: {settings.minio_access_key}")
logger.info(f"MinIO Secret Key: {settings.minio_secret_key[:10]}...")
logger.info(f"MinIO Secure: {settings.minio_secure}")
logger.info(f"MinIO Bucket: {settings.minio_bucket_name}")
logger.info(f"MinIO Benchmark Bucket: {settings.minio_benchmark_bucket}")
logger.info(f"MinIO Evaluation Bucket: {settings.minio_evaluation_bucket}")

logger.info("=== REDIS CONFIGURATION ===")
logger.info(f"Redis Host: {settings.redis_host}")
logger.info(f"Redis Port: {settings.redis_port}")
logger.info(f"Redis DB: {settings.redis_db}")

logger.info("=== CHROMADB CONFIGURATION ===")
logger.info(f"Chroma Path: {settings.chroma_path}")
logger.info(f"Default Embedding Model: {settings.default_embedding_model}")
logger.info(f"Embedding Batch Size: {settings.embedding_batch_size}")

logger.info("=== QDRANT CONFIGURATION ===")
logger.info(f"Qdrant Host: {settings.qdrant_host}")
logger.info(f"Qdrant Port: {settings.qdrant_port}")

logger.info("=== ENVIRONMENT VARIABLES ===")
logger.info(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'NOT FOUND')[:20] if os.getenv('OPENAI_API_KEY') else 'NOT FOUND'}...")
logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT FOUND')}")
logger.info(f"CELERY_BROKER_URL: {os.getenv('CELERY_BROKER_URL', 'NOT FOUND')}")
logger.info(f"CELERY_RESULT_BACKEND: {os.getenv('CELERY_RESULT_BACKEND', 'NOT FOUND')}")
logger.info(f"AUTORAG_API_ENV: {os.getenv('AUTORAG_API_ENV', 'NOT FOUND')}")
logger.info(f"AUTORAG_WORK_DIR: {os.getenv('AUTORAG_WORK_DIR', 'NOT FOUND')}")
logger.info("=== END CONFIGURATION ===") 