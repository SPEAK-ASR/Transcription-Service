"""
Transcription endpoints for collecting user transcriptions.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_database_session
from app.models import Audio
from app.schemas import (
    TranscriptionCreate,
    TranscriptionResponse,
)
from app.services.db_service import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=TranscriptionResponse,
    status_code=201,
    summary="Submit a transcription",
    description="Submit a user transcription for an audio file with speaker metadata"
)
async def create_transcription(
    transcription_data: TranscriptionCreate,
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Create a new transcription for an audio file.
    
    This endpoint:
    1. Validates the audio file exists
    2. Checks if the audio already has enough transcriptions (max 2)
    3. Creates the transcription record with speaker metadata
    4. Updates audio transcription count
    """
    try:
        # Get the audio file (now truly async)
        result = await db.execute(select(Audio).where(Audio.audio_id == transcription_data.audio_id))
        audio_file = result.scalar_one_or_none()
        
        if not audio_file:
            raise HTTPException(
                status_code=404,
                detail=f"Audio file not found: {transcription_data.audio_id}"
            )
        
        # Check if audio already has enough transcriptions
        if audio_file.transcription_count >= 2:
            logger.warning(f"Attempt to transcribe completed audio: {audio_file.audio_filename}")
            raise HTTPException(
                status_code=400,
                detail="This audio file already has the maximum number of transcriptions (2)"
            )
        
        # Create the transcription (now truly async)
        new_transcription = await TranscriptionService.create_transcription(
            db,
            transcription_data,
        )
        
        logger.info(
            f"Created transcription {new_transcription.trans_id} "
            f"for audio {audio_file.audio_filename}"
        )
        
        return TranscriptionResponse(
            trans_id=new_transcription.trans_id,
            audio_id=audio_file.audio_id,
            transcription=new_transcription.transcription,
            speaker_gender=new_transcription.speaker_gender,
            has_noise=new_transcription.has_noise,
            is_code_mixed=new_transcription.is_code_mixed,
            is_speaker_overlapping=new_transcription.is_speaker_overlapping,
            created_at=new_transcription.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transcription: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating transcription"
        )
