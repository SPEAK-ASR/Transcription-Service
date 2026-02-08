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
from app.services.db_service import TranscriptionService, YouTubeVideoService
from app.services.gcs_service import gcs_service
from app.schemas import (
    AudioResponse,
    TranscriptionResponse,
    TranscriptionValidationUpdate,
    ValidationQueueItem,
    ValidationProgressResponse,
    AudioClipForValidation,
    YouTubeVideoWithAudioClips,
    YouTubeVideoValidationStatusUpdate,
    YouTubeVideoValidationResponse,
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


@router.get(
    "/youtube-video/next",
    response_model=YouTubeVideoWithAudioClips,
    summary="Get the next YouTube video awaiting validation with audio clips",
    tags=["YouTube Video Validation"],
)
async def get_next_youtube_video_for_validation(
    db: AsyncSession = Depends(get_async_database_session),
) -> YouTubeVideoWithAudioClips:
    """
    Return the next unvalidated YouTube video with the highest audio clip count.
    
    Audio clip selection logic:
    - Returns 10% of the video's total audio clips
    - If 10% > 10, caps at 10 audio clips
    - If 10% < 1, returns all existing audio clips
    
    Videos are ordered by audio_clip_count descending to prioritize videos with more clips.
    """
    try:
        video_data = await YouTubeVideoService.get_next_youtube_video_for_validation(db)
        
        if not video_data:
            raise HTTPException(
                status_code=404,
                detail="No YouTube videos pending validation",
            )
        
        # Generate signed URLs for each audio clip
        audio_clips_with_urls = []
        for clip in video_data['audio_clips']:
            signed_url = await gcs_service.generate_signed_url(clip['audio_filename'])
            audio_clips_with_urls.append(
                AudioClipForValidation(
                    audio_id=clip['audio_id'],
                    audio_filename=clip['audio_filename'],
                    google_transcription=clip['google_transcription'],
                    gcs_signed_url=signed_url,
                )
            )
        
        return YouTubeVideoWithAudioClips(
            id=video_data['id'],
            video_id=video_data['video_id'],
            title=video_data['title'],
            description=video_data['description'],
            duration=video_data['duration'],
            uploader=video_data['uploader'],
            upload_date=video_data['upload_date'],
            thumbnail=video_data['thumbnail'],
            url=video_data['url'],
            domain=video_data['domain'],
            is_validated=video_data['is_validated'],
            created_at=video_data['created_at'],
            audio_clip_count=video_data['audio_clip_count'],
            audio_clips=audio_clips_with_urls,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching YouTube video for validation: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load YouTube video for validation")


@router.post(
    "/youtube-video/{video_id}/validation-status",
    response_model=YouTubeVideoValidationResponse,
    summary="Update YouTube video validation status",
    tags=["YouTube Video Validation"],
)
async def update_youtube_video_validation_status(
    video_id: UUID,
    payload: YouTubeVideoValidationStatusUpdate,
    db: AsyncSession = Depends(get_async_database_session),
) -> YouTubeVideoValidationResponse:
    """
    Update the is_validated status of a YouTube video.
    
    Set is_validated to True to mark as validated, or False to mark as invalid.
    """
    try:
        result = await YouTubeVideoService.update_youtube_video_validation_status(
            db, video_id, payload.is_validated
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"YouTube video with id {video_id} not found",
            )
        
        status_text = "validated" if result['is_validated'] else "marked as invalid"
        return YouTubeVideoValidationResponse(
            id=result['id'],
            video_id=result['video_id'],
            is_validated=result['is_validated'],
            message=f"YouTube video successfully {status_text}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating YouTube video validation status: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update validation status")
