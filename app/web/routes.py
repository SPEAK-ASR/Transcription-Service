"""
Web routes for the transcription UI.
"""

import logging
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.core.database import get_async_database_session
from app.services.db_service import AudioService, TranscriptionService
from app.services.gcs_service import gcs_service
from app.schemas import TranscriptionCreate, SpeakerGender

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def transcription_home(
    request: Request,
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Main transcription page - loads a random audio file for transcription.
    """
    try:
        # Get a random audio file that needs transcription
        audio_file = await AudioService.get_random_audio_for_transcription(db)
        
        audio_data = None
        if audio_file:
            # Generate signed URL for the audio file
            signed_url = await gcs_service.generate_signed_url(audio_file.audio_filename)
            
            audio_data = {
                "audio_id": str(audio_file.audio_id),
                "audio_filename": audio_file.audio_filename,
                "google_transcription": audio_file.google_transcription,
                "transcription_count": audio_file.transcription_count,
                "gcs_signed_url": signed_url
            }
            
            logger.info(f"Serving audio file: {audio_file.audio_filename}")
        
        return templates.TemplateResponse(
            "transcription.html",
            {
                "request": request,
                "audio": audio_data,
                "speaker_genders": [gender.value for gender in SpeakerGender],
                "success_message": None,
                "error_message": None
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading transcription page: {e}")
        return templates.TemplateResponse(
            "transcription.html",
            {
                "request": request,
                "audio": None,
                "speaker_genders": [gender.value for gender in SpeakerGender],
                "success_message": None,
                "error_message": "Error loading audio file. Please try again."
            }
        )


@router.post("/submit-transcription", response_class=HTMLResponse)
async def submit_transcription(
    request: Request,
    audio_id: str = Form(...),
    transcription: str = Form(...),
    speaker_gender: str = Form(...),
    has_noise: bool = Form(default=False),
    is_code_mixed: bool = Form(default=False),
    is_speaker_overlapping: bool = Form(default=False),
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Submit a transcription and load a new random audio file.
    """
    try:
        # Validate and create transcription
        transcription_data = TranscriptionCreate(
            audio_id=UUID(audio_id),
            transcription=transcription.strip(),
            speaker_gender=SpeakerGender(speaker_gender),
            has_noise=has_noise,
            is_code_mixed=is_code_mixed,
            is_speaker_overlapping=is_speaker_overlapping
        )
        
        # Submit the transcription
        new_transcription = await TranscriptionService.create_transcription(
            db, transcription_data
        )
        
        logger.info(f"Transcription submitted: {new_transcription.trans_id}")
        
        # Get a new random audio file for the next transcription
        audio_file = await AudioService.get_random_audio_for_transcription(db)
        
        audio_data = None
        if audio_file:
            signed_url = await gcs_service.generate_signed_url(audio_file.audio_filename)
            audio_data = {
                "audio_id": str(audio_file.audio_id),
                "audio_filename": audio_file.audio_filename,
                "google_transcription": audio_file.google_transcription,
                "transcription_count": audio_file.transcription_count,
                "gcs_signed_url": signed_url
            }
        
        return templates.TemplateResponse(
            "transcription.html",
            {
                "request": request,
                "audio": audio_data,
                "speaker_genders": [gender.value for gender in SpeakerGender],
                "success_message": "Transcription submitted successfully! Here's your next audio file.",
                "error_message": None
            }
        )
        
    except ValueError as ve:
        logger.warning(f"Validation error in transcription submission: {ve}")
        error_message = f"Validation error: {str(ve)}"
    except HTTPException as he:
        logger.warning(f"HTTP error in transcription submission: {he.detail}")
        error_message = he.detail
    except Exception as e:
        logger.error(f"Error submitting transcription: {e}")
        error_message = "An error occurred while submitting your transcription. Please try again."
    
    # On error, try to reload the same audio or get a new one
    try:
        # Try to get the current audio file first
        current_audio = None
        if audio_id:
            from sqlalchemy import select
            from app.models import Audio
            result = await db.execute(select(Audio).where(Audio.audio_id == UUID(audio_id)))
            current_audio = result.scalar_one_or_none()
            
            if current_audio and current_audio.transcription_count < 2:
                signed_url = await gcs_service.generate_signed_url(current_audio.audio_filename)
                audio_data = {
                    "audio_id": str(current_audio.audio_id),
                    "audio_filename": current_audio.audio_filename,
                    "google_transcription": current_audio.google_transcription,
                    "transcription_count": current_audio.transcription_count,
                    "gcs_signed_url": signed_url
                }
            else:
                # Get a new random audio file
                audio_file = await AudioService.get_random_audio_for_transcription(db)
                if audio_file:
                    signed_url = await gcs_service.generate_signed_url(audio_file.audio_filename)
                    audio_data = {
                        "audio_id": str(audio_file.audio_id),
                        "audio_filename": audio_file.audio_filename,
                        "google_transcription": audio_file.google_transcription,
                        "transcription_count": audio_file.transcription_count,
                        "gcs_signed_url": signed_url
                    }
                else:
                    audio_data = None
        else:
            audio_data = None
            
    except Exception:
        audio_data = None
    
    return templates.TemplateResponse(
        "transcription.html",
        {
            "request": request,
            "audio": audio_data,
            "speaker_genders": [gender.value for gender in SpeakerGender],
            "success_message": None,
            "error_message": error_message
        }
    )


@router.get("/new-audio", response_class=HTMLResponse)
async def get_new_audio(
    request: Request,
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Get a new random audio file (skip current one).
    """
    return RedirectResponse(url="/", status_code=302)
