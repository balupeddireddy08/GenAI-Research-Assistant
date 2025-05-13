"""
Data Transfer Script for the GenAI Research Assistant.

This script provides functionality to transfer data between PostgreSQL and
the SQLite fallback database in the tmp directory.

Usage:
    # Transfer from PostgreSQL to SQLite
    python -m app.scripts.transfer_data --direction pg_to_sqlite
    
    # Transfer from SQLite to PostgreSQL
    python -m app.scripts.transfer_data --direction sqlite_to_pg
"""
import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Add parent directory to path so we can import from the app package
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from app.database import Base
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.utils.db_fallback import TMP_DIR, SQLITE_DB_PATH, check_postgres_connection
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def pg_to_sqlite_transfer():
    """Transfer data from PostgreSQL to SQLite."""
    # Check if PostgreSQL is available
    postgres_available = await check_postgres_connection(settings.DATABASE_URL)
    
    if not postgres_available:
        logger.error("PostgreSQL is not available. Cannot perform data transfer.")
        return False
    
    logger.info("Starting data transfer from PostgreSQL to SQLite...")
    
    # Create engine for PostgreSQL
    pg_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True
    )
    
    # Create engine for SQLite
    sqlite_url = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"
    sqlite_engine = create_async_engine(
        sqlite_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
    )
    
    # Create session factories
    pg_session_factory = sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    sqlite_session_factory = sessionmaker(
        sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        # Create tables in SQLite if they don't exist
        async with sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Transfer users
        await transfer_users(pg_session_factory, sqlite_session_factory)
        
        # Transfer conversations
        await transfer_conversations(pg_session_factory, sqlite_session_factory)
        
        # Transfer messages
        await transfer_messages(pg_session_factory, sqlite_session_factory)
        
        logger.info("Data transfer from PostgreSQL to SQLite completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during data transfer: {str(e)}", exc_info=True)
        return False
    finally:
        await pg_engine.dispose()
        await sqlite_engine.dispose()

async def sqlite_to_pg_transfer():
    """Transfer data from SQLite to PostgreSQL."""
    # Check if PostgreSQL is available
    postgres_available = await check_postgres_connection(settings.DATABASE_URL)
    
    if not postgres_available:
        logger.error("PostgreSQL is not available. Cannot perform data transfer.")
        return False
        
    # Check if SQLite file exists
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database file not found at {SQLITE_DB_PATH}")
        return False
    
    logger.info("Starting data transfer from SQLite to PostgreSQL...")
    
    # Create engine for PostgreSQL
    pg_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True
    )
    
    # Create engine for SQLite
    sqlite_url = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"
    sqlite_engine = create_async_engine(
        sqlite_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
    )
    
    # Create session factories
    pg_session_factory = sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    sqlite_session_factory = sessionmaker(
        sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        # Create tables in PostgreSQL if they don't exist
        async with pg_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Transfer users
        await transfer_users(sqlite_session_factory, pg_session_factory)
        
        # Transfer conversations
        await transfer_conversations(sqlite_session_factory, pg_session_factory)
        
        # Transfer messages
        await transfer_messages(sqlite_session_factory, pg_session_factory)
        
        logger.info("Data transfer from SQLite to PostgreSQL completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during data transfer: {str(e)}", exc_info=True)
        return False
    finally:
        await pg_engine.dispose()
        await sqlite_engine.dispose()

async def transfer_users(source_session_factory, target_session_factory):
    """Transfer users from source to target database."""
    logger.info("Transferring users...")
    
    async with source_session_factory() as source_session:
        # Get all users from source
        result = await source_session.execute(text("SELECT * FROM users"))
        users = result.fetchall()
    
    if not users:
        logger.info("No users to transfer")
        return
    
    logger.info(f"Transferring {len(users)} users")
    
    async with target_session_factory() as target_session:
        # First, delete existing users in target
        await target_session.execute(text("DELETE FROM users"))
        
        # Insert users into target
        for user in users:
            user_dict = dict(user)
            await target_session.execute(
                text("INSERT INTO users VALUES (:id, :email, :hashed_password, :full_name, "
                ":is_active, :is_superuser, :created_at, :updated_at, :preferences)"),
                user_dict
            )
        
        await target_session.commit()

async def transfer_conversations(source_session_factory, target_session_factory):
    """Transfer conversations from source to target database."""
    logger.info("Transferring conversations...")
    
    async with source_session_factory() as source_session:
        # Get all conversations from source
        result = await source_session.execute(text("SELECT * FROM conversations"))
        conversations = result.fetchall()
    
    if not conversations:
        logger.info("No conversations to transfer")
        return
    
    logger.info(f"Transferring {len(conversations)} conversations")
    
    async with target_session_factory() as target_session:
        # First, delete existing conversations in target
        await target_session.execute(text("DELETE FROM conversations"))
        
        # Insert conversations into target
        for conv in conversations:
            conv_dict = dict(conv)
            await target_session.execute(
                text("INSERT INTO conversations VALUES (:id, :title, :created_at, :updated_at, "
                ":user_id, :embedding, :meta_data)"),
                conv_dict
            )
        
        await target_session.commit()

async def transfer_messages(source_session_factory, target_session_factory):
    """Transfer messages from source to target database."""
    logger.info("Transferring messages...")
    
    async with source_session_factory() as source_session:
        # Get all messages from source
        result = await source_session.execute(text("SELECT * FROM messages"))
        messages = result.fetchall()
    
    if not messages:
        logger.info("No messages to transfer")
        return
    
    logger.info(f"Transferring {len(messages)} messages")
    
    async with target_session_factory() as target_session:
        # First, delete existing messages in target
        await target_session.execute(text("DELETE FROM messages"))
        
        # Insert messages into target
        for msg in messages:
            msg_dict = dict(msg)
            await target_session.execute(
                text("INSERT INTO messages VALUES (:id, :conversation_id, :role, :content, "
                ":created_at, :meta_data)"),
                msg_dict
            )
        
        await target_session.commit()

async def main(direction):
    """Main function to handle data transfer based on direction."""
    if direction == "pg_to_sqlite":
        success = await pg_to_sqlite_transfer()
    elif direction == "sqlite_to_pg":
        success = await sqlite_to_pg_transfer()
    else:
        logger.error(f"Invalid direction: {direction}")
        return
    
    if success:
        logger.info(f"Data transfer ({direction}) completed successfully")
    else:
        logger.error(f"Data transfer ({direction}) failed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transfer data between PostgreSQL and SQLite databases")
    parser.add_argument(
        "--direction", 
        type=str, 
        choices=["pg_to_sqlite", "sqlite_to_pg"],
        required=True,
        help="Direction of data transfer"
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.direction)) 