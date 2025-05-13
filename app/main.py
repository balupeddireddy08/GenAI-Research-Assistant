"""
Main FastAPI application for the GenAI Research Assistant.
This file initializes the FastAPI application and includes all routers.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from contextlib import asynccontextmanager

from app.api.endpoints import chat, history, recommendations
from app.database import create_db_and_tables
from app.utils.logging_config import configure_logging

# Set up logging using centralized configuration
configure_logging(logging.WARNING)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for application startup and shutdown."""
    # Startup events
    try:
        logger.info("Initializing database...")
        await create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}", exc_info=True)
        logger.warning("Application will continue without full database functionality")
    
    yield  # This separates startup from shutdown events
    
    # Shutdown events can be added here if needed

# Create FastAPI app
app = FastAPI(
    title="GenAI Research Assistant",
    description="A multi-agent AI system for research assistance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])

@app.get("/")
async def root():
    """Root endpoint returning a welcome message."""
    return {"message": "Welcome to the GenAI Research Assistant API. Please refer to the documentation for more information using docs endpoint."}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )