# Sinhala ASR Dataset Collection Service

A comprehensive FastAPI service for collecting and managing Sinhala Automatic Speech Recognition (ASR) transcription data. The service provides a web interface for annotators to transcribe audio files with quality metadata, while ensuring data integrity through lease-based concurrency control.

## 🎯 Overview

This service facilitates the creation of high-quality Sinhala ASR datasets by:
- Serving audio files from Google Cloud Storage with secure signed URLs
- Collecting human transcriptions with comprehensive quality metadata
- Preventing race conditions through database-level lease management
- Prioritizing audio files with fewer existing transcriptions
- Supporting bulk audio metadata import via CSV files

## ✨ Key Features

### Audio Management
- **Lease-based Assignment**: Race-condition free audio file claiming using PostgreSQL's `FOR UPDATE SKIP LOCKED`
- **Priority Queue**: Automatically prioritizes audio files with fewer transcriptions
- **Secure Access**: Direct audio streaming via Google Cloud Storage signed URLs
- **Bulk Import**: CSV-based audio metadata import with duplicate detection

### Transcription Collection
- **Rich Metadata**: Speaker gender, background noise, code-mixing, and overlapping speaker detection
- **Audio Suitability**: Flag audio as unsuitable (corrupted, wrong language, etc.)
- **Quality Control**: Built-in validation and data integrity checks
- **Progress Tracking**: Real-time transcription count updates

### Web Interface
- **Responsive Design**: Modern, mobile-friendly transcription interface
- **Audio Player**: Custom HTML5 player with speed controls and replay functionality
- **Sinhala Input**: Built-in phonetic keyboard for users without Sinhala keyboards
- **Real-time Feedback**: Instant submission status and error handling

### Developer Experience
- **Async Architecture**: Full async/await support with SQLAlchemy and asyncpg
- **Type Safety**: Comprehensive Pydantic schemas with validation
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Clean Architecture**: Layered design with clear separation of concerns

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │────│   FastAPI App    │────│   PostgreSQL    │
│                 │    │                  │    │    Database     │
│ - HTML/CSS/JS   │    │ - REST API       │    │                 │
│ - Audio Player  │    │ - Web Routes     │    │ - Audio Records │
│ - Form Handling │    │ - Validation     │    │ - Transcriptions│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                       ┌──────────────────┐
                       │ Google Cloud     │
                       │ Storage          │
                       │                  │
                       │ - Audio Files    │
                       │ - Signed URLs    │
                       │ - File Metadata  │
                       └──────────────────┘
```

**Technology Stack:**
- **Backend**: FastAPI with async support
- **Database**: PostgreSQL with async SQLAlchemy and asyncpg driver
- **Storage**: Google Cloud Storage for audio file hosting
- **Frontend**: HTML5, CSS3, JavaScript with custom audio player
- **Authentication**: Google Cloud service account or ADC

## 📁 Project Structure

```
transcription_service/
├── app/
│   ├── main.py                     # FastAPI application entry point
│   ├── core/
│   │   ├── config.py               # Configuration management
│   │   ├── database.py             # Database connection and session management
│   │   └── gcp_auth.py             # Google Cloud authentication
│   ├── models/
│   │   └── __init__.py             # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── __init__.py             # Pydantic request/response schemas
│   ├── services/
│   │   ├── db_service.py           # Database service layer
│   │   └── gcs_service.py          # Google Cloud Storage service
│   ├── api/v1/
│   │   ├── api.py                  # API router configuration
│   │   └── endpoints/
│   │       ├── audio.py            # Audio-related endpoints
│   │       └── transcription.py    # Transcription endpoints
│   └── web/
│       └── routes.py               # Web UI routes
├── static/
│   ├── script.js                   # Frontend JavaScript
│   ├── sin-phonetic-ime.js         # Sinhala phonetic keyboard
│   └── style.css                   # Responsive CSS styles
├── templates/
│   └── transcription.html          # Main transcription interface
├── requirements.txt                # Python dependencies
├── run_server.py                   # Development server launcher
└── README.md                       # This file
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
# Database Configuration (Required)
DATABASE_URL=postgresql://username:password@host:port/database

# Google Cloud Storage (Required)
GCS_BUCKET_NAME=your-audio-bucket-name

# Authentication (Optional - uses ADC if not provided)
SERVICE_ACCOUNT_B64=base64_encoded_service_account_json

# Application Settings
DEBUG=true
AUDIO_LEASE_TIMEOUT_MINUTES=15
MAX_TRANSCRIPTIONS_PER_AUDIO=2
```

### 3. Database Setup

Ensure your PostgreSQL database has the required tables. The application uses SQLAlchemy models defined in `app/models/__init__.py`.

### 4. Google Cloud Setup

1. Create a Google Cloud Storage bucket for audio files
2. Set up authentication using one of:
   - Service account JSON (recommended for production)
   - Application Default Credentials (ADC) for development

### 5. Run the Application

```bash
# Development server with auto-reload
python run_server.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## 📚 API Reference

### Audio Endpoints

#### Get Random Audio for Transcription
```http
GET /api/v1/audio/random
```
Returns an audio file that needs transcription with a secure signed URL.

**Response:**
```json
{
  "audio_id": "uuid",
  "audio_filename": "example.wav",
  "google_transcription": "reference text",
  "transcription_count": 1,
  "gcs_signed_url": "https://signed-url"
}
```

#### Upload Audio Metadata CSV
```http
POST /api/v1/audio/upload-csv
Content-Type: multipart/form-data
```
Bulk import audio file metadata from CSV file.

**CSV Format:**
```csv
filename,transcription
audio1.wav,Optional reference transcription
audio2.wav,Another reference text
```

#### List All Files
```http
GET /api/v1/audio/files
```
Returns metadata for all files in the Google Cloud Storage bucket.

#### Compare Cloud vs Database
```http
GET /api/v1/audio/compare
```
Compares audio files in cloud storage with database records.

### Transcription Endpoints

#### Submit Transcription
```http
POST /api/v1/transcription/
Content-Type: application/json
```

**Request Body:**
```json
{
  "audio_id": "uuid",
  "transcription": "සිංහල transcription text",
  "speaker_gender": "male",
  "has_noise": false,
  "is_code_mixed": true,
  "is_speaker_overlappings_exist": false,
  "is_audio_suitable": true
}
```

## 🔧 Configuration Options

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | Required | PostgreSQL connection string |
| `GCS_BUCKET_NAME` | string | Required | Google Cloud Storage bucket name |
| `SERVICE_ACCOUNT_B64` | string | Optional | Base64 encoded service account JSON |
| `DEBUG` | boolean | false | Enable debug logging |
| `AUDIO_LEASE_TIMEOUT_MINUTES` | integer | 15 | Audio file lease timeout in minutes |
| `MAX_TRANSCRIPTIONS_PER_AUDIO` | integer | 2 | Maximum transcriptions per audio file |
| `SUPPORTED_AUDIO_FORMATS` | list | [".mp3", ".wav", ".m4a", ".ogg", ".flac"] | Supported audio file extensions |

## 🛡️ Data Models

### Audio Model
```python
class Audio:
    audio_id: UUID              # Primary key
    audio_filename: str         # Original filename
    google_transcription: str   # Reference transcription (optional)
    transcription_count: int    # Number of user transcriptions
    leased_until: datetime      # Lease expiration timestamp
```

### Transcription Model
```python
class Transcriptions:
    trans_id: UUID                      # Primary key
    audio_id: UUID                      # Foreign key to Audio
    transcription: str                  # User transcription text
    speaker_gender: str                 # male/female/cannot_recognized
    has_noise: bool                     # Background noise present
    is_code_mixed: bool                 # Multiple languages present
    is_speaker_overlappings_exist: bool # Overlapping speakers
    is_audio_suitable: bool             # Audio quality suitable
    created_at: datetime                # Creation timestamp
```

## 🔄 Lease-Based Concurrency

The service uses a sophisticated lease-based system to prevent race conditions:

1. **Audio Claiming**: Uses PostgreSQL's `FOR UPDATE SKIP LOCKED` to atomically claim audio files
2. **Lease Timeout**: Audio files are automatically released after the configured timeout
3. **Priority System**: Prioritizes audio files with fewer existing transcriptions
4. **Automatic Cleanup**: Completed transcriptions automatically release leases

## 🌐 Web Interface Features

### Audio Player
- Custom HTML5 audio player with full controls
- Variable playback speed (0.5x to 1.5x)
- Replay and seek functionality
- Volume control with mute option

### Sinhala Input Support
- Built-in phonetic keyboard for Sinhala input
- Quick language switching (Ctrl+Space)
- Visual language indicator

### Quality Metadata Collection
- Speaker gender identification
- Background noise detection
- Code-mixing (multiple languages) flagging
- Overlapping speaker detection
- Audio suitability assessment

## 🚀 Deployment

### Production Environment Variables
```env
DATABASE_URL=postgresql://user:pass@host:5432/db
GCS_BUCKET_NAME=production-audio-bucket
SERVICE_ACCOUNT_B64=eyJ0eXAiOiJKV1Q...
DEBUG=false
```

### Docker Deployment
```bash
# Build image
docker build -t sinhala-asr-service .

# Run container
docker run -d -p 8000:8000 --env-file .env sinhala-asr-service
```

### Health Checks
- **Health Endpoint**: `GET /health` - Basic health check
- **Database Connection**: Verified during application startup
- **GCS Access**: Validated through bucket operations

## 🔍 Monitoring and Logging

The application provides comprehensive logging for:
- Database operations and connection status
- Google Cloud Storage interactions
- Audio file lease management
- Transcription submissions and validation
- Error tracking and debugging information

Log levels can be controlled via the `DEBUG` environment variable.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Review the API documentation at `/docs`
- Check the application logs for detailed error information

---

Built with ❤️ for the Sinhala ASR research community

