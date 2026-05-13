"""
Audio API endpoints for the Sinhala ASR Dataset Collection Service.

Provides `/audio/random` for fetching the next leased audio clip for transcription.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_database_session
from app.schemas import AudioResponse
from app.services.gcs_service import gcs_service
from app.services.db_service import AudioService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/random",
    response_model=AudioResponse,
    summary="Get a random audio file",
    description="Returns a random audio file from Google Cloud Storage that needs transcription"
)
async def get_random_audio_clip(
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Get a random audio file for transcription.

    Claims an audio row via lease, then returns metadata with a signed GCS URL.
    """
    try:
        audio_file = await AudioService.get_random_audio_for_transcription(db)

        if not audio_file:
            raise HTTPException(
                status_code=404,
                detail="No audio files available for transcription"
            )

        signed_url = await gcs_service.generate_signed_url(audio_file.audio_filename)

        logger.info(
            f"Serving audio file: {audio_file.audio_filename} "
            f"(transcriptions: {audio_file.transcription_count})"
        )

        return AudioResponse(
            audio_id=audio_file.audio_id,
            audio_filename=audio_file.audio_filename,
            google_transcription=audio_file.google_transcription,
            speak_transcription=getattr(audio_file, "speak_transcription", None),
            transcription_count=audio_file.transcription_count,
            gcs_signed_url=signed_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving random audio file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching audio file"
        )
