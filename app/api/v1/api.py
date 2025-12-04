"""
API v1 router configuration.

This module configures the main API router by combining all endpoint routers
for the Sinhala ASR Dataset Collection Service API v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import audio, transcription, validation, admin

# Create main API router
api_router = APIRouter()

# Include endpoint routers with appropriate prefixes and tags
api_router.include_router(
    audio.router, 
    prefix="/audio", 
    tags=["Audio Management"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request"}
    }
)

api_router.include_router(
    transcription.router, 
    prefix="/transcription", 
    tags=["Transcription Collection"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request"},
        404: {"description": "Audio file not found"}
    }
)

api_router.include_router(
    validation.router,
    prefix="/validation",
    tags=["Transcription Validation"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "No items pending validation"}
    }
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"],
    responses={
        500: {"description": "Internal server error"}
    }
)
