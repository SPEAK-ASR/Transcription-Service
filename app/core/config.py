"""
Configuration settings for the application.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    """
    
    # Application settings
    APP_NAME: str = "Sinhala ASR Dataset Service"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Database connection components
    DBUSER: str = os.getenv("DBUSER")
    PASSWORD: str = os.getenv("PASSWORD")
    HOST: str = os.getenv("HOST")
    PORT: str = os.getenv("PORT")
    DBNAME: str = os.getenv("DBNAME")

    DATABASE_URL: str = f"postgresql://{DBUSER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

    # Google Cloud Storage settings
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "sinhala-asr-audio-dataset-2025")
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Audio settings
    SUPPORTED_AUDIO_FORMATS: List[str] = [".mp3", ".wav", ".m4a", ".ogg"]
    MAX_AUDIO_DURATION_SECONDS: int = 300  # 5 minutes
    
    # Annotation settings
    ANNOTATIONS_PER_CLIP: int = 2  # Each clip should be annotated by 2 users
    
    class Config:
        case_sensitive = True
        env_file = ".env"


# Create global settings instance
settings = Settings()
