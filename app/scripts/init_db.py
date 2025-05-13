"""
Database initialization script for the GenAI Research Assistant.

This script initializes the database with the rollback functionality,
creating either a PostgreSQL database or an SQLite fallback in the tmp directory.

Usage:
    python -m app.scripts.init_db
"""
import os
import sys
import asyncio
import logging
import tempfile
from pathlib import Path

# Add parent directory to path so we can import from the app package
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.database import create_db_and_tables, setup_db_engine
from app.utils.db_fallback import TMP_DIR, SQLITE_DB_PATH, check_postgres_connection
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize the database with rollback functionality."""
    logger.info("Starting database initialization")
    
    # Check if PostgreSQL is available
    postgres_available = await check_postgres_connection(settings.DATABASE_URL)
    
    if postgres_available:
        logger.info(f"PostgreSQL is available at {settings.DATABASE_URL}")
    else:
        logger.warning("PostgreSQL is not available")
        logger.info(f"SQLite fallback will be used at {SQLITE_DB_PATH}")
        logger.info(f"Temporary directory path: {TMP_DIR}")
    
    # Setup database engine (will handle fallback internally)
    await setup_db_engine()
    
    # Create database tables
    await create_db_and_tables()
    
    logger.info("Database initialization completed successfully")

def main():
    """Main entry point for the script."""
    try:
        asyncio.run(init_database())
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 