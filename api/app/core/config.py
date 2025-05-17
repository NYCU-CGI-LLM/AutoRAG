import logging
import os # Added for os.getenv
from typing import List
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Pydantic v2 settings: load environment variables from .env.dev
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_file=str(Path(__file__).resolve().parent.parent.parent / '.env.dev'),
        env_file_encoding='utf-8'
    )

    autorag_api_env: str = Field("dev", env="AUTORAG_API_ENV")
    work_dir: Path = Field(default=Path(__file__).resolve().parent.parent / "projects", env="AUTORAG_WORK_DIR")
    app_name: str = "AUO-RAG API"
    app_version: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    cors_allow_origins: List[str] = ["*"]
    database_url: str = Field(..., env="DATABASE_URL")
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = 30

logger = logging.getLogger(__name__)
logger.info("Before Settings instantiation in config.py")
logger.info(f"DATABASE_URL in config.py (os.getenv): {os.getenv('DATABASE_URL')}")
logger.info(f"SECRET_KEY in config.py (os.getenv): {os.getenv('SECRET_KEY')}")

settings = Settings()
logger.info("After Settings instantiation in config.py") 