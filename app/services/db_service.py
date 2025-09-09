"""
Database service layer for audio and transcription operations.

This module provides high-level database operations with proper error handling,
transaction management, and concurrency safety. All operations use async
SQLAlchemy sessions for optimal performance.
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from uuid import UUID
from io import StringIO
import pandas as pd

from app.models import Audio, Transcriptions
from app.schemas import TranscriptionCreate
from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioService:
    """Service for audio database operations."""



    @staticmethod
    async def claim_audio_for_transcription(db: AsyncSession) -> Optional[Audio]:
        """
        Atomically claim an audio file for transcription using lease-based system.
        
        This method uses PostgreSQL's FOR UPDATE SKIP LOCKED to safely claim
        an audio file without race conditions. It prioritizes files with fewer
        existing transcriptions and ensures proper lease management.
        
        Process:
        1. Find available audio files (transcription_count < max, lease expired)
        2. Order by transcription_count to prioritize less-transcribed files
        3. Lock and claim one row atomically
        4. Set lease expiration timestamp
        
        Returns:
            Optional[Audio]: Claimed audio file or None if no files available
        """
        try:
            # Use a raw SQL query for optimal performance with FOR UPDATE SKIP LOCKED
            query = text(f"""
                UPDATE "Audio" 
                SET leased_until = NOW() + INTERVAL '{settings.AUDIO_LEASE_TIMEOUT_MINUTES} minutes'
                WHERE audio_id = (
                    SELECT audio_id 
                    FROM "Audio" 
                    WHERE transcription_count < {settings.MAX_TRANSCRIPTIONS_PER_AUDIO}
                    AND (leased_until IS NULL OR leased_until < NOW())
                    ORDER BY transcription_count ASC, audio_id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING audio_id, audio_filename, google_transcription, transcription_count, leased_until;
            """)
            
            result = await db.execute(query)
            audio_row = result.fetchone()
            
            if audio_row:
                await db.commit()
                
                # Convert the row to an Audio object-like structure
                audio_data = {
                    'audio_id': audio_row[0],
                    'audio_filename': audio_row[1], 
                    'google_transcription': audio_row[2],
                    'transcription_count': audio_row[3],
                    'leased_until': audio_row[4]
                }
                
                logger.info(f"Successfully claimed audio for transcription: {audio_data['audio_filename']} (lease until: {audio_data['leased_until']}, timeout: {settings.AUDIO_LEASE_TIMEOUT_MINUTES} minutes)")
                
                # Create a minimal Audio-like object for compatibility
                class ClaimedAudio:
                    def __init__(self, data):
                        self.audio_id = data['audio_id']
                        self.audio_filename = data['audio_filename']
                        self.google_transcription = data['google_transcription']
                        self.transcription_count = data['transcription_count']
                        self.leased_until = data['leased_until']
                
                return ClaimedAudio(audio_data)
            else:
                await db.rollback()
                logger.info("No audio files available for claiming")
                return None
                
        except Exception as e:
            await db.rollback()
            logger.error(f"Error claiming audio for transcription: {e}")
            raise

    @staticmethod
    async def get_random_audio_for_transcription(db: AsyncSession) -> Optional[Audio]:
        """
        Get an audio file for transcription using the lease-based claiming system.
        
        This method safely claims an audio file for transcription, preventing
        race conditions through database-level locking and lease management.
        
        Returns:
            Optional[Audio]: Claimed audio file or None if no files available
        """
        return await AudioService.claim_audio_for_transcription(db)

    @staticmethod
    async def release_audio_lease(db: AsyncSession, audio_id: UUID) -> bool:
        """
        Release the lease on an audio file.
        
        Sets the lease expiration to the current time, making the audio
        available for claiming by other users. Called when a transcription
        is submitted or when a lease needs to be manually released.
        
        Args:
            db: Database session
            audio_id: UUID of the audio file to release
            
        Returns:
            bool: True if lease was released successfully, False otherwise
        """
        try:
            query = text("""
                UPDATE "Audio" 
                SET leased_until = NOW()
                WHERE audio_id = :audio_id
                RETURNING audio_id;
            """)
            
            result = await db.execute(query, {"audio_id": audio_id})
            updated_row = result.fetchone()
            
            if updated_row:
                await db.commit()
                logger.info(f"Successfully released lease for audio: {audio_id}")
                return True
            else:
                await db.rollback()
                logger.warning(f"No audio found with ID: {audio_id}")
                return False
                
        except Exception as e:
            await db.rollback()
            logger.error(f"Error releasing audio lease for {audio_id}: {e}")
            raise

    @staticmethod
    async def get_all_audio_files(db: AsyncSession) -> List[Audio]:
        """Get all audio files from the database."""
        try:
            result = await db.execute(select(Audio))
            audio_files = result.scalars().all()
            logger.info(f"Retrieved {len(audio_files)} audio files from database")
            return audio_files
        except Exception as e:
            logger.error(f"Error getting all audio files: {e}")
            raise

    @staticmethod
    async def bulk_insert_from_csv(db: AsyncSession, csv_content: str) -> Tuple[int, int, List[str]]:
        """
        Bulk insert audio records from CSV file content.
        
        Processes a CSV file containing audio metadata and inserts new records
        into the database. Existing filenames and invalid entries are skipped.
        
        Expected CSV format:
        - filename: Audio file name (required, must be unique)
        - transcription: Reference transcription text (optional)
        
        Args:
            db: Database session
            csv_content: Raw CSV file content as string
            
        Returns:
            Tuple containing (inserted_count, skipped_count, skipped_files_list)
        """
        inserted = 0
        skipped = 0
        skipped_files: List[str] = []

        try:
            df = pd.read_csv(StringIO(csv_content))

            required_columns = ["filename", "transcription"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            # Normalize filenames and collect the set for a single DB lookup
            df["filename"] = df["filename"].astype(str).str.strip()
            filenames = {fn for fn in df["filename"].tolist() if fn}

            if filenames:
                existing_result = await db.execute(
                    select(Audio.audio_filename).where(Audio.audio_filename.in_(filenames))
                )
                existing_filenames = set(existing_result.scalars().all())
            else:
                existing_filenames = set()

            for index, row in df.iterrows():
                filename = str(row["filename"]).strip() if pd.notna(row["filename"]) else ""
                transcription = (
                    str(row["transcription"]).strip() if pd.notna(row["transcription"]) else None
                )

                if not filename:
                    skipped += 1
                    skipped_files.append({"row": index + 1, "filename": filename})
                    continue

                if filename in existing_filenames:
                    skipped += 1
                    skipped_files.append({"row": index + 1, "filename": filename})
                    continue

                new_audio = Audio(
                    audio_filename=filename,
                    google_transcription=transcription,
                    transcription_count=0,
                )
                db.add(new_audio)
                inserted += 1

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
        """
        Create a new transcription record with metadata.
        
        Stores the user's transcription along with quality metadata such as
        background noise, code-mixing, and speaker information. The database
        automatically updates the parent audio record's transcription count.
        
        Args:
            db: Database session
            transcription_data: Validated transcription data
            
        Returns:
            Transcriptions: Created transcription record
        """
        # Create the transcription object
        new_transcription = Transcriptions(
            audio_id=transcription_data.audio_id,
            transcription=transcription_data.transcription,
            speaker_gender=transcription_data.speaker_gender,
            has_noise=transcription_data.has_noise,
            is_code_mixed=transcription_data.is_code_mixed,
            is_speaker_overlappings_exist=transcription_data.is_speaker_overlappings_exist,
            is_audio_suitable=transcription_data.is_audio_suitable,
        )

        db.add(new_transcription)
        await db.commit()
        
        logger.info(
            f"Created new transcription: {new_transcription.trans_id} "
            f"for audio: {transcription_data.audio_id} "
            f"(transcription_count updated by trigger)"
        )
        return new_transcription

    @staticmethod
    async def get_transcriptions_for_audio(db: AsyncSession, audio_id: UUID) -> List[Transcriptions]:
        """Get all transcriptions for a specific audio file."""
        try:
            result = await db.execute(select(Transcriptions).where(Transcriptions.audio_id == audio_id))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting transcriptions for audio: {e}")
            raise
