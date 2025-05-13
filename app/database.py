"""
Database configuration and utilities for the GenAI Research Assistant.
This file handles database connection setup, session management, and table creation.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncEngine
import logging
import os
from typing import AsyncGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/research_assistant")

# SQLite fallback URL
SQLITE_URL = "sqlite+aiosqlite:///./research_assistant.db"

engine = None

# Create async engine with graceful fallback
async def setup_db_engine():
    """
    Set up the database engine with fallback to SQLite if PostgreSQL fails.
    """
    global engine
    try:
        # First try the configured database
        temp_engine = create_async_engine(
            DATABASE_URL,
            echo=True,  # Set to False in production
            future=True
        )
        
        # Test connection
        async with temp_engine.begin() as conn:
            # Just connect to verify the connection works
            pass
        
        engine = temp_engine
        logger.info(f"Successfully connected to database: {DATABASE_URL}")
    except Exception as e:
        logger.warning(f"Failed to connect to primary database: {str(e)}")
        logger.info(f"Falling back to SQLite database at {SQLITE_URL}")
        
        # Fall back to SQLite
        engine = create_async_engine(
            SQLITE_URL,
            echo=True,  # Set to False in production
            future=True,
            connect_args={"check_same_thread": False}
        )

# Create declarative base
Base = declarative_base()

# Get async session
async def get_async_session():
    """
    Create an async session factory.
    """
    if engine is None:
        await setup_db_engine()
        
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    Yields a session and ensures it's closed after use.
    """
    # Ensure engine is set up
    if engine is None:
        await setup_db_engine()
    
    # Get session factory
    async_session = await get_async_session()
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}", exc_info=True)
            raise
        finally:
            await session.close()

async def create_db_and_tables():
    """
    Create all database tables.
    This should be called during application startup.
    """
    try:
        # Ensure engine is set up
        if engine is None:
            await setup_db_engine()
            
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}", exc_info=True)
        raise

async def drop_db_and_tables():
    """
    Drop all database tables.
    This should be used with caution, typically only in development or testing.
    """
    try:
        # Ensure engine is set up
        if engine is None:
            await setup_db_engine()
            
        logger.info("Dropping database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {str(e)}", exc_info=True)
        raise