"""
Database configuration and connection setup for Supabase.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    Base class for all database models.
    """
    pass


# Create async engine for Supabase PostgreSQL connection
# Supabase uses standard PostgreSQL, so we use asyncpg driver
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,  # Log SQL queries when in debug mode
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """
    Initialize database connection and create tables if they don't exist.
    Note: Since tables are already created in Supabase, this mainly verifies connection.
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered with Base
            from app.models import Audio, Transcriptions
            
            logger.info("Database connection established successfully")
            logger.info(f"Connected to database: {settings.DBNAME} at {settings.HOST}")
            
            # Optionally create tables if they don't exist (uncomment if needed)
            # await conn.run_sync(Base.metadata.create_all)
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database():
    """
    Close database connection.
    """
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")
        raise