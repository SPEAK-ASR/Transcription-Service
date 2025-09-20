"""
Pydantic schemas for API request/response models.

This module defines data validation and serialization schemas for the API
endpoints using Pydantic v2. All models include proper field validation,
documentation, and type hints.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


# Type definitions
SpeakerGender = Literal["male", "female", "cannot_recognized"]
AdminName = Literal["chirath", "rusira", "kokila", "sahan"]


class AudioResponse(BaseModel):
    """
    Response model for audio data.
    """
    audio_id: UUID
    audio_filename: str
    google_transcription: Optional[str] = None
    transcription_count: int = 0
    gcs_signed_url: str  # Signed URL for direct access
    
    model_config = ConfigDict(from_attributes=True)


class TranscriptionCreate(BaseModel):
    """
    Request model for creating a new transcription.
    """
    audio_id: UUID = Field(..., description="UUID of the audio being transcribed")
    transcription: str = Field(..., min_length=1, description="The transcribed text")
    speaker_gender: SpeakerGender = Field(..., description="Gender of the speaker")
    has_noise: bool = Field(default=False, description="Whether the audio contains noise")
    is_code_mixed: bool = Field(default=False, description="Whether the audio contains code-mixed content")
    is_speaker_overlappings_exist: bool = Field(default=False, description="Whether speakers are overlapping")
    is_audio_suitable: Optional[bool] = Field(default=True, description="Whether the audio is suitable for transcription")
    admin: Optional[AdminName] = Field(default=None, description="Admin attribution if submitted by an admin")
    is_validated: bool = Field(default=False, description="Whether the transcription is validated (True for admin submissions)")
    
    @field_validator("transcription")
    @classmethod
    def validate_transcription_text(cls, v: str, info) -> str:
        # If audio is not suitable, we allow a default transcription
        is_audio_suitable = info.data.get('is_audio_suitable', True)
        if is_audio_suitable is False:
            return v if v else "Audio not suitable for transcription"
        
        # For suitable audio, require actual transcription
        if not v or not v.strip():
            raise ValueError("Transcription text cannot be empty")
        return v.strip()


class TranscriptionResponse(BaseModel):
    """
    Response model for transcription data.
    """
    trans_id: UUID
    audio_id: UUID
    transcription: str
    speaker_gender: SpeakerGender
    has_noise: bool
    is_code_mixed: bool
    is_speaker_overlappings_exist: bool
    is_audio_suitable: Optional[bool]
    admin: Optional[AdminName]
    is_validated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TranscriptionValidationUpdate(BaseModel):
    """
    Request model for validating an existing transcription.
    """
    transcription: str = Field(..., min_length=1, description="Updated transcription text")
    speaker_gender: SpeakerGender = Field(..., description="Updated speaker gender")
    has_noise: bool = Field(default=False, description="Whether the audio contains noise")
    is_code_mixed: bool = Field(default=False, description="Whether the audio contains code-mixed content")
    is_speaker_overlappings_exist: bool = Field(default=False, description="Whether speakers are overlapping")
    is_audio_suitable: Optional[bool] = Field(default=True, description="Whether the audio remains suitable for transcription")
    admin: Optional[AdminName] = Field(default=None, description="Admin attribution if validated by an admin")

    @field_validator("transcription")
    @classmethod
    def validate_transcription_text(cls, v: str, info) -> str:
        is_audio_suitable = info.data.get('is_audio_suitable', True)
        if is_audio_suitable is False:
            return v if v else "Audio not suitable for transcription"
        if not v or not v.strip():
            raise ValueError("Transcription text cannot be empty")
        return v.strip()


class ValidationQueueItem(BaseModel):
    """
    Combined response payload for validation queue items.
    """
    audio: AudioResponse
    transcription: TranscriptionResponse

    model_config = ConfigDict(from_attributes=True)

class CSVUploadResult(BaseModel):
    """
    Response model for CSV upload results.
    """
    total_records: int = Field(..., description="Total number of records in the CSV")
    inserted: int = Field(..., description="Number of records successfully inserted")
    skipped: int = Field(..., description="Number of records skipped due to errors")
    skipped_files: List[dict] = Field(default=[], description="List of skipped filenames with indices")


class BulkAudioCreate(BaseModel):
    """
    Schema for bulk audio creation from CSV.
    """
    audio_filename: str = Field(..., description="The filename of the audio file")
    google_transcription: Optional[str] = Field(None, description="Google transcription text")


class ErrorResponse(BaseModel):
    """
    Response model for error messages.
    """
    error: str
    message: str
    details: Optional[str] = None


class FileMetadata(BaseModel):
    """
    Response model for file metadata.
    """
    filename: str = Field(..., description="The filename without path")
    full_path: str = Field(..., description="Full GCS path")
    size_bytes: int = Field(..., description="File size in bytes")
    size_mb: float = Field(..., description="File size in MB")
    content_type: str = Field(..., description="MIME type of the file")
    created_date: str = Field(..., description="File creation date")
    updated_date: str = Field(..., description="File last updated date")
    md5_hash: str = Field(..., description="MD5 hash of the file")
    is_audio_file: bool = Field(..., description="Whether the file is an audio file")


class FilesListResponse(BaseModel):
    """
    Response model for files list.
    """
    total_files: int = Field(..., description="Total number of files")
    audio_files: int = Field(..., description="Number of audio files")
    other_files: int = Field(..., description="Number of non-audio files")
    files: List[FileMetadata] = Field(..., description="List of file metadata")


class AudioFileComparisonItem(BaseModel):
    """
    Model for individual audio file in comparison.
    """
    filename: str = Field(..., description="Audio filename")
    full_path: Optional[str] = Field(None, description="Full GCS path if exists in cloud")
    size_bytes: Optional[int] = Field(None, description="File size in bytes if exists in cloud")
    size_mb: Optional[float] = Field(None, description="File size in MB if exists in cloud")
    audio_id: Optional[UUID] = Field(None, description="Database audio ID if exists in DB")
    transcription_count: Optional[int] = Field(None, description="Number of transcriptions if exists in DB")
    google_transcription: Optional[str] = Field(None, description="Google transcription if exists in DB")


class AudioComparisonResponse(BaseModel):
    """
    Response model for audio files comparison between cloud bucket and database.
    """
    summary: dict = Field(..., description="Summary statistics of the comparison")
    cloud_only_files: List[AudioFileComparisonItem] = Field(
        ..., description="Audio files that exist only in cloud bucket"
    )
    db_only_files: List[AudioFileComparisonItem] = Field(
        ..., description="Audio files that exist only in database"
    )
    matched_files_count: int = Field(..., description="Number of files that exist in both cloud and DB")


