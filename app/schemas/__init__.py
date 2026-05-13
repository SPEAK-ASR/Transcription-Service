"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


# Type definitions
SpeakerGender = Literal["male", "female", "cannot_recognized"]
AdminName = Literal["chirath", "rusira", "kokila", "sahan"]


class AudioResponse(BaseModel):
    """Response model for audio data."""

    audio_id: UUID
    audio_filename: str
    google_transcription: Optional[str] = None
    speak_transcription: Optional[str] = None
    transcription_count: int = 0
    is_best_google: Optional[bool] = None
    gcs_signed_url: str

    model_config = ConfigDict(from_attributes=True)


class TranscriptionCreate(BaseModel):
    """Request model for creating a new transcription."""

    audio_id: UUID = Field(..., description="UUID of the audio being transcribed")
    transcription: str = Field(..., min_length=1, description="The transcribed text")
    speaker_gender: SpeakerGender = Field(..., description="Gender of the speaker")
    has_noise: bool = Field(default=False, description="Whether the audio contains noise")
    is_code_mixed: bool = Field(default=False, description="Whether the audio contains code-mixed content")
    is_speaker_overlappings_exist: bool = Field(default=False, description="Whether speakers are overlapping")
    is_audio_suitable: Optional[bool] = Field(default=True, description="Whether the audio is suitable for transcription")
    admin: Optional[AdminName] = Field(default=None, description="Admin attribution if submitted by an admin")
    validated_at: Optional[datetime] = Field(default=None, description="Timestamp when validated (set automatically for admin submissions)")
    is_best_google: Optional[bool] = Field(
        default=None,
        description="True if user copied Google reference, False if SPEAK, null if manual or identical refs",
    )

    @field_validator("transcription")
    @classmethod
    def validate_transcription_text(cls, v: str, info) -> str:
        is_audio_suitable = info.data.get('is_audio_suitable', True)
        if is_audio_suitable is False:
            return v if v else "Audio not suitable for transcription"

        if not v or not v.strip():
            raise ValueError("Transcription text cannot be empty")
        return v.strip()


class TranscriptionResponse(BaseModel):
    """Response model for transcription data."""

    trans_id: UUID
    audio_id: UUID
    transcription: str
    speaker_gender: Optional[SpeakerGender]
    has_noise: Optional[bool]
    is_code_mixed: Optional[bool]
    is_speaker_overlappings_exist: Optional[bool]
    is_audio_suitable: Optional[bool]
    admin: Optional[AdminName]
    validated_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
