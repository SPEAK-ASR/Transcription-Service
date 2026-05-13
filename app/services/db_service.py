"""
Database service layer for audio and transcription operations.

Provides async SQLAlchemy operations for claiming audio for transcription
and creating transcription records.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from uuid import UUID

from app.models import Audio, Transcriptions
from app.schemas import TranscriptionCreate
from app.core.config import settings
from app.services.gcs_service import gcs_service

logger = logging.getLogger(__name__)


def _normalize_reference_text(value: Optional[str]) -> str:
    """Collapse whitespace for comparing ASR reference strings."""
    if not value or not str(value).strip():
        return ""
    return " ".join(str(value).strip().split())


class AudioService:
    """Service for audio database operations."""

    @staticmethod
    async def claim_audio_for_transcription(db: AsyncSession) -> Optional[Audio]:
        """
        Atomically claim an audio file for transcription using lease-based system.
        """
        try:
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
                RETURNING audio_id, audio_filename, google_transcription, speak_transcription, transcription_count, leased_until;
            """)

            result = await db.execute(query)
            audio_row = result.fetchone()

            if audio_row:
                await db.commit()

                audio_data = {
                    'audio_id': audio_row[0],
                    'audio_filename': audio_row[1],
                    'google_transcription': audio_row[2],
                    'speak_transcription': audio_row[3],
                    'transcription_count': audio_row[4],
                    'leased_until': audio_row[5]
                }

                logger.info(
                    f"Successfully claimed audio for transcription: {audio_data['audio_filename']} "
                    f"(lease until: {audio_data['leased_until']}, timeout: {settings.AUDIO_LEASE_TIMEOUT_MINUTES} minutes)"
                )

                class ClaimedAudio:
                    def __init__(self, data):
                        self.audio_id = data['audio_id']
                        self.audio_filename = data['audio_filename']
                        self.google_transcription = data['google_transcription']
                        self.speak_transcription = data['speak_transcription']
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
        """Claim and return an audio file for transcription."""
        return await AudioService.claim_audio_for_transcription(db)


class TranscriptionService:
    """Service for transcription database operations."""

    @staticmethod
    async def create_transcription(db: AsyncSession, transcription_data: TranscriptionCreate) -> Transcriptions:
        """
        Create a new transcription record with metadata.
        """
        is_unsuitable = transcription_data.is_audio_suitable is False

        if is_unsuitable:
            try:
                result = await db.execute(
                    select(Audio).where(Audio.audio_id == transcription_data.audio_id)
                )
                audio_record = result.scalar_one_or_none()

                if audio_record:
                    original_filename = audio_record.audio_filename

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
                created_at=None,
            )
        else:
            new_transcription = Transcriptions(
                audio_id=transcription_data.audio_id,
                transcription=transcription_data.transcription,
                speaker_gender=transcription_data.speaker_gender,
                has_noise=transcription_data.has_noise,
                is_code_mixed=transcription_data.is_code_mixed,
                is_speaker_overlappings_exist=transcription_data.is_speaker_overlappings_exist,
                is_audio_suitable=transcription_data.is_audio_suitable,
                admin=transcription_data.admin,
                validated_at=transcription_data.validated_at,
            )

        db.add(new_transcription)
        await db.commit()

        if transcription_data.is_best_google is not None:
            try:
                audio_result = await db.execute(
                    select(Audio).where(Audio.audio_id == transcription_data.audio_id)
                )
                audio_record = audio_result.scalar_one_or_none()

                if audio_record:
                    g_norm = _normalize_reference_text(audio_record.google_transcription)
                    s_norm = _normalize_reference_text(audio_record.speak_transcription)

                    is_best_google_value = transcription_data.is_best_google
                    if g_norm and s_norm and g_norm == s_norm and is_best_google_value is not None:
                        logger.info(
                            "Coercing is_best_google to NULL: Google and SPEAK references are identical"
                        )
                        is_best_google_value = None

                    audio_record.is_best_google = is_best_google_value
                    await db.commit()
                    logger.info(
                        f"Updated Audio {transcription_data.audio_id} is_best_google to {is_best_google_value}"
                    )
            except Exception as e:
                logger.error(f"Error updating is_best_google on Audio record: {e}")

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
