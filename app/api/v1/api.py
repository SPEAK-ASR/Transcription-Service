"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import audio, transcription

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(transcription.router, prefix="/transcription", tags=["transcription"])
