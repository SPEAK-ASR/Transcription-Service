#!/usr/bin/env python3
"""
Development server launcher for Sinhala ASR Dataset Collection Service.

This script provides a convenient way to run the FastAPI application in
development mode with automatic reloading and proper configuration validation.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Ensure the app module can be imported
sys.path.insert(0, str(Path(__file__).parent))


def check_environment() -> bool:
    """Check if the environment is properly configured."""
    env_file = Path(__file__).parent / '.env'
    
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("   Please copy .env.example to .env and configure your settings.")
        print("   Required settings: DATABASE_URL, GCS_BUCKET_NAME")
        return False
    
    # Check for required environment variables
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    required_vars = ['DATABASE_URL', 'GCS_BUCKET_NAME']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Warning: Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True


def main():
    """Main entry point for the development server."""
    print("🎯 Sinhala ASR Dataset Collection Service")
    print("=" * 60)
    
    # Check environment configuration
    if check_environment():
        print("✅ Environment configuration validated")
    else:
        print("❌ Environment configuration issues detected")
        print("   The application may not work correctly.")
    
    print()
    print("🌐 Server will be available at:")
    print("   - Main Interface: http://localhost:8000")
    print("   - API Documentation (Swagger): http://localhost:8000/docs")
    print("   - API Documentation (ReDoc): http://localhost:8000/redoc")
    print("   - Health Check: http://localhost:8000/health")
    print()
    print("📝 Development Features:")
    print("   - Auto-reload on code changes")
    print("   - Detailed error messages")
    print("   - Debug logging enabled")
    print()
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True,
            reload_dirs=["app", "static", "templates"]
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
