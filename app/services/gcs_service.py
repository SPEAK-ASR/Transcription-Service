"""
Service layer for Google Cloud Storage operations.
"""

import logging
from typing import Optional, List
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError
from datetime import timedelta
import random

from app.core.config import settings

logger = logging.getLogger(__name__)


class GCSService:
    """
    Service for Google Cloud Storage operations.
    """
    
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
    
    async def get_random_audio_clip(self, exclude_clip_ids: Optional[List[str]] = None) -> Optional[dict]:
        """
        Get a random audio clip from the GCS bucket.
        
        Args:
            exclude_clip_ids: List of clip IDs to exclude from selection
            
        Returns:
            Dictionary with clip metadata or None if no clips found
        """
        try:
            # List all blobs in the bucket
            blobs = list(self.bucket.list_blobs())
            
            # Filter for audio files
            audio_blobs = [
                blob for blob in blobs 
                if any(blob.name.lower().endswith(fmt) for fmt in settings.SUPPORTED_AUDIO_FORMATS)
            ]
            
            if not audio_blobs:
                logger.warning("No audio files found in GCS bucket")
                return None
            
            # Filter out excluded clips if provided
            if exclude_clip_ids:
                audio_blobs = [
                    blob for blob in audio_blobs 
                    if self._extract_clip_id_from_path(blob.name) not in exclude_clip_ids
                ]
            
            if not audio_blobs:
                logger.warning("No available audio files after filtering exclusions")
                return None
            
            # Select random blob
            selected_blob = random.choice(audio_blobs)
            
            return {
                'clip_id': self._extract_clip_id_from_path(selected_blob.name),
                'gcs_path': selected_blob.name,
                'filename': selected_blob.name.split('/')[-1],
                'file_size_bytes': selected_blob.size,
                'audio_format': selected_blob.name.split('.')[-1].lower(),
                'blob': selected_blob
            }
            
        except GoogleCloudError as e:
            logger.error(f"GCS error when fetching random clip: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error when fetching random clip: {e}")
            raise
    
    async def generate_signed_url(self, blob_name: str, expiration_hours: int = 1) -> str:
        """
        Generate a signed URL for accessing a blob.
        
        Args:
            blob_name: Name/path of the blob in GCS
            expiration_hours: Hours until URL expires
            
        Returns:
            Signed URL string
        """
        try:
            blob = self.bucket.blob(blob_name)
            
            # Generate signed URL
            signed_url = blob.generate_signed_url(
                expiration=timedelta(hours=expiration_hours),
                method='GET'
            )
            
            return signed_url
            
        except GoogleCloudError as e:
            logger.error(f"GCS error when generating signed URL: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error when generating signed URL: {e}")
            raise
    
    async def get_blob_metadata(self, blob_name: str) -> Optional[dict]:
        """
        Get metadata for a specific blob.
        
        Args:
            blob_name: Name/path of the blob in GCS
            
        Returns:
            Dictionary with blob metadata or None if not found
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()
            
            return {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated,
                'md5_hash': blob.md5_hash
            }
            
        except NotFound:
            logger.warning(f"Blob not found: {blob_name}")
            return None
        except GoogleCloudError as e:
            logger.error(f"GCS error when getting blob metadata: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting blob metadata: {e}")
            raise
    
    async def list_all_files(self) -> List[dict]:
        """
        List all files in the GCS bucket with their metadata.
        
        Returns:
            List of dictionaries containing file metadata
        """
        try:
            # List all blobs in the bucket
            blobs = list(self.bucket.list_blobs())
            
            files_metadata = []
            for blob in blobs:
                # Reload to get updated metadata
                blob.reload()
                
                files_metadata.append({
                    'filename': blob.name.split('/')[-1],  # Just the filename without path
                    'full_path': blob.name,  # Full GCS path
                    'size_bytes': blob.size or 0,
                    'size_mb': round((blob.size or 0) / (1024 * 1024), 2),
                    'content_type': blob.content_type or 'unknown',
                    'created_date': blob.time_created.strftime('%Y-%m-%d %H:%M:%S') if blob.time_created else 'unknown',
                    'updated_date': blob.updated.strftime('%Y-%m-%d %H:%M:%S') if blob.updated else 'unknown',
                    'md5_hash': blob.md5_hash or 'unknown',
                    'is_audio_file': any(blob.name.lower().endswith(fmt) for fmt in settings.SUPPORTED_AUDIO_FORMATS)
                })
            
            # Sort by filename for consistent ordering
            files_metadata.sort(key=lambda x: x['filename'].lower())
            
            logger.info(f"Retrieved metadata for {len(files_metadata)} files from GCS bucket")
            return files_metadata
            
        except GoogleCloudError as e:
            logger.error(f"GCS error when listing files: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error when listing files: {e}")
            raise

    def _extract_clip_id_from_path(self, gcs_path: str) -> str:
        """
        Extract clip ID from GCS path.
        Assumes format like: folder/subfolder/clip_id.ext
        """
        filename = gcs_path.split('/')[-1]
        return filename.split('.')[0]  # Remove extension


# Create global GCS service instance
gcs_service = GCSService()
