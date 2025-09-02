# Sinhala ASR Dataset Creation Service

FastAPI application for creating Sinhala Automatic Speech Recognition (ASR) datasets through crowd-sourced transcription collection.

## Features

- **Random Audio Serving**: Serves random audio clips from Google Cloud Storage with intelligent prioritization
- **Transcription Collection**: Collects user transcriptions with metadata (speaker gender, noise detection, code-mixing)
- **Duplicate Tracking**: Ensures each audio clip is transcribed by 2 different users (configurable)
- **Smart Prioritization**: Prioritizes clips with fewer annotations for balanced dataset creation
- **Supabase Integration**: Uses Supabase (PostgreSQL) for reliable, scalable database operations

## Architecture

- **Backend**: FastAPI with async/await support
- **Database**: Supabase (PostgreSQL) with SQLAlchemy ORM
- **Storage**: Google Cloud Storage for audio files
- **Lightweight**: Only essential endpoints for core functionality

## Project Structure

```
transcription_service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   └── database.py        # Supabase database connection and setup
│   ├── models/
│   │   └── __init__.py        # SQLAlchemy models (Audio, Transcriptions)
│   ├── schemas/
│   │   └── __init__.py        # Pydantic schemas
│   ├── services/
│   │   ├── gcs_service.py     # Google Cloud Storage operations
│   │   └── db_service.py      # Database operations (AudioService, TranscriptionService)
│   └── api/
│       └── v1/
│           ├── api.py         # API router configuration
│           └── endpoints/
│               ├── audio.py       # Audio serving endpoints
│               └── transcription.py # Transcription collection endpoints
├── requirements.txt
├── .env.example
├── test_db_connection.py      # Database connection test script
└── README.md
```

## Setup

### 1. Environment Setup

```bash
# Clone and navigate to the project
cd transcription_service

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Supabase Database Setup

1. **Create Supabase Project**:
   - Go to [Supabase](https://supabase.com) and create a new project
   - Wait for the database to be provisioned

2. **Get Database Credentials**:
   - Go to Settings > Database in your Supabase dashboard
   - Copy the connection details:
     - Host
     - Database name
     - Username
     - Password
     - Port (usually 5432)

3. **Create Tables**:
   The tables should already be created in your Supabase database. If not, you can create them using the SQL editor in Supabase dashboard:

### 3. Google Cloud Storage Setup

1. Create a GCS bucket for audio files
2. Create a service account with Storage Object Viewer permissions
3. Download the service account key JSON file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### 4. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your Supabase credentials
USER=your_supabase_user
PASSWORD=your_supabase_password
HOST=your_supabase_host
PORT=5432
DBNAME=postgres
GCS_BUCKET_NAME=your_gcs_bucket_name
DEBUG=true
```

### 5. Test Database Connection

```bash
# Test your database connection
python test_db_connection.py
```

If successful, you should see:
```
✅ Database connection test completed successfully!
Your Supabase connection is properly configured.
```

### 6. Run the Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Endpoints

### Audio Endpoints
- `GET /api/v1/audio/random` - Get a random audio clip for transcription (prioritized by transcription count)
- `POST /api/v1/audio/upload-csv` - Upload CSV file with audio filenames and Google transcriptions

### Transcription Endpoints
- `POST /api/v1/transcription/` - Submit a user transcription with metadata

### Health Check
- `GET /` - Root endpoint with service information
- `GET /health` - Health check endpoint

## Usage Examples

### 1. Get a random audio clip
```bash
curl "http://localhost:8000/api/v1/audio/random"
```

Response:
```json
{
  "audio_id": "550e8400-e29b-41d4-a716-446655440000",
  "audio_filename": "audio_001.wav",
  "google_transcription": "මේ සිංහල කතාවකි",
  "transcription_count": 0,
  "gcs_signed_url": "https://storage.googleapis.com/..."
}
```

### 2. Submit transcription
```bash
curl -X POST "http://localhost:8000/api/v1/transcription/" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_id": "550e8400-e29b-41d4-a716-446655440000",
    "transcription": "මේ ශ්‍රී ලංකාවේ ප්‍රධාන නගරයක්.",
    "speaker_gender": "male",
    "has_noise": false,
    "is_code_mixed": false,
    "is_speaker_overlapping": false
  }'
```

### 3. Upload audio metadata via CSV
```bash
curl -X POST "http://localhost:8000/api/v1/audio/upload-csv" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio_metadata.csv"
```

## Database Models

### Audio
- `audio_id`: UUID primary key
- `audio_filename`: Name of the audio file
- `google_transcription`: Google Cloud Speech-to-Text transcription (optional)
- `transcription_count`: Number of user transcriptions (automatically updated)

### Transcriptions
- `trans_id`: UUID primary key
- `audio_id`: Foreign key to Audio table
- `transcription`: User-provided transcription text
- `speaker_gender`: Gender of the speaker (male/female/unknown)
- `has_noise`: Boolean flag for noisy audio
- `is_code_mixed`: Boolean flag for code-mixed content
- `is_speaker_overlapping`: Boolean flag for overlapping speakers
- `created_at`: Timestamp of transcription creation

## Configuration Options

Key environment variables:

- `USER`: Supabase database username
- `PASSWORD`: Supabase database password
- `HOST`: Supabase database host
- `PORT`: Database port (usually 5432)
- `DBNAME`: Database name (usually 'postgres')
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name
- `DEBUG`: Enable debug mode (true/false)
- `ANNOTATIONS_PER_CLIP`: Number of transcriptions required per clip (default: 2)

## Development

### Running Tests
```bash
# Test database connection
python test_db_connection.py

# Run application tests (if available)
pytest
```

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

### Database Operations

The service includes two main service classes:

1. **AudioService**: Handles audio file operations
   - `get_random_audio_for_transcription()`: Get prioritized audio for transcription
   - `bulk_insert_from_csv()`: Bulk insert audio metadata from CSV

2. **TranscriptionService**: Handles transcription operations
   - `create_transcription()`: Create new user transcription
   - `get_transcriptions_for_audio()`: Get all transcriptions for an audio file

## Troubleshooting

### Database Connection Issues
1. Verify Supabase credentials in `.env` file
2. Check if your Supabase project is running
3. Ensure your IP is allowed in Supabase network settings
4. Test connection using `test_db_connection.py`

### Common Errors
- **"Import could not be resolved"**: Make sure virtual environment is activated and packages are installed
- **"Database connection failed"**: Check Supabase credentials and network connectivity
- **"Table not found"**: Ensure tables are created in Supabase dashboard

## Deployment

### Docker Deployment
Create a `Dockerfile` and `docker-compose.yml` for containerized deployment.

### Cloud Deployment
The application is ready for deployment on cloud platforms like:
- Vercel (with Supabase)
- Heroku (with Supabase)
- Google Cloud Run
- AWS ECS
- Azure Container Instances

## Contributing

1. Follow the existing code structure and patterns
2. Add proper logging for new features
3. Include error handling for all external service calls
4. Update tests for new functionality
5. Document any new configuration options

## License

[Add your license information here]
