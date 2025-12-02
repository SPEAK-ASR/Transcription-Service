"""
Database service layer for audio and transcription operations.

This module provides high-level database operations with proper error handling,
transaction management, and concurrency safety. All operations use async
SQLAlchemy sessions for optimal performance.
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from uuid import UUID
from io import StringIO
import pandas as pd
from datetime import datetime, timezone

from app.models import Audio, Transcriptions
from app.schemas import TranscriptionCreate, TranscriptionValidationUpdate
from app.core.config import settings
from app.services.gcs_service import gcs_service

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
    async def lease_audio_for_validation(db: AsyncSession, audio_id: UUID) -> bool:
        """Lease an audio item while it is under validation."""
        try:
            query = text(f"""
                UPDATE "Audio"
                SET leased_until = NOW() + INTERVAL '{settings.AUDIO_LEASE_TIMEOUT_MINUTES} minutes'
                WHERE audio_id = :audio_id
                RETURNING audio_id;
            """)
            result = await db.execute(query, {"audio_id": audio_id})
            row = result.fetchone()

            if row:
                await db.commit()
                logger.info(f"Leased audio {audio_id} for validation")
                return True

            await db.rollback()
            logger.warning(f"Attempted to lease audio for validation but no audio found: {audio_id}")
            return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Error leasing audio {audio_id} for validation: {e}")
            raise

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
        
        If audio is marked as unsuitable (is_audio_suitable=False), this method will:
        1. Update the Audio table to mark it as "not_suitable" and clear metadata
        2. Create a Transcriptions entry with nullified fields
        
        Args:
            db: Database session
            transcription_data: Validated transcription data
            
        Returns:
            Transcriptions: Created transcription record
        """
        # Check if audio is being marked as unsuitable
        is_unsuitable = transcription_data.is_audio_suitable is False
        
        if is_unsuitable:
            # Update the Audio table for unsuitable audio
            try:
                # Fetch the audio record
                result = await db.execute(
                    select(Audio).where(Audio.audio_id == transcription_data.audio_id)
                )
                audio_record = result.scalar_one_or_none()
                
                if audio_record:
                    # Store the original filename before updating
                    original_filename = audio_record.audio_filename
                    
                    # Delete the audio file from Google Cloud Storage
                    try:
                        deletion_success = await gcs_service.delete_blob(original_filename)
                        if deletion_success:
                            logger.info(
                                f"Successfully deleted audio file from GCS: {original_filename}"
                            )
                        else:
                            logger.warning(
                                f"Audio file not found in GCS (may have been deleted already): {original_filename}"
                            )
                    except Exception as gcs_error:
                        logger.error(
                            f"Failed to delete audio file from GCS: {original_filename}. Error: {gcs_error}"
                        )
                        # Continue with database update even if GCS deletion fails
                    
                    # Update Audio table fields for unsuitable audio
                    audio_record.audio_filename = "not_suitable"
                    audio_record.google_transcription = "Audio not suitable for transcription"
                    audio_record.start_time = None
                    audio_record.end_time = None
                    audio_record.padded_duration = None
                    audio_record.created_at = None
                    
                    logger.info(
                        f"Marked audio {transcription_data.audio_id} as not_suitable "
                        f"and cleared metadata fields"
                    )
            except Exception as e:
                logger.error(f"Error updating audio record for unsuitable audio: {e}")
                await db.rollback()
                raise
            
            # Create transcription with nullified fields for unsuitable audio
            new_transcription = Transcriptions(
                audio_id=transcription_data.audio_id,
                transcription=transcription_data.transcription,
                speaker_gender=None,
                has_noise=None,
                is_code_mixed=None,
                is_speaker_overlappings_exist=None,
                is_audio_suitable=False,
                admin=None,
                validated_at=None,
                created_at=None
            )
        else:
            # Create normal transcription with all metadata
            # Note: created_at is not set here, so the database default (NOW()) will be used
            new_transcription = Transcriptions(
                audio_id=transcription_data.audio_id,
                transcription=transcription_data.transcription,
                speaker_gender=transcription_data.speaker_gender,
                has_noise=transcription_data.has_noise,
                is_code_mixed=transcription_data.is_code_mixed,
                is_speaker_overlappings_exist=transcription_data.is_speaker_overlappings_exist,
                is_audio_suitable=transcription_data.is_audio_suitable,
                admin=transcription_data.admin,
                validated_at=transcription_data.validated_at
            )

        db.add(new_transcription)
        await db.commit()
        
        if is_unsuitable:
            logger.info(
                f"Created unsuitable transcription: {new_transcription.trans_id} "
                f"for audio: {transcription_data.audio_id} "
                f"(all metadata fields nullified)"
            )
        else:
            logger.info(
                f"Created new transcription: {new_transcription.trans_id} "
                f"for audio: {transcription_data.audio_id} "
                f"(validated_at: {transcription_data.validated_at}, admin: {transcription_data.admin}) "
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

    @staticmethod
    async def get_next_unvalidated_transcription(
        db: AsyncSession
    ) -> Optional[Tuple[Transcriptions, Audio]]:
        """
        Fetch the next available transcription that needs validation.
        
        Uses a lease-based system similar to audio claiming to prevent multiple
        users from getting the same transcription. Falls back to different
        transcriptions if the first one is already being validated.
        """
        try:
            # Use raw SQL query to properly handle lease expiration with NOW()
            query = text("""
                SELECT t.trans_id, t.audio_id, t.transcription, t.speaker_gender, 
                       t.has_noise, t.is_code_mixed, t.is_speaker_overlappings_exist, 
                       t.is_audio_suitable, t.admin, t.validated_at, t.created_at,
                       a.audio_id, a.audio_filename, a.google_transcription, 
                       a.transcription_count, a.leased_until
                FROM "Transcriptions" t
                JOIN "Audio" a ON t.audio_id = a.audio_id
                WHERE t.is_audio_suitable = TRUE
                AND t.validated_at IS NULL
                AND (a.leased_until IS NULL OR a.leased_until < NOW())
                ORDER BY t.created_at ASC
                LIMIT 5
                FOR UPDATE OF t, a SKIP LOCKED
            """)
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            # Try to lease each transcription until we find one that's available
            for row in rows:
                audio_id = row[1]  # t.audio_id from the query
                
                # Try to lease this audio for validation
                leased = await AudioService.lease_audio_for_validation(db, audio_id)
                if leased:
                    # Create transcription and audio objects from the row data
                    transcription_data = {
                        'trans_id': row[0],
                        'audio_id': row[1], 
                        'transcription': row[2],
                        'speaker_gender': row[3],
                        'has_noise': row[4],
                        'is_code_mixed': row[5],
                        'is_speaker_overlappings_exist': row[6],
                        'is_audio_suitable': row[7],
                        'admin': row[8],
                        'validated_at': row[9],
                        'created_at': row[10]
                    }
                    
                    audio_data = {
                        'audio_id': row[11],
                        'audio_filename': row[12],
                        'google_transcription': row[13],
                        'transcription_count': row[14],
                        'leased_until': row[15]
                    }
                    
                    # Create minimal objects for compatibility
                    class TranscriptionObj:
                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key, value)
                    
                    class AudioObj:
                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key, value)
                    
                    transcription_obj = TranscriptionObj(transcription_data)
                    audio_obj = AudioObj(audio_data)
                    
                    logger.info(f"Successfully claimed transcription {transcription_obj.trans_id} for validation")
                    return transcription_obj, audio_obj
            
            # If we couldn't lease any of the transcriptions, return None
            logger.info("No transcriptions available for validation at this time")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching next unvalidated transcription: {e}")
            raise

    @staticmethod
    async def get_validation_progress_counts(
        db: AsyncSession
    ) -> dict:
        """Return counts of pending and completed validations."""
        try:
            total_stmt = (
                select(func.count())
                .select_from(Transcriptions)
                .where(Transcriptions.is_audio_suitable.is_(True))
            )
            pending_stmt = (
                select(func.count())
                .select_from(Transcriptions)
                .where(Transcriptions.validated_at.is_(None) & Transcriptions.is_audio_suitable.is_(True))
            )

            total_result = await db.execute(total_stmt)
            pending_result = await db.execute(pending_stmt)

            total = int(total_result.scalar_one())
            pending = int(pending_result.scalar_one())
            completed = max(total - pending, 0)

            return {"total": total, "pending": pending, "completed": completed}
        except Exception as exc:
            logger.error("Error calculating validation progress counts: %s", exc)
            raise

    @staticmethod
    async def validate_transcription(
        db: AsyncSession,
        trans_id: UUID,
        update_data: TranscriptionValidationUpdate
    ) -> Transcriptions:
        """Update transcription fields and mark the record as validated."""
        try:
            result = await db.execute(
                select(Transcriptions).where(Transcriptions.trans_id == trans_id)
            )
            transcription = result.scalar_one_or_none()
            if not transcription:
                raise ValueError(f"Transcription not found: {trans_id}")

            transcription_text = (update_data.transcription or '').strip()
            transcription.transcription = transcription_text
            transcription.speaker_gender = update_data.speaker_gender
            transcription.has_noise = update_data.has_noise
            transcription.is_code_mixed = update_data.is_code_mixed
            transcription.is_speaker_overlappings_exist = update_data.is_speaker_overlappings_exist
            transcription.is_audio_suitable = (
                update_data.is_audio_suitable
                if update_data.is_audio_suitable is not None
                else transcription.is_audio_suitable
            )
            # Keep the original admin value unchanged during validation
            transcription.validated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(transcription)

            try:
                released = await AudioService.release_audio_lease(db, transcription.audio_id)
                if not released:
                    logger.warning(
                        "Lease release skipped for audio %s after validation",
                        transcription.audio_id
                    )
            except Exception as lease_error:
                logger.warning(
                    "Failed to release lease for audio %s after validation: %s",
                    transcription.audio_id,
                    lease_error
                )

            logger.info(
                "Validated transcription %s (audio %s) - original admin: %s",
                transcription.trans_id,
                transcription.audio_id,
                transcription.admin or 'none'
            )
            return transcription
        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error validating transcription {trans_id}: {e}")
            raise
