"""
Google Cloud Storage service for audio file management.

This module provides high-level operations for interacting with Google Cloud
Storage, including file listing, metadata retrieval, and signed URL generation
for secure audio file access.
"""

import logging
from typing import Optional, List
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError
from datetime import timedelta

from app.core.config import settings
from app.core.gcp_auth import gcp_auth_manager

logger = logging.getLogger(__name__)


class GCSService:
    """
    Google Cloud Storage service with lazy initialization and caching.
    
    Provides methods for file operations, metadata retrieval, and signed URL
    generation. Uses lazy initialization to improve startup performance and
    handles authentication via the GCP auth manager.
    """
    
    def __init__(self):
        """Initialize with lazy-loaded client and bucket."""
        self._client = None
        self._bucket = None
    
    @property
    def client(self):
        """Lazy initialization of storage client."""
        if self._client is None:
            try:
                self._client = gcp_auth_manager.get_storage_client()
                logger.info("GCS client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._client
    
    @property 
    def bucket(self):
        """Lazy initialization of bucket."""
        if self._bucket is None:
            try:
                self._bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
                logger.info(f"GCS bucket '{settings.GCS_BUCKET_NAME}' initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GCS bucket '{settings.GCS_BUCKET_NAME}': {e}")
                raise
        return self._bucket
    

    
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
    
    async def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from the GCS bucket.
        
        Args:
            blob_name: Name/path of the blob in GCS to delete
            
        Returns:
            True if successfully deleted, False if blob not found
            
        Raises:
            GoogleCloudError: If there's an error deleting the blob
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Successfully deleted blob from GCS: {blob_name}")
            return True
            
        except NotFound:
            logger.warning(f"Blob not found for deletion: {blob_name}")
            return False
        except GoogleCloudError as e:
            logger.error(f"GCS error when deleting blob '{blob_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error when deleting blob '{blob_name}': {e}")
            raise
    
    async def bulk_delete_blobs(self, blob_names: List[str]) -> dict:
        """
        Delete multiple blobs from the GCS bucket.
        
        Args:
            blob_names: List of blob names/paths to delete
            
        Returns:
            Dictionary with deletion results:
            - successful: list of successfully deleted filenames
            - not_found: list of filenames not found in bucket
            - failed: list of tuples (filename, error_message) for failed deletions
            - summary: dict with counts
        """
        results = {
            'successful': [],
            'not_found': [],
            'failed': [],
        }
        
        for blob_name in blob_names:
            try:
                blob = self.bucket.blob(blob_name)
                blob.delete()
                results['successful'].append(blob_name)
                logger.info(f"Successfully deleted blob from GCS: {blob_name}")
                
            except NotFound:
                results['not_found'].append(blob_name)
                logger.warning(f"Blob not found for deletion: {blob_name}")
                
            except GoogleCloudError as e:
                error_msg = str(e)
                results['failed'].append((blob_name, error_msg))
                logger.error(f"GCS error when deleting blob '{blob_name}': {e}")
                
            except Exception as e:
                error_msg = str(e)
                results['failed'].append((blob_name, error_msg))
                logger.error(f"Unexpected error when deleting blob '{blob_name}': {e}")
        
        # Add summary
        results['summary'] = {
            'total_requested': len(blob_names),
            'successful_count': len(results['successful']),
            'not_found_count': len(results['not_found']),
            'failed_count': len(results['failed'])
        }
        
        logger.info(
            f"Bulk deletion completed: {results['summary']['successful_count']}/{len(blob_names)} successful, "
            f"{results['summary']['not_found_count']} not found, "
            f"{results['summary']['failed_count']} failed"
        )
        
        return results
    
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
        return await self._list_files(audio_only=False)

    async def list_all_audio_files(self) -> List[dict]:
        """
        List only audio files in the GCS bucket with their metadata.
        
        Returns:
            List of dictionaries containing audio file metadata
        """
        return await self._list_files(audio_only=True)

    async def _list_files(self, audio_only: bool = False) -> List[dict]:
        """
        Private method to list files in the GCS bucket with their metadata.
        
        Args:
            audio_only: If True, only return audio files. If False, return all files.
        
        Returns:
            List of dictionaries containing file metadata
        """
        try:
            # List all blobs in the bucket
            blobs = list(self.bucket.list_blobs())
            
            # Filter for audio files if requested
            if audio_only:
                blobs = [
                    blob for blob in blobs 
                    if any(blob.name.lower().endswith(fmt) for fmt in settings.SUPPORTED_AUDIO_FORMATS)
                ]
            
            files_metadata = []
            for blob in blobs:
                # Reload to get updated metadata
                blob.reload()
                
                file_metadata = {
                    'filename': blob.name.split('/')[-1],  # Just the filename without path
                    'full_path': blob.name,  # Full GCS path
                    'size_bytes': blob.size or 0,
                    'size_mb': round((blob.size or 0) / (1024 * 1024), 2),
                    'content_type': blob.content_type or 'unknown',
                    'created_date': blob.time_created.strftime('%Y-%m-%d %H:%M:%S') if blob.time_created else 'unknown',
                    'updated_date': blob.updated.strftime('%Y-%m-%d %H:%M:%S') if blob.updated else 'unknown',
                    'md5_hash': blob.md5_hash or 'unknown',
                }
                
                # Add is_audio_file flag only when listing all files (not audio-only)
                if not audio_only:
                    file_metadata['is_audio_file'] = any(
                        blob.name.lower().endswith(fmt) for fmt in settings.SUPPORTED_AUDIO_FORMATS
                    )
                
                files_metadata.append(file_metadata)
            
            # Sort by filename for consistent ordering
            files_metadata.sort(key=lambda x: x['filename'].lower())
            
            file_type = "audio files" if audio_only else "files"
            logger.info(f"Retrieved metadata for {len(files_metadata)} {file_type} from GCS bucket")
            return files_metadata
            
        except GoogleCloudError as e:
            error_type = "audio files" if audio_only else "files"
            logger.error(f"GCS error when listing {error_type}: {e}")
            raise
        except Exception as e:
            error_type = "audio files" if audio_only else "files"
            logger.error(f"Unexpected error when listing {error_type}: {e}")
            raise




# Create global GCS service instance
gcs_service = GCSService()
