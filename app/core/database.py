"""
Database configuration and connection setup using SQLAlchemy's asynchronous engine.

This module exposes a single async engine and the corresponding `AsyncSession`
factory for use across the application, along with small helpers to initialize
and close connections during application startup/shutdown.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an asynchronous SQLAlchemy `AsyncSession`."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database() -> None:
    """Initialize database connection (async) and verify connectivity."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Async database connection established successfully")
            logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Failed to initialize async database: {e}")
        raise


async def close_database() -> None:
    """Dispose the async engine."""
    try:
        await async_engine.dispose()
        logger.info("Async database connection closed")
    except Exception as e:
        logger.error(f"Error closing async database connection: {e}")
        raise
