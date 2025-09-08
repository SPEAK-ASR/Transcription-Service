# Sinhala ASR Dataset Service

FastAPI service to collect Sinhala Automatic Speech Recognition (ASR) transcriptions. It serves audio from Google Cloud Storage (GCS), assigns clips safely with a lease-based mechanism, and stores user transcriptions in PostgreSQL (e.g., Supabase).

## Features

- Race-condition safe audio claiming (lease + SKIP LOCKED)
- Prioritized assignment of low-annotated clips
- CSV import for audio metadata (filename + optional transcription)
- Signed URL delivery straight from GCS
- Clean async SQLAlchemy integration

## Architecture

- Backend: FastAPI (async)
- DB: PostgreSQL via SQLAlchemy (asyncpg)
- Storage: Google Cloud Storage

## Project Structure

```
app/
  main.py                 # FastAPI app + lifespan
  core/
    config.py             # Settings (Pydantic Settings)
    database.py           # Async engine + session helpers
    gcp_auth.py           # Service account handling (base64 or ADC)
  models/
    __init__.py           # SQLAlchemy models (Audio, Transcriptions)
  schemas/
    __init__.py           # Pydantic schemas
  services/
    db_service.py         # DB services (Audio/Transcription)
    gcs_service.py        # GCS utilities (list/sign URL)
  api/
    v1/api.py             # Router
    v1/endpoints/
      audio.py            # Audio + utility endpoints
      transcription.py     # Transcription endpoints
static/, templates/        # Web UI
run_server.py              # Local dev runner
requirements.txt
.env.example
```

## Quick Start

1) Environment

```
python -m venv .venv
.venv\Scripts\activate   # Windows
# or
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

2) Configure

Copy `.env.example` to `.env` and set values:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
GCS_BUCKET_NAME=<your_gcs_bucket>
# Optional if not using ADC locally
SERVICE_ACCOUNT_B64=<base64_of_service_account_json>
DEBUG=true
```

3) Run

```
python run_server.py
# or
uvicorn app.main:app --reload
```

Docs: http://localhost:8000/docs

## API Overview

- GET `/api/v1/audio/random` → Random audio needing transcription (with signed URL)
- POST `/api/v1/audio/upload-csv` (multipart file) → Import `filename,transcription`
- GET `/api/v1/audio/files` → All GCS files + metadata
- GET `/api/v1/audio/compare` → Compare GCS files vs DB rows
- POST `/api/v1/transcription/` → Submit user transcription
- Web UI: GET `/` (form), GET `/new-audio`

## Configuration

- `DATABASE_URL`: PostgreSQL connection string
- `GCS_BUCKET_NAME`: GCS bucket name
- `SERVICE_ACCOUNT_B64` (optional): Base64 service account JSON (production)
- `DEBUG`: Enable verbose logging
- `AUDIO_LEASE_TIMEOUT_MINUTES` (default 15)
- `MAX_TRANSCRIPTIONS_PER_AUDIO` (default 2)

## Notes

- The service uses a lease-based claim to safely select clips without collisions.
- CSV import skips blanks and existing filenames to avoid duplicates.

## License

Add your license here.

