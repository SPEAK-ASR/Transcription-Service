#!/usr/bin/env python
"""
Build script for Vercel deployment of FastAPI application.

This script runs during the build phase on Vercel, before the application
is deployed. It can be used for pre-deployment setup tasks.
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run build tasks for Vercel deployment."""
    try:
        logger.info("Starting Vercel build process...")
        
        # Task 1: Validate Python version
        logger.info(f"Python version: {sys.version}")
        if sys.version_info < (3, 11):
            logger.error("Python 3.11+ is required for this application")
            return 1
        
        # Task 2: Validate dependencies
        logger.info("Validating dependencies...")
        try:
            import fastapi
            import uvicorn
            import sqlalchemy
            import google.cloud.storage
            logger.info("✓ All critical dependencies are installed")
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            return 1
        
        # Task 3: Validate configuration
        logger.info("Validating application configuration...")
        try:
            from app.core.config import settings
            logger.info(f"✓ Application name: {settings.APP_NAME}")
            logger.info(f"✓ Application version: {settings.VERSION}")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return 1
        
        # Task 4: Check required environment variables
        logger.info("Checking required environment variables...")
        required_vars = ["DATABASE_URL", "GCS_BUCKET_NAME"]
        missing_vars = []
        unverifiable_vars = []
        
        from app.core.config import settings
        
        for var in required_vars:
            try:
                value = getattr(settings, var, None)
                if not value:
                    missing_vars.append(var)
                else:
                    logger.info(f"✓ {var} is configured")
            except Exception as e:
                unverifiable_vars.append(var)
                logger.error(f"Could not verify required environment variable {var}: {e}")
        
        if missing_vars:
            logger.error(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Set these in Vercel project settings before deploying."
            )
        
        if unverifiable_vars:
            logger.error(
                f"Could not verify required environment variables: {', '.join(unverifiable_vars)}."
            )
        
        if missing_vars or unverifiable_vars:
            return 1
        
        logger.info("✓ Build process completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Build process failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
