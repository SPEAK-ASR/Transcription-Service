"""
Pydantic schemas for request/response models.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class SpeakerGender(str, Enum):
    """
    Enum for speaker gender.
    """
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AudioResponse(BaseModel):
    """
    Response model for audio data.
    """
    audio_id: UUID
    audio_filename: str
    google_transcription: Optional[str] = None
    transcription_count: int = 0
    gcs_signed_url: str  # Signed URL for direct access
    
    class Config:
        from_attributes = True


class TranscriptionCreate(BaseModel):
    """
    Request model for creating a new transcription.
    """
    audio_id: UUID = Field(..., description="UUID of the audio being transcribed")
    transcription: str = Field(..., min_length=1, description="The transcribed text")
    speaker_gender: SpeakerGender = Field(..., description="Gender of the speaker")
    has_noise: bool = Field(default=False, description="Whether the audio contains noise")
    is_code_mixed: bool = Field(default=False, description="Whether the audio contains code-mixed content")
    is_speaker_overlapping: bool = Field(default=False, description="Whether speakers are overlapping")
    
    @validator('transcription')
    def validate_transcription_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Transcription text cannot be empty')
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
    is_speaker_overlapping: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


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
