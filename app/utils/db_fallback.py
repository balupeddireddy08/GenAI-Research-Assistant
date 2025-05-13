"""
Database fallback utility for the GenAI Research Assistant.

This module provides functions to check and handle database fallbacks
when PostgreSQL is not available, automatically setting up a SQLite
alternative in the tmp directory.
"""
import os
import sys
import logging
import tempfile
from sqlalchemy.ext.asyncio import create_async_engine

# Configure logging
logger = logging.getLogger(__name__)

# Create a local tmp directory in the project root instead of using system temp folder
# Get the project root directory (assuming this file is in app/utils/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
TMP_DIR = os.path.join(PROJECT_ROOT, 'tmp', 'genai_research_assistant')
os.makedirs(TMP_DIR, exist_ok=True)

# Define SQLite database path in tmp directory
SQLITE_DB_PATH = os.path.join(TMP_DIR, 'research_assistant.db')
SQLITE_URL = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"

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
        logger.info(f"Successfully connected to PostgreSQL database: {postgres_url}")
        return True
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {str(e)}")
        return False

async def setup_fallback_database():
    """
    Set up fallback SQLite database in tmp directory and update environment.
    
    Returns:
        str: The SQLite connection URL
    """
    logger.info(f"Setting up fallback SQLite database at {SQLITE_DB_PATH}")
    
    # Update environment variable to use SQLite
    os.environ["DATABASE_URL"] = SQLITE_URL
    
    # Return the SQLite URL
    return SQLITE_URL

async def get_available_database_url(postgres_url):
    """
    Check PostgreSQL availability and return appropriate database URL.
    
    Args:
        postgres_url: The PostgreSQL database URL from configuration
        
    Returns:
        str: Either the PostgreSQL URL if available, or SQLite fallback URL
    """
    # Check if PostgreSQL is available
    if await check_postgres_connection(postgres_url):
        return postgres_url
    
    # PostgreSQL unavailable, set up fallback
    logger.warning("PostgreSQL unavailable. Setting up SQLite fallback database.")
    return await setup_fallback_database() 