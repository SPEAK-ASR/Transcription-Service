# Changelog

All notable changes to the Sinhala ASR Dataset Collection Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added
- Initial release of Sinhala ASR Dataset Collection Service
- FastAPI-based REST API with async support
- Web interface for audio transcription with built-in Sinhala phonetic keyboard
- Lease-based audio file assignment system to prevent race conditions
- PostgreSQL database integration with SQLAlchemy ORM
- Google Cloud Storage integration for audio file hosting
- Comprehensive transcription metadata collection:
  - Speaker gender identification
  - Background noise detection
  - Code-mixing (multiple languages) detection
  - Overlapping speaker detection
  - Audio suitability assessment
- CSV bulk import for audio file metadata
- Audio file comparison between cloud storage and database
- Signed URL generation for secure audio access
- Responsive web interface with custom audio player
- Docker containerization support
- Comprehensive API documentation
- Health check endpoints
- Proper error handling and logging
- Environment-based configuration management

### Features
- **Audio Management**: Lease-based assignment, priority queue, secure access
- **Transcription Collection**: Rich metadata, quality control, progress tracking
- **Web Interface**: Responsive design, custom audio player, Sinhala input support
- **API**: RESTful endpoints, OpenAPI documentation, type-safe validation
- **Deployment**: Docker support, cloud-ready, production configuration
- **Security**: CORS configuration, input validation, secure file access

### Technical Details
- FastAPI with async/await support
- PostgreSQL with asyncpg driver
- SQLAlchemy ORM with async support
- Pydantic for data validation and serialization
- Google Cloud Storage for file hosting
- HTML5 audio player with custom controls
- Built-in Sinhala phonetic keyboard (sin-phonetic-ime.js)
- Lease-based concurrency control using PostgreSQL FOR UPDATE SKIP LOCKED
- Environment variable configuration with validation
- Comprehensive error handling and logging
- Docker multi-stage build for optimized images
- Production-ready deployment configurations

### Documentation
- Comprehensive README with setup instructions
- API documentation with examples
- Deployment guide for various platforms
- Environment configuration examples
- Docker and docker-compose configurations
