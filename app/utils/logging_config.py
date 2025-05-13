"""
Logging configuration for the GenAI Research Assistant.
This file provides centralized logging configuration for the application.
"""
import logging
import sys

def configure_logging(log_level=logging.WARNING):
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (default: WARNING to reduce verbosity)
    """
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set SQLAlchemy logging to be more quiet
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    # Set aiohttp client to warning level to suppress connection pool messages
    logging.getLogger('aiohttp.client').setLevel(logging.WARNING)
    
    # Set uvicorn and fastapi to warning level
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING) 