"""
Audio endpoints for serving random audio clips.
"""

import logging
import io
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_database_session
from app.schemas import AudioResponse, CSVUploadResult, FilesListResponse
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


@router.get(
    "/files",
    response_model=FilesListResponse,
    summary="Get all files metadata",
    description="Returns metadata for all files in the Google Cloud Storage bucket"
)
async def get_all_files_metadata():
    """
    Get metadata for all files in the GCS bucket.
    
    This endpoint returns information about all files including:
    - File names and paths
    - File sizes (in bytes and MB)
    - Content types
    - Creation and modification dates
    - Whether the file is an audio file
    """
    try:
        # Get all files metadata from GCS
        files_metadata = await gcs_service.list_all_files()
        
        # Calculate statistics
        total_files = len(files_metadata)
        audio_files = sum(1 for f in files_metadata if f['is_audio_file'])
        other_files = total_files - audio_files
        
        logger.info(
            f"Retrieved metadata for {total_files} files "
            f"({audio_files} audio, {other_files} other)"
        )
        
        return FilesListResponse(
            total_files=total_files,
            audio_files=audio_files,
            other_files=other_files,
            files=files_metadata
        )
        
    except Exception as e:
        logger.error(f"Error retrieving files metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving files metadata"
        )


@router.get(
    "/files/csv",
    summary="Download files metadata as CSV",
    description="Downloads all files metadata as a CSV file"
)
async def download_files_metadata_csv():
    """
    Download all files metadata as a CSV file.
    
    This endpoint generates and returns a CSV file containing:
    - filename: The filename without path
    - full_path: Complete GCS path
    - size_bytes: File size in bytes
    - size_mb: File size in megabytes
    - content_type: MIME type
    - created_date: File creation date
    - updated_date: File last modified date
    - md5_hash: MD5 hash of the file
    - is_audio_file: Boolean indicating if it's an audio file
    """
    try:
        # Get all files metadata from GCS
        files_metadata = await gcs_service.list_all_files()
        
        # Create CSV content
        csv_content = io.StringIO()
        
        # Write CSV header
        headers = [
            'filename', 'full_path', 'size_bytes', 'size_mb', 
            'content_type', 'created_date', 'updated_date', 
            'md5_hash', 'is_audio_file'
        ]
        csv_content.write(','.join(headers) + '\n')
        
        # Write data rows
        for file_metadata in files_metadata:
            row = [
                f'"{file_metadata["filename"]}"',
                f'"{file_metadata["full_path"]}"',
                str(file_metadata["size_bytes"]),
                str(file_metadata["size_mb"]),
                f'"{file_metadata["content_type"]}"',
                f'"{file_metadata["created_date"]}"',
                f'"{file_metadata["updated_date"]}"',
                f'"{file_metadata["md5_hash"]}"',
                str(file_metadata["is_audio_file"]).lower()
            ]
            csv_content.write(','.join(row) + '\n')
        
        # Create response
        csv_string = csv_content.getvalue()
        csv_content.close()
        
        # Create a streaming response
        response = StreamingResponse(
            io.StringIO(csv_string),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gcs_files_metadata.csv"}
        )
        
        logger.info(f"Generated CSV with {len(files_metadata)} file records")
        return response
        
    except Exception as e:
        logger.error(f"Error generating files CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while generating CSV"
        )