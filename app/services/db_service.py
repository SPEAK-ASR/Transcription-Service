"""
Service layer for database operations with async support.
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID
from io import StringIO
import pandas as pd

from app.models import Audio, Transcriptions
from app.schemas import TranscriptionCreate

logger = logging.getLogger(__name__)


class AudioService:
    """Service for audio database operations."""

    @staticmethod
    async def get_audio_needing_transcription_prioritized(
        db: AsyncSession,
        limit: int = 10
    ) -> List[Audio]:
        """Get audio files that need transcriptions, prioritized by transcription count."""
        try:
            result = await db.execute(
                select(Audio)
                .where(Audio.transcription_count < 2)
                .order_by(Audio.transcription_count.asc())
                .limit(limit)
            )
            audio_files = result.scalars().all()
            logger.info(f"Retrieved {len(audio_files)} audio files needing transcription")
            return audio_files
        except Exception as e:
            logger.error(f"Error getting prioritized audio files: {e}")
            raise

    @staticmethod
    async def get_random_audio_for_transcription(db: AsyncSession) -> Optional[Audio]:
        """Get an audio file needing transcription (lowest transcription count)."""
        try:
            audio_files = await AudioService.get_audio_needing_transcription_prioritized(db=db, limit=1)
            audio = audio_files[0] if audio_files else None
            if audio:
                logger.info(f"Selected audio for transcription: {audio.audio_filename}")
            else:
                logger.info("No audio files available for transcription")
            return audio
        except Exception as e:
            logger.error(f"Error getting audio for transcription: {e}")
            raise

    @staticmethod
    async def bulk_insert_from_csv(db: AsyncSession, csv_content: str) -> Tuple[int, int, int, List[str]]:
        """Bulk insert audio records from CSV content."""
        inserted = 0
        skipped = 0
        skipped_files: List[str] = []

        try:
            df = pd.read_csv(StringIO(csv_content))

            required_columns = ['filename', 'transcription']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            for index, row in df.iterrows():
                try:
                    filename = str(row['filename']).strip()
                    transcription = str(row['transcription']).strip() if pd.notna(row['transcription']) else None

                    if not filename:
                        skipped += 1
                        skipped_files.append({
                            "row": index + 1,
                            "filename": filename
                        })
                        continue

                    # Try to insert new audio record
                    new_audio = Audio(
                        audio_filename=filename,
                        google_transcription=transcription,
                        transcription_count=0
                    )
                    db.add(new_audio)
                    await db.flush()  # Flush to catch unique constraint violations
                    inserted += 1
                    logger.info(f"Created new audio record: {filename}")

                except Exception as e:
                    # Handle unique constraint violation - just skip existing records
                    await db.rollback()
                    skipped += 1
                    logger.info(f"Skipped existing audio record: {filename}")
                    skipped_files.append({
                        "row": index + 1,
                        "filename": filename
                    })

            await db.commit()
            logger.info(f"Bulk insert completed: {inserted} inserted, {skipped} skipped")
            return inserted, skipped, skipped_files

        except Exception as e:
            await db.rollback()
            logger.error(f"Error during bulk insert: {e}")
            raise


class TranscriptionService:
    """Service for transcription database operations."""

    @staticmethod
    async def create_transcription(db: AsyncSession, transcription_data: TranscriptionCreate) -> Transcriptions:
        """Create a new transcription."""
        try:
            new_transcription = Transcriptions(
                audio_id=transcription_data.audio_id,
                transcription=transcription_data.transcription,
                speaker_gender=transcription_data.speaker_gender,
                has_noise=transcription_data.has_noise,
                is_code_mixed=transcription_data.is_code_mixed,
                is_speaker_overlapping=transcription_data.is_speaker_overlapping,
            )

            db.add(new_transcription)
            await db.commit()
            await db.refresh(new_transcription)

            logger.info(f"Created new transcription: {new_transcription.trans_id}")
            return new_transcription

        except Exception as e:
            logger.error(f"Error creating transcription: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_transcriptions_for_audio(db: AsyncSession, audio_id: UUID) -> List[Transcriptions]:
        """Get all transcriptions for a specific audio file."""
        try:
            result = await db.execute(select(Transcriptions).where(Transcriptions.audio_id == audio_id))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting transcriptions for audio: {e}")
            raise
