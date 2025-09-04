"""
Database models for the Sinhala ASR dataset service.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class SpeakerGender(enum.Enum):
    """
    Enum for speaker gender.
    """
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class Audio(Base):
    """
    Model for audio clips.
    """
    __tablename__ = "Audio"
    
    audio_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    audio_filename = Column(Text, nullable=False)
    google_transcription = Column(Text, nullable=True)
    transcription_count = Column(Integer, default=0)
    leased_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    transcriptions = relationship("Transcriptions", back_populates="audio")


class Transcriptions(Base):
    """
    Model for user transcriptions of audio clips.
    """
    __tablename__ = "Transcriptions"
    
    trans_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to audio
    audio_id = Column(UUID(as_uuid=True), ForeignKey("Audio.audio_id"), nullable=False)
    
    # Transcription data
    transcription = Column(Text, nullable=False)
    
    # Audio quality and content flags
    has_noise = Column(Boolean, default=False)
    is_code_mixed = Column(Boolean, default=False)
    
    # Speaker information
    is_speaker_overlapping = Column(Boolean, default=False)
    is_speaker_male = Column(Boolean, default=None, nullable=True)
    speaker_gender = Column(Enum(SpeakerGender), nullable=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    audio = relationship("Audio", back_populates="transcriptions")
