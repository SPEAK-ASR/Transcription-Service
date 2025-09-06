"""
Main FastAPI application for Sinhala ASR dataset creation.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_database, close_database
from app.core.gcp_auth import gcp_auth_manager
from app.api.v1.api import api_router
from app.web.routes import router as web_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up Sinhala ASR Dataset Creation Service")
    
    # Setup GCP credentials first
    try:
        gcp_auth_manager.setup_credentials()
        logger.info("GCP authentication configured successfully")
    except Exception as e:
        logger.error(f"Failed to setup GCP credentials: {e}")
        # Don't raise here - let the app continue with default auth
    
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sinhala ASR Dataset Creation Service")
    try:
        await close_database()
        logger.info("Database connection closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    # Cleanup GCP resources
    try:
        gcp_auth_manager.cleanup()
        logger.info("GCP resources cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up GCP resources: {e}")


app = FastAPI(
    title="Sinhala ASR Dataset Creation Service",
    description="API for creating Sinhala ASR datasets with transcription collection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include web routes
app.include_router(web_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {
        "message": "Sinhala ASR Dataset Creation Service",
        "status": "active",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}
