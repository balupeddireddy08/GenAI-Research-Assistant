"""
Conversation history endpoint API for the GenAI Research Assistant.
This file defines API routes for managing conversation history, including listing
conversations, retrieving conversation details, and deleting conversations.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from typing import List
import logging

from app.database import get_db
from app.schemas.conversation import ConversationResponse, ConversationDetail
from app.models.conversation import Conversation, Message

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a list of conversation history.
    """
    try:
        # Query conversations ordered by most recent first
        result = await db.execute(
            select(Conversation)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        conversations = result.scalars().all()
        
        # Convert MetaData objects to dictionaries
        response_conversations = []
        for conv in conversations:
            # Create a dictionary representation and ensure metadata is a dict
            conv_dict = {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "user_id": conv.user_id,
                "metadata": dict(conv.meta_data) if conv.meta_data else {}
            }
            response_conversations.append(conv_dict)
            
        return response_conversations
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        # Return empty list instead of throwing an error
        return []


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific conversation with all its messages.
    """
    try:
        # Get the conversation
        conversation = await db.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get the messages for this conversation
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages_raw = result.scalars().all()
        
        # Convert Message objects to properly formatted dictionaries
        messages = []
        for msg in messages_raw:
            msg_dict = {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "metadata": dict(msg.meta_data) if msg.meta_data else {}
            }
            messages.append(msg_dict)
        
        # Create response with conversation and its messages
        # Ensure metadata is properly converted to a dictionary
        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat() if conversation.created_at else None,
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
            user_id=conversation.user_id,
            metadata=dict(conversation.meta_data) if conversation.meta_data else {},
            messages=messages
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a conversation and all its messages.
    """
    try:
        conversation = await db.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete the conversation (cascade delete will remove messages)
        await db.delete(conversation)
        await db.commit()
        
        return None
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")