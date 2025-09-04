"""
Audio endpoints for serving random audio clips.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_database_session
from app.schemas import AudioResponse, CSVUploadResult
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
    
    This endpoint:
    1. Fetches an audio file that needs transcription from the database
    2. Gets the corresponding audio file from cloud bucket  
    3. Returns audio metadata with signed URL
    """
    try:
        # Get a random audio file that needs transcription (now truly async)
        audio_file = await AudioService.get_random_audio_for_transcription(db)
        
        if not audio_file:
            raise HTTPException(
                status_code=404,
                detail="No audio files available for transcription"
            )
        
        # Generate signed URL for direct access to the audio file in GCS
        signed_url = await gcs_service.generate_signed_url(audio_file.audio_filename)
        
        logger.info(
            f"Serving audio file: {audio_file.audio_filename} "
            f"(transcriptions: {audio_file.transcription_count})"
        )
        
        return AudioResponse(
            audio_id=audio_file.audio_id,
            audio_filename=audio_file.audio_filename,
            google_transcription=audio_file.google_transcription,
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


@router.post(
    "/upload-csv",
    response_model=CSVUploadResult,
    summary="Upload CSV with audio transcriptions",
    description="Upload a CSV file containing audio filenames and their Google transcriptions"
)
async def upload_transcriptions_csv(
    file: UploadFile = File(..., description="CSV file with columns: filename, transcription"),
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Upload a CSV file containing audio transcriptions.
    
    Expected CSV format:
    - filename: Name of the audio file (maps to audio_filename)
    - transcription: Google transcription text (maps to google_transcription)
    
    This endpoint will:
    1. Parse the uploaded CSV file
    2. Insert new audio records or update existing ones
    3. Return statistics about the operation
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="File must be a CSV file"
            )
        
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Process the CSV (now truly async)
        inserted, skipped, skipped_files = await AudioService.bulk_insert_from_csv(
            db,
            csv_content,
        )

        total_records = inserted + skipped
        
        logger.info(
            f"CSV upload completed for file: {file.filename}. "
            f"Total: {total_records}, Inserted: {inserted}, Skipped: {skipped}"
        )
        
        return CSVUploadResult(
            total_records=total_records,
            inserted=inserted,
            skipped=skipped,
            skipped_files=skipped_files
        )
        
    except HTTPException:
        raise
    except UnicodeDecodeError:
        logger.error(f"Failed to decode CSV file: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Invalid file encoding. Please ensure the CSV file is UTF-8 encoded."
        )
    except Exception as e:
        logger.error(f"Error processing CSV upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while processing CSV: {str(e)}"
        )