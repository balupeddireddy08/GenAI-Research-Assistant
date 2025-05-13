"""
Main API router configuration for the GenAI Research Assistant.
This file defines the main API router and includes all endpoint routers.
"""
from fastapi import APIRouter

from app.api.endpoints import chat, history, recommendations, models

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(models.router, prefix="/models", tags=["models"])