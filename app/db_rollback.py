"""
PostgreSQL Rollback Script for GenAI Research Assistant

This script creates an SQLite database in the tmp folder as a fallback option
when PostgreSQL is not available. It ensures compatibility with the existing
database schema and operations.
"""
import os
import tempfile
import logging
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

# Add parent directory to path so we can import from the app package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.utils.logging_config import configure_logging

# Configure logging
configure_logging(logging.WARNING)
logger = logging.getLogger(__name__)

# Create a local tmp directory in the project root instead of using system temp folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TMP_DIR = os.path.join(PROJECT_ROOT, 'tmp', 'genai_research_assistant')
os.makedirs(TMP_DIR, exist_ok=True)

# Define SQLite database URL in tmp directory
SQLITE_DB_PATH = os.path.join(TMP_DIR, 'research_assistant.db')
SQLITE_URL = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"

async def setup_rollback_db():
    """
    Set up a rollback SQLite database in the tmp directory.
    """
    logger.info(f"Setting up rollback database at {SQLITE_DB_PATH}")
    
    # Create async engine for SQLite
    engine = create_async_engine(
        SQLITE_URL,
        echo=False,  
        future=True,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Rollback database tables created successfully")
    
    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    return engine, async_session

async def check_postgres_connection(postgres_url):
    """
    Check if PostgreSQL is available.
    
    Args:
        postgres_url: The PostgreSQL database URL
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        engine = create_async_engine(
            postgres_url,
            echo=False,
            future=True
        )
        
        # Test connection
        async with engine.begin() as conn:
            # Just connect to verify connection works
            pass
        
        await engine.dispose()
        return True
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {str(e)}")
        return False

async def migrate_data_from_postgres(postgres_url, sqlite_session_factory):
    """
    Migrate data from PostgreSQL to SQLite.
    
    Args:
        postgres_url: The PostgreSQL database URL
        sqlite_session_factory: Session factory for SQLite
    """
    try:
        # Connect to PostgreSQL
        pg_engine = create_async_engine(
            postgres_url,
            echo=False,
            future=True
        )
        
        pg_session_factory = sessionmaker(
            pg_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Get data from PostgreSQL
        async with pg_session_factory() as pg_session:
            # Get users
            users = (await pg_session.execute(text("SELECT * FROM users"))).all()
            
            # Get conversations
            conversations = (await pg_session.execute(text("SELECT * FROM conversations"))).all()
            
            # Get messages
            messages = (await pg_session.execute(text("SELECT * FROM messages"))).all()
        
        # Insert data into SQLite
        async with sqlite_session_factory() as sqlite_session:
            # Insert users
            if users:
                await sqlite_session.execute(text("DELETE FROM users"))
                for user in users:
                    user_dict = dict(user)
                    await sqlite_session.execute(
                        text("INSERT INTO users VALUES (:id, :email, :hashed_password, :full_name, "
                        ":is_active, :is_superuser, :created_at, :updated_at, :preferences)"),
                        user_dict
                    )
            
            # Insert conversations
            if conversations:
                await sqlite_session.execute(text("DELETE FROM conversations"))
                for conv in conversations:
                    conv_dict = dict(conv)
                    await sqlite_session.execute(
                        text("INSERT INTO conversations VALUES (:id, :title, :created_at, :updated_at, "
                        ":user_id, :embedding, :meta_data)"),
                        conv_dict
                    )
            
            # Insert messages
            if messages:
                await sqlite_session.execute(text("DELETE FROM messages"))
                for msg in messages:
                    msg_dict = dict(msg)
                    await sqlite_session.execute(
                        text("INSERT INTO messages VALUES (:id, :conversation_id, :role, :content, "
                        ":created_at, :meta_data)"),
                        msg_dict
                    )
            
            await sqlite_session.commit()
        
        await pg_engine.dispose()
        logger.info("Data migration from PostgreSQL to SQLite completed successfully")
    except Exception as e:
        logger.error(f"Error during data migration: {str(e)}", exc_info=True)

async def update_env_to_use_sqlite():
    """Update environment to use SQLite instead of PostgreSQL."""
    # Set environment variable to use SQLite
    os.environ["DATABASE_URL"] = SQLITE_URL
    logger.info(f"Environment updated to use SQLite at {SQLITE_URL}")

async def main():
    """Main function to set up rollback database."""
    from app.config import settings
    
    # Check if PostgreSQL is available
    postgres_available = await check_postgres_connection(settings.DATABASE_URL)
    
    if postgres_available:
        logger.info("PostgreSQL is available, no rollback needed")
        return
    
    # PostgreSQL is not available, set up rollback database
    logger.info("PostgreSQL is not available, setting up rollback database")
    
    # Set up rollback database
    engine, async_session = await setup_rollback_db()
    
    # Try to migrate data from PostgreSQL if it becomes available later
    postgres_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    if await check_postgres_connection(postgres_url):
        await migrate_data_from_postgres(postgres_url, async_session)
    
    # Update environment to use SQLite
    await update_env_to_use_sqlite()
    
    logger.info(f"Rollback database setup complete. Using SQLite at {SQLITE_DB_PATH}")
    
    return engine, async_session

if __name__ == "__main__":
    asyncio.run(main()) 