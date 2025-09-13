"""
Web UI routes for the transcription interface.

This module provides web routes for the browser-based transcription interface,
including the main transcription page, form submission handlers, and AJAX
endpoints for dynamic content loading.
"""

import logging
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import Optional

from app.core.database import get_async_database_session
from app.services.db_service import AudioService, TranscriptionService
from app.services.gcs_service import gcs_service
from app.schemas import TranscriptionCreate

# Speaker gender options for form dropdowns
SPEAKER_GENDER_OPTIONS = ["male", "female", "cannot_recognized"]

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
                "speaker_genders": SPEAKER_GENDER_OPTIONS,
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
                "speaker_genders": SPEAKER_GENDER_OPTIONS,
                "success_message": None,
                "error_message": "Error loading audio file. Please try again."
            }
        )


@router.post("/submit-transcription")
async def submit_transcription(
    request: Request,
    audio_id: str = Form(...),
    transcription: str = Form(...),
    speaker_gender: str = Form(...),
    has_noise: bool = Form(default=False),
    is_code_mixed: bool = Form(default=False),
    is_speaker_overlapping: bool = Form(default=False),
    is_audio_suitable: Optional[bool] = Form(default=True),
    admin: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Submit a transcription and return JSON response.
    """
    try:
        # Validate and create transcription
        transcription_data = TranscriptionCreate(
            audio_id=UUID(audio_id),
            transcription=transcription.strip(),
            speaker_gender=speaker_gender,  # Now just a string, not enum
            has_noise=has_noise,
            is_code_mixed=is_code_mixed,
            is_speaker_overlappings_exist=is_speaker_overlapping,
            is_audio_suitable=is_audio_suitable,
            admin=admin if admin else None
        )
        
        # Submit the transcription
        new_transcription = await TranscriptionService.create_transcription(
            db, transcription_data
        )
        
        logger.info(f"Transcription submitted: {new_transcription.trans_id}")
        
        # Return success JSON response
        return JSONResponse(
            content={
                "success": True,
                "message": "Transcription submitted successfully!"
            },
            status_code=200
        )
        
    except ValueError as ve:
        logger.warning(f"Validation error in transcription submission: {ve}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"Validation error: {str(ve)}"
            },
            status_code=400
        )
    except HTTPException as he:
        logger.warning(f"HTTP error in transcription submission: {he.detail}")
        return JSONResponse(
            content={
                "success": False,
                "message": he.detail
            },
            status_code=he.status_code
        )
    except Exception as e:
        logger.error(f"Error submitting transcription: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": "An error occurred while submitting your transcription. Please try again."
            },
            status_code=500
        )


@router.get("/api/new-audio")
async def get_new_audio_api(
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    API endpoint to get a new random audio file as JSON.
    """
    try:
        # Get a random audio file that needs transcription
        audio_file = await AudioService.get_random_audio_for_transcription(db)
        
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
            
            logger.info(f"Serving new audio file via API: {audio_file.audio_filename}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "audio": audio_data
                }
            )
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "No audio files available for transcription."
                }
            )
            
    except Exception as e:
        logger.error(f"Error getting new audio via API: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": "Error loading audio file. Please try again."
            },
            status_code=500
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


@router.get("/api/admin-leaderboard")
async def get_admin_leaderboard(
    range: str = "all",
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Return aggregated transcription counts per admin.

    Query params:
    - range: one of 'all', 'week', 'month'
    """
    try:
        rng = (range or "all").lower()
        if rng not in {"all", "week", "month"}:
            rng = "all"

        # Build time filter using PostgreSQL date_trunc for current week/month
        time_filter = ""
        if rng == "week":
            time_filter = " AND created_at >= date_trunc('week', now())"
        elif rng == "month":
            time_filter = " AND created_at >= date_trunc('month', now())"

        query = text(
            f"""
            SELECT admin, COUNT(*) AS count
            FROM "Transcriptions"
            WHERE admin IS NOT NULL {time_filter}
            GROUP BY admin
            ORDER BY count DESC, admin ASC;
            """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        data = [
            {"admin": r[0], "count": int(r[1]) if r[1] is not None else 0}
            for r in rows
            if r[0] is not None
        ]

        total = sum(item["count"] for item in data)

        return JSONResponse(
            content={
                "success": True,
                "range": rng,
                "total": total,
                "leaders": data,
            }
        )
    except Exception as e:
        logger.error(f"Error generating admin leaderboard: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": "Failed to load leaderboard."
            },
            status_code=500
        )
