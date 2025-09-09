"""
Database configuration and connection management.

This module provides asynchronous database connectivity using SQLAlchemy
with asyncpg driver for PostgreSQL. It includes connection lifecycle
management and session factory for dependency injection.
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
    """
    Base class for all SQLAlchemy ORM models.
    
    This declarative base provides the foundation for all database models
    in the application with automatic table mapping and relationship support.
    """
    pass


# Convert standard PostgreSQL URL to asyncpg format
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Create async database engine with connection pooling
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,  # Use NullPool for serverless/lambda deployments
)

# Create async session factory
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
