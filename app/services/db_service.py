"""
Service layer for database operations.
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from uuid import UUID
from io import StringIO
import pandas as pd

from app.models import Audio, Transcriptions
from app.schemas import TranscriptionCreate, BulkAudioCreate
from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioService:
    """
    Service for audio database operations.
    """

    @staticmethod
    async def get_audio_needing_transcription_prioritized(
        db: AsyncSession,
        limit: int = 10
    ) -> List[Audio]:
        """
        Get audio files that need transcriptions, prioritized by transcription count.
        Priority order: 0 transcriptions -> 1 transcription -> ... 
        """
        try:
            # Get audio files prioritized by transcription count (ascending)
            result = await db.execute(
                select(Audio)
                .where(Audio.transcription_count < 2)  # Each audio should get 2 transcriptions
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
    async def get_random_audio_for_transcription(
        db: AsyncSession
    ) -> Optional[Audio]:
        """
        Get an audio file that needs transcription, prioritized by transcription count.
        Returns the audio with the lowest transcription count.
        """
        try:
            # Get the audio file with the lowest transcription count
            audio_files = await AudioService.get_audio_needing_transcription_prioritized(
                db=db,
                limit=1
            )
            
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
    async def bulk_insert_from_csv(
        db: AsyncSession,
        csv_content: str
    ) -> Tuple[int, int, int, List[str]]:
        """
        Bulk insert audio records from CSV content.
        
        Args:
            db: Database session
            csv_content: CSV content as string
            
        Returns:
            Tuple of (inserted, updated, skipped, error_messages)
        """
        inserted = 0
        updated = 0
        skipped = 0
        errors = []
        
        try:
            # Parse CSV content
            df = pd.read_csv(StringIO(csv_content))
            
            # Validate required columns
            required_columns = ['filename', 'transcription']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    filename = str(row['filename']).strip()
                    transcription = str(row['transcription']).strip() if pd.notna(row['transcription']) else None
                    
                    # Skip empty filenames
                    if not filename:
                        skipped += 1
                        errors.append(f"Row {index + 1}: Empty filename")
                        continue
                    
                    # Check if audio already exists
                    result = await db.execute(
                        select(Audio).where(Audio.audio_filename == filename)
                    )
                    existing_audio = result.scalar_one_or_none()
                    
                    if existing_audio:
                        # Update existing record if transcription is provided and different
                        if transcription and existing_audio.google_transcription != transcription:
                            existing_audio.google_transcription = transcription
                            updated += 1
                            logger.info(f"Updated audio record: {filename}")
                        else:
                            skipped += 1
                    else:
                        # Create new audio record
                        new_audio = Audio(
                            audio_filename=filename,
                            google_transcription=transcription,
                            transcription_count=0
                        )
                        db.add(new_audio)
                        inserted += 1
                        logger.info(f"Created new audio record: {filename}")
                        
                except Exception as e:
                    skipped += 1
                    error_msg = f"Row {index + 1}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Error processing row {index + 1}: {e}")
            
            # Commit all changes
            await db.commit()
            
            logger.info(f"Bulk insert completed: {inserted} inserted, {updated} updated, {skipped} skipped")
            return inserted, updated, skipped, errors
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error during bulk insert: {e}")
            raise


class TranscriptionService:
    """
    Service for transcription database operations.
    """
    
    @staticmethod
    async def create_transcription(
        db: AsyncSession,
        transcription_data: TranscriptionCreate
    ) -> Transcriptions:
        """
        Create a new transcription.
        """
        try:
            new_transcription = Transcriptions(
                audio_id=transcription_data.audio_id,
                transcription=transcription_data.transcription,
                speaker_gender=transcription_data.speaker_gender,
                has_noise=transcription_data.has_noise,
                is_code_mixed=transcription_data.is_code_mixed,
                is_speaker_overlapping=transcription_data.is_speaker_overlapping
            )
            
            db.add(new_transcription)
            await db.commit()
            await db.refresh(new_transcription)
            
            # Note: transcription_count is automatically updated by database trigger
            
            logger.info(f"Created new transcription: {new_transcription.trans_id}")
            return new_transcription
            
        except Exception as e:
            logger.error(f"Error creating transcription: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_transcriptions_for_audio(
        db: AsyncSession,
        audio_id: UUID
    ) -> List[Transcriptions]:
        """
        Get all transcriptions for a specific audio file.
        """
        try:
            result = await db.execute(
                select(Transcriptions)
                .where(Transcriptions.audio_id == audio_id)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting transcriptions for audio: {e}")
            raise
