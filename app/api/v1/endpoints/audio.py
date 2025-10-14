"""
Audio API endpoints for the Sinhala ASR Dataset Collection Service.

This module provides REST API endpoints for:
- Retrieving audio files for transcription
- Uploading CSV files with audio metadata
- Listing files and metadata from Google Cloud Storage
- Comparing cloud storage with database records
- Bulk deleting audio files from Google Cloud Storage
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_database_session
from app.schemas import (
    AudioResponse,
    CSVUploadResult,
    FilesListResponse,
    AudioComparisonResponse,
    AudioFileComparisonItem,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
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
    "/compare",
    response_model=AudioComparisonResponse,
    summary="Compare audio files between cloud bucket and database",
    description="Compares audio files in GCS bucket with audio records in database and returns differences"
)
async def compare_audio_files(
    db: AsyncSession = Depends(get_async_database_session)
):
    """
    Compare audio files between Google Cloud Storage bucket and database.
    
    This endpoint:
    1. Gets all audio files from GCS bucket
    2. Gets all audio records from database 
    3. Compares them and returns:
       - Files that exist only in cloud bucket (not in database)
       - Files that exist only in database (not in cloud bucket)
       - Summary statistics
    """
    try:
        # Get all audio files from GCS bucket
        logger.info("Fetching audio files from GCS bucket...")
        gcs_audio_files = await gcs_service.list_all_audio_files()
        
        # Get all audio records from database
        logger.info("Fetching audio records from database...")
        db_audio_files = await AudioService.get_all_audio_files(db)
        
        # Create sets of filenames for comparison
        gcs_filenames = {file['filename'] for file in gcs_audio_files}
        db_filenames = {audio.audio_filename for audio in db_audio_files}
        
        # Find files that exist only in GCS (not in DB)
        cloud_only_filenames = gcs_filenames - db_filenames
        cloud_only_files = []
        for gcs_file in gcs_audio_files:
            if gcs_file['filename'] in cloud_only_filenames:
                cloud_only_files.append(AudioFileComparisonItem(
                    filename=gcs_file['filename'],
                    full_path=gcs_file['full_path'],
                    size_bytes=gcs_file['size_bytes'],
                    size_mb=gcs_file['size_mb']
                ))
        
        # Find files that exist only in DB (not in GCS)
        db_only_filenames = db_filenames - gcs_filenames
        db_only_files = []
        for db_audio in db_audio_files:
            if db_audio.audio_filename in db_only_filenames:
                db_only_files.append(AudioFileComparisonItem(
                    filename=db_audio.audio_filename,
                    audio_id=db_audio.audio_id,
                    transcription_count=db_audio.transcription_count,
                    google_transcription=db_audio.google_transcription
                ))
        
        # Calculate matched files
        matched_files_count = len(gcs_filenames & db_filenames)
        
        # Create summary statistics
        summary = {
            "total_gcs_audio_files": len(gcs_audio_files),
            "total_db_audio_records": len(db_audio_files),
            "cloud_only_count": len(cloud_only_files),
            "db_only_count": len(db_only_files),
            "matched_count": matched_files_count,
            "gcs_total_size_mb": round(sum(f['size_mb'] for f in gcs_audio_files), 2)
        }
        
        logger.info(
            f"Audio comparison completed: "
            f"GCS={len(gcs_audio_files)}, DB={len(db_audio_files)}, "
            f"Cloud-only={len(cloud_only_files)}, DB-only={len(db_only_files)}, "
            f"Matched={matched_files_count}"
        )
        
        return AudioComparisonResponse(
            summary=summary,
            cloud_only_files=cloud_only_files,
            db_only_files=db_only_files,
            matched_files_count=matched_files_count
        )
        
    except Exception as e:
        logger.error(f"Error comparing audio files: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while comparing audio files"
        )


@router.post(
    "/bulk-delete",
    response_model=BulkDeleteResponse,
    summary="Bulk delete audio files from GCS bucket",
    description="Delete multiple audio files from Google Cloud Storage bucket by providing a list of filenames"
)
async def bulk_delete_audio_files(
    request: BulkDeleteRequest
):
    """
    Bulk delete audio files from Google Cloud Storage bucket.
    
    This endpoint:
    1. Accepts a list of audio filenames to delete
    2. Attempts to delete each file from the GCS bucket
    3. Returns detailed results for each file:
       - Successfully deleted files
       - Files not found in bucket
       - Files that failed to delete (with error messages)
    
    **Note:** This operation is permanent and cannot be undone.
    Files are deleted from cloud storage only, database records are not affected.
    
    Example request body:
    ```json
    {
        "filenames": [
            "14Ykn2QXnQ0-001.wav",
            "14Ykn2QXnQ0-011.wav",
            "audio_sample.mp3"
        ]
    }
    ```
    """
    try:
        if not request.filenames:
            raise HTTPException(
                status_code=400,
                detail="Filenames list cannot be empty"
            )
        
        logger.info(f"Starting bulk deletion of {len(request.filenames)} files from GCS bucket")
        
        # Perform bulk deletion
        results = await gcs_service.bulk_delete_blobs(request.filenames)
        
        # Format failed results for response
        failed_formatted = [
            {
                "filename": filename,
                "error": error_msg
            }
            for filename, error_msg in results['failed']
        ]
        
        logger.info(
            f"Bulk deletion completed: {results['summary']['successful_count']} successful, "
            f"{results['summary']['not_found_count']} not found, "
            f"{results['summary']['failed_count']} failed"
        )
        
        return BulkDeleteResponse(
            summary=results['summary'],
            successful=results['successful'],
            not_found=results['not_found'],
            failed=failed_formatted
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during bulk deletion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during bulk deletion: {str(e)}"
        )

