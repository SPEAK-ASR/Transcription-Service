"""
Database configuration and connection setup for Supabase using asynchronous SQLAlchemy engine.
"""

import logging
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Build async asyncpg URL for async operations
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Build sync psycopg2 URL for sync operations (kept for compatibility)
SYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg2://"
)

# Async engine for async operations
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

# Sync engine for compatibility (can be removed later)
engine = create_engine(
    SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine,
    class_=AsyncSession
)

# Standard sync session factory (kept for compatibility)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_async_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an asynchronous SQLAlchemy AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


def get_database_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a synchronous SQLAlchemy Session (deprecated - use async version)."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def init_database() -> None:
    """Initialize database connection (async) — verifies connectivity."""
    try:
        async with async_engine.connect() as conn:
            # Simple no-op to check connection - use text() for raw SQL
            await conn.execute(text("SELECT 1"))
            logger.info("Async database connection established successfully")
            logger.info(f"Connected to database: {settings.DBNAME} at {settings.HOST}")
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


# Legacy sync functions (kept for compatibility)
def init_database_sync() -> None:
    """Initialize database connection (sync) — verifies connectivity."""
    try:
        with engine.connect() as conn:
            # Simple no-op to check connection - use text() for raw SQL
            conn.execute(text("SELECT 1"))
            logger.info("Sync database connection established successfully")
            logger.info(f"Connected to database: {settings.DBNAME} at {settings.HOST}")
    except Exception as e:
        logger.error(f"Failed to initialize sync database: {e}")
        raise


def close_database_sync() -> None:
    """Dispose the sync engine."""
    try:
        engine.dispose()
        logger.info("Sync database connection closed")
    except Exception as e:
        logger.error(f"Error closing sync database connection: {e}")
        raise