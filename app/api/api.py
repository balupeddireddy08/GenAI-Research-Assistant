from fastapi import APIRouter
from app.api.endpoints import chat, history, recommendations

# Create main API router
api_router = APIRouter()

# Include routers from all endpoint modules
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])