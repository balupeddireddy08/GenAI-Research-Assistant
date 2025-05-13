"""
Test script for the database rollback functionality.

This script tests the database rollback functionality by:
1. Checking if PostgreSQL is available
2. Setting up the rollback database if needed
3. Performing basic database operations to verify functionality

Usage:
    python -m app.scripts.test_rollback
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path so we can import from the app package
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from app.utils.db_fallback import check_postgres_connection, TMP_DIR, SQLITE_DB_PATH
from app.database import setup_db_engine, get_async_session, create_db_and_tables, Base
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_database(engine):
    """
    Drop and recreate all tables to ensure a clean test environment.
    
    Args:
        engine: SQLAlchemy engine
    """
    logger.info("Resetting database by dropping and recreating all tables...")
    
    try:
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        # Recreate all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database reset completed successfully")
    except Exception as e:
        logger.error(f"Error during database reset: {str(e)}", exc_info=True)
        raise

async def cleanup_test_data(session_factory):
    """
    Delete any existing test data to avoid unique constraint violations.
    
    Args:
        session_factory: SQLAlchemy session factory
    """
    logger.info("Cleaning up any existing test data...")
    
    async with session_factory() as session:
        try:
            # Delete test user by email
            email = "test@example.com"
            
            # Delete messages associated with test user's conversations
            await session.execute(
                text("DELETE FROM messages WHERE conversation_id IN "
                     "(SELECT id FROM conversations WHERE user_id IN "
                     "(SELECT id FROM users WHERE email = :email))"), 
                {"email": email}
            )
            
            # Delete conversations associated with test user
            await session.execute(
                text("DELETE FROM conversations WHERE user_id IN "
                     "(SELECT id FROM users WHERE email = :email)"),
                {"email": email}
            )
            
            # Delete the test user
            await session.execute(
                text("DELETE FROM users WHERE email = :email"),
                {"email": email}
            )
            
            await session.commit()
            logger.info("Test data cleanup completed")
        except Exception as e:
            logger.warning(f"Error during test data cleanup: {str(e)}")
            await session.rollback()

async def test_db_operations(session_factory):
    """
    Test basic database operations.
    
    Args:
        session_factory: SQLAlchemy session factory
    """
    # First clean up any existing test data
    await cleanup_test_data(session_factory)
    
    logger.info("Testing basic database operations...")
    
    # Create test user
    test_user = {
        "email": "test@example.com",
        "hashed_password": "hashed_password",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "preferences": {}
    }
    
    # Create test conversation
    test_conversation = {
        "title": "Test Conversation",
        "user_id": None,  # Will be set after user creation
        "meta_data": {"source": "test_rollback"}
    }
    
    # Create test message
    test_message = {
        "role": "user",
        "content": "Hello, this is a test message",
        "conversation_id": None,  # Will be set after conversation creation
        "meta_data": {"source": "test_rollback"}
    }
    
    async with session_factory() as session:
        try:
            # Create user
            user = User(**test_user)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created test user with ID: {user.id}")
            
            # Create conversation
            test_conversation["user_id"] = user.id
            conversation = Conversation(**test_conversation)
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            logger.info(f"Created test conversation with ID: {conversation.id}")
            
            # Create message
            test_message["conversation_id"] = conversation.id
            message = Message(**test_message)
            session.add(message)
            await session.commit()
            await session.refresh(message)
            logger.info(f"Created test message with ID: {message.id}")
            
            # Verify data by querying
            users = (await session.execute(text("SELECT * FROM users"))).fetchall()
            logger.info(f"Found {len(users)} users in database")
            
            conversations = (await session.execute(text("SELECT * FROM conversations"))).fetchall()
            logger.info(f"Found {len(conversations)} conversations in database")
            
            messages = (await session.execute(text("SELECT * FROM messages"))).fetchall()
            logger.info(f"Found {len(messages)} messages in database")
            
            logger.info("Basic database operations successful!")
        except Exception as e:
            logger.error(f"Error during database operations: {str(e)}", exc_info=True)
            await session.rollback()
            raise

async def main():
    """Main function to test database rollback functionality."""
    logger.info("Starting database rollback functionality test")
    logger.info(f"SQLite database will be stored at: {SQLITE_DB_PATH}")
    
    # Check if PostgreSQL is available
    postgres_available = await check_postgres_connection(settings.DATABASE_URL)
    
    if postgres_available:
        logger.info(f"PostgreSQL is available at {settings.DATABASE_URL}")
        db_type = "PostgreSQL"
    else:
        logger.info(f"PostgreSQL is not available. Using SQLite fallback at {SQLITE_DB_PATH}")
        db_type = "SQLite"
    
    # Setup database engine (will handle fallback internally)
    await setup_db_engine()
    
    # Get the database engine from the application
    from app.database import engine
    
    # Reset the database to ensure a clean test environment
    await reset_database(engine)
    
    # Get session factory
    session_factory = await get_async_session()
    
    # Test database operations
    try:
        await test_db_operations(session_factory)
        logger.info(f"All tests passed successfully using {db_type}!")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 