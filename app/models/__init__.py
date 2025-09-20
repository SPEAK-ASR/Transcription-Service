"""
Database models for the Sinhala ASR Dataset Collection Service.

This module defines SQLAlchemy ORM models for audio files and transcriptions
with proper relationships, indexing, and data validation constraints.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Audio(Base):
    """
    Audio files available for transcription.
    
    This model represents audio clips stored in Google Cloud Storage that need
    to be transcribed by users. It includes lease-based assignment to prevent
    concurrent transcription conflicts.
    
    Attributes:
        audio_id: Unique identifier for the audio file
        audio_filename: Original filename of the audio file in GCS
        google_transcription: Reference transcription from Google Speech-to-Text (optional)
        transcription_count: Number of user transcriptions collected
        leased_until: Timestamp until which this audio is leased to a user
        transcriptions: Relationship to user transcriptions
    """
    __tablename__ = "Audio"
    
    audio_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    audio_filename = Column(Text, nullable=False, unique=True, index=True)
    google_transcription = Column(Text, nullable=True)
    transcription_count = Column(Integer, default=0, nullable=False, index=True)
    leased_until = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    transcriptions = relationship("Transcriptions", back_populates="audio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Audio(id={self.audio_id}, filename='{self.audio_filename}', transcriptions={self.transcription_count})>"


class Transcriptions(Base):
    """
    User transcriptions with metadata for audio quality assessment.
    
    This model stores transcriptions submitted by users along with metadata
    about audio quality, speaker characteristics, and content classification.
    
    Attributes:
        trans_id: Unique identifier for the transcription
        audio_id: Foreign key reference to the audio file
        transcription: User-provided transcription text
        speaker_gender: Gender classification of the speaker
        has_noise: Whether background noise is present
        is_code_mixed: Whether multiple languages are present
        is_speaker_overlappings_exist: Whether multiple speakers overlap
        is_audio_suitable: Whether audio is suitable for transcription
        admin: Admin who submitted the transcription (if any)
        is_validated: Whether the transcription is validated (True for admin submissions)
        created_at: Timestamp of transcription creation
        audio: Relationship back to the audio file
    """
    __tablename__ = "Transcriptions"
    
    trans_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key relationship
    audio_id = Column(UUID(as_uuid=True), ForeignKey("Audio.audio_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transcription content
    transcription = Column(Text, nullable=False)
    
    # Audio quality metadata
    has_noise = Column(Boolean, default=False, nullable=False)
    is_code_mixed = Column(Boolean, default=False, nullable=False)
    is_audio_suitable = Column(Boolean, nullable=True, default=True)
    
    # Speaker metadata
    is_speaker_overlappings_exist = Column(Boolean, default=False, nullable=False)
    speaker_gender = Column(
        Enum("male", "female", "cannot_recognized", name="speaker_gender_enum", create_type=False), 
        nullable=False, 
        default="cannot_recognized"
    )

    # Admin attribution (nullable). Enum type is assumed to exist in DB (Supabase)
    # with allowed values: chirath, rusira, kokila, sahan
    admin = Column(
        Enum("chirath", "rusira", "kokila", "sahan", name="admin_enum", create_type=False),
        nullable=True,
        default=None
    )
    
    # Validation status - True if submitted by admin, False otherwise
    is_validated = Column(Boolean, default=False, nullable=False, index=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    audio = relationship("Audio", back_populates="transcriptions")

    def __repr__(self):
        return f"<Transcription(id={self.trans_id}, audio_id={self.audio_id}, suitable={self.is_audio_suitable})>"
