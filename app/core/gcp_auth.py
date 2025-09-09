"""
Google Cloud Platform authentication management.

This module handles GCP authentication using base64-encoded service account
credentials or Application Default Credentials (ADC). It provides a centralized
way to manage credentials across the application with proper resource cleanup.
"""

import os
import base64
import json
import tempfile
import logging
from typing import Optional
import google.auth
from google.oauth2 import service_account
from google.cloud import storage

from app.core.config import settings

logger = logging.getLogger(__name__)

class GCPAuthManager:
    """
    Centralized Google Cloud Platform authentication manager.
    
    Handles authentication using either:
    1. Base64-encoded service account credentials from environment variables
    2. Application Default Credentials (ADC) as fallback
    
    Provides credential management, storage client creation, and proper
    resource cleanup for temporary credential files.
    """
    
    def __init__(self):
        """Initialize the auth manager with empty credential state."""
        self._credentials = None
        self._temp_file_path = None
    
    def setup_credentials(self) -> bool:
        """
        Setup GCP credentials from base64 encoded service account.
        
        Returns:
            bool: True if credentials were successfully set up, False otherwise
        """
        if not settings.SERVICE_ACCOUNT_B64:
            logger.warning("SERVICE_ACCOUNT_B64 not found in environment variables")
            logger.info("Falling back to default Google Cloud authentication (ADC)")
            return False
        
        try:
            # Decode the base64 service account
            service_account_json = base64.b64decode(settings.SERVICE_ACCOUNT_B64).decode('utf-8')
            service_account_info = json.loads(service_account_json)
            
            # Create credentials from service account info
            self._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Also create a temporary file for compatibility with some GCP libraries
            # that might expect GOOGLE_APPLICATION_CREDENTIALS to point to a file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(service_account_info, temp_file)
                self._temp_file_path = temp_file.name
            
            # Set environment variable for other GCP libraries
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self._temp_file_path
            
            logger.info("Successfully configured GCP credentials from base64 service account")
            return True
            
        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode service account from base64: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up GCP credentials: {e}")
            return False
    
    def get_credentials(self):
        """
        Get the configured credentials.
        
        Returns:
            google.oauth2.service_account.Credentials or None
        """
        return self._credentials
    
    def get_storage_client(self) -> storage.Client:
        """
        Get a Google Cloud Storage client with the configured credentials.
        
        Returns:
            google.cloud.storage.Client
        """
        # If credentials are already set up, use them
        if self._credentials:
            return storage.Client(credentials=self._credentials)
        
        # Try to set up credentials if we haven't attempted yet
        if not hasattr(self, '_setup_attempted'):
            self._setup_attempted = True
            if self.setup_credentials() and self._credentials:
                return storage.Client(credentials=self._credentials)
        
        # Fall back to creating a client without credentials
        # This will use Application Default Credentials or fail gracefully
        logger.info("Creating storage client without explicit credentials (using ADC)")
        
        # For development/testing, we might not have proper GCP setup
        # Create a client that won't fail during import but will fail on actual operations
        try:
            # Try with default credentials but don't auto-discover project to avoid file errors
            credentials, project = google.auth.default()
            return storage.Client(credentials=credentials, project=project)
        except Exception as e:
            logger.warning(f"Could not initialize with default credentials: {e}")
            # Return a client that will work for initialization but fail on actual GCS operations
            # This allows the app to start even without proper GCP setup
            return storage.Client(project="dummy-project")
    
    def cleanup(self):
        """
        Clean up temporary files and resources.
        """
        if self._temp_file_path and os.path.exists(self._temp_file_path):
            try:
                os.unlink(self._temp_file_path)
                logger.info("Cleaned up temporary service account file")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")
            finally:
                self._temp_file_path = None
        
        # Remove environment variable
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']


# Global auth manager instance
gcp_auth_manager = GCPAuthManager()
