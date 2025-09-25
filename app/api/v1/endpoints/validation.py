"""
Validation endpoints for transcription review workflow.

These endpoints serve the browser-based validation page with pending
transcriptions and allow admins to confirm or correct submissions.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_database_session
from app.services.db_service import TranscriptionService
from app.services.gcs_service import gcs_service
from app.schemas import (
    AudioResponse,
    TranscriptionResponse,
    TranscriptionValidationUpdate,
    ValidationQueueItem,
    ValidationProgressResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/next",
    response_model=ValidationQueueItem,
    summary="Get the next transcription awaiting validation",
    tags=["Transcription Validation"],
)
async def get_next_validation_item(
    db: AsyncSession = Depends(get_async_database_session),
) -> ValidationQueueItem:
    """Return the oldest transcription that still needs validation."""
    try:
        record = await TranscriptionService.get_next_unvalidated_transcription(db)
        if not record:
            raise HTTPException(
                status_code=404,
                detail="No transcriptions pending validation",
            )

        transcription, audio = record
        signed_url = await gcs_service.generate_signed_url(audio.audio_filename)

        audio_payload = AudioResponse(
            audio_id=audio.audio_id,
            audio_filename=audio.audio_filename,
            google_transcription=audio.google_transcription,
            transcription_count=audio.transcription_count,
            gcs_signed_url=signed_url,
        )

        transcription_payload = TranscriptionResponse(
            trans_id=transcription.trans_id,
            audio_id=transcription.audio_id,
            transcription=transcription.transcription,
            speaker_gender=transcription.speaker_gender,
            has_noise=transcription.has_noise,
            is_code_mixed=transcription.is_code_mixed,
            is_speaker_overlappings_exist=transcription.is_speaker_overlappings_exist,
            is_audio_suitable=transcription.is_audio_suitable,
            admin=transcription.admin,
            validated_at=transcription.validated_at,
            created_at=transcription.created_at,
        )

        return ValidationQueueItem(audio=audio_payload, transcription=transcription_payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching validation item: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load validation item")


@router.get(
    "/stats",
    response_model=ValidationProgressResponse,
    summary="Get validation progress counts",
    tags=["Transcription Validation"],
)
async def get_validation_stats(
    db: AsyncSession = Depends(get_async_database_session),
) -> ValidationProgressResponse:
    """Return counts for validation progress indicator on the dashboard."""
    try:
        counts = await TranscriptionService.get_validation_progress_counts(db)
        return ValidationProgressResponse(**counts)
    except Exception as exc:
        logger.error("Error fetching validation stats: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load validation progress")

@router.put(
    "/{transcription_id}",
    response_model=TranscriptionResponse,
    summary="Validate and update an existing transcription",
    tags=["Transcription Validation"],
)
async def validate_transcription_item(
    transcription_id: UUID,
    payload: TranscriptionValidationUpdate,
    db: AsyncSession = Depends(get_async_database_session),
) -> TranscriptionResponse:
    """Update a transcription with reviewer corrections and mark it as validated."""
    try:
        updated = await TranscriptionService.validate_transcription(db, transcription_id, payload)
        return TranscriptionResponse(
            trans_id=updated.trans_id,
            audio_id=updated.audio_id,
            transcription=updated.transcription,
            speaker_gender=updated.speaker_gender,
            has_noise=updated.has_noise,
            is_code_mixed=updated.is_code_mixed,
            is_speaker_overlappings_exist=updated.is_speaker_overlappings_exist,
            is_audio_suitable=updated.is_audio_suitable,
            admin=updated.admin,
            validated_at=updated.validated_at,
            created_at=updated.created_at,
        )
    except ValueError as exc:
        logger.warning("Validation target missing: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error validating transcription %s: %s", transcription_id, exc)
        raise HTTPException(status_code=500, detail="Failed to validate transcription")
