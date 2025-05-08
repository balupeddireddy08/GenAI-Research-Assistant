from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.database import get_db
from app.services.recommendations import get_recommendations_for_conversation

router = APIRouter()


@router.get("/{conversation_id}", response_model=List[Dict[str, Any]])
async def get_recommendations(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get content recommendations based on the conversation.
    """
    # Check if conversation exists
    conversation = await db.get("conversations", conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get recommendations based on conversation content
    recommendations = await get_recommendations_for_conversation(conversation_id, db)
    
    return recommendations