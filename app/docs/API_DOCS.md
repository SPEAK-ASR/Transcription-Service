# API Documentation

## Sinhala ASR Dataset Collection Service API

This document provides detailed information about the REST API endpoints provided by the Sinhala ASR Dataset Collection Service.

### Base URL
```
http://localhost:8000
```

### Authentication
The API uses Google Cloud Storage signed URLs for secure audio access. No additional authentication is required for the public endpoints.

---

## Audio Endpoints

### GET /api/v1/audio/random

Retrieves a random audio file that needs transcription with a secure signed URL.

**Response:**
```json
{
  "audio_id": "550e8400-e29b-41d4-a716-446655440000",
  "audio_filename": "sample_audio.wav",
  "google_transcription": "මම ඔබට කියන්නම්",
  "transcription_count": 1,
  "gcs_signed_url": "https://storage.googleapis.com/..."
}
```

**Status Codes:**
- `200 OK`: Audio file retrieved successfully
- `404 Not Found`: No audio files available for transcription
- `500 Internal Server Error`: Server error

---

### POST /api/v1/audio/upload-csv

Bulk import audio file metadata from CSV file.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (file): CSV file containing audio metadata

**CSV Format:**
```csv
filename,transcription
audio1.wav,සිංහල transcription
audio2.wav,Another transcription
```

**Response:**
```json
{
  "total_records": 100,
  "inserted": 95,
  "skipped": 5,
  "skipped_files": [
    {"row": 1, "filename": "duplicate.wav"},
    {"row": 5, "filename": "invalid.wav"}
  ]
}
```

**Status Codes:**
- `200 OK`: CSV processed successfully
- `400 Bad Request`: Invalid file format
- `500 Internal Server Error`: Processing error

---

### GET /api/v1/audio/files

Lists all files in the Google Cloud Storage bucket with metadata.

**Response:**
```json
{
  "total_files": 1500,
  "audio_files": 1200,
  "other_files": 300,
  "files": [
    {
      "filename": "audio1.wav",
      "full_path": "folder/audio1.wav",
      "size_bytes": 1048576,
      "size_mb": 1.0,
      "content_type": "audio/wav",
      "created_date": "2024-01-15 10:30:00",
      "updated_date": "2024-01-15 10:30:00",
      "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
      "is_audio_file": true
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Files listed successfully
- `500 Internal Server Error`: Storage access error

---

### GET /api/v1/audio/compare

Compares audio files in cloud storage with database records.

**Response:**
```json
{
  "summary": {
    "total_gcs_audio_files": 1200,
    "total_db_audio_records": 1150,
    "cloud_only_count": 50,
    "db_only_count": 0,
    "matched_count": 1150,
    "gcs_total_size_mb": 2400.5
  },
  "cloud_only_files": [
    {
      "filename": "new_audio.wav",
      "full_path": "folder/new_audio.wav",
      "size_bytes": 1048576,
      "size_mb": 1.0
    }
  ],
  "db_only_files": [],
  "matched_files_count": 1150
}
```

**Status Codes:**
- `200 OK`: Comparison completed successfully
- `500 Internal Server Error`: Comparison error

---

## Transcription Endpoints

### POST /api/v1/transcription/

Submit a user transcription with quality metadata.

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "audio_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcription": "මම ඔබට කියන්නම් මේ ගැන",
  "speaker_gender": "male",
  "has_noise": false,
  "is_code_mixed": true,
  "is_speaker_overlappings_exist": false,
  "is_audio_suitable": true
}
```

**Field Descriptions:**
- `audio_id` (UUID): ID of the audio file being transcribed
- `transcription` (string): The transcribed text
- `speaker_gender` (enum): "male", "female", or "cannot_recognized"
- `has_noise` (boolean): Whether background noise is present
- `is_code_mixed` (boolean): Whether multiple languages are present
- `is_speaker_overlappings_exist` (boolean): Whether speakers overlap
- `is_audio_suitable` (boolean): Whether audio is suitable for transcription

**Response:**
```json
{
  "trans_id": "660e8400-e29b-41d4-a716-446655440000",
  "audio_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcription": "මම ඔබට කියන්නම් මේ ගැන",
  "speaker_gender": "male",
  "has_noise": false,
  "is_code_mixed": true,
  "is_speaker_overlappings_exist": false,
  "is_audio_suitable": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `201 Created`: Transcription created successfully
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Audio file not found
- `500 Internal Server Error`: Server error

---

## Web UI Routes

### GET /

Main transcription interface with audio player and form.

**Response:** HTML page with embedded audio player and transcription form

---

### POST /submit-transcription

Web form submission endpoint for transcriptions.

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `audio_id`: UUID of the audio file
- `transcription`: Transcribed text
- `speaker_gender`: Speaker gender selection
- `has_noise`: Checkbox for noise presence
- `is_code_mixed`: Checkbox for code-mixed content
- `is_speaker_overlapping`: Checkbox for overlapping speakers
- `is_audio_suitable`: Checkbox for audio suitability

**Response:**
```json
{
  "success": true,
  "message": "Transcription submitted successfully!"
}
```

---

### GET /api/new-audio

AJAX endpoint to get a new random audio file.

**Response:**
```json
{
  "success": true,
  "audio": {
    "audio_id": "550e8400-e29b-41d4-a716-446655440000",
    "audio_filename": "new_audio.wav",
    "google_transcription": "Reference text",
    "transcription_count": 0,
    "gcs_signed_url": "https://storage.googleapis.com/..."
  }
}
```

---

## Health Check Endpoints

### GET /health

Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

### GET /

Root endpoint with service information.

**Response:**
```json
{
  "message": "Sinhala ASR Dataset Creation Service",
  "status": "active",
  "version": "1.0.0"
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `400 Bad Request`: Invalid input data
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production deployments.

---

## CORS Configuration

The service is configured to allow all origins (`*`) for development. Update `ALLOWED_HOSTS` in production for security.

---

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

These endpoints provide interactive documentation where you can test API endpoints directly from the browser.
