"""
Chat endpoint API for the GenAI Research Assistant.
This file defines the API routes for chat functionality, including sending messages,
creating conversations, and retrieving AI responses.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid

from app.database import get_db
from app.schemas.conversation import ChatRequest, ChatResponse, ConversationCreate, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.services.chat_service import process_message
from app.models.conversation import Conversation, Message

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to the GenAI Research Assistant and get a response.
    If no conversation_id is provided, a new conversation will be created.
    """
    conversation_id = request.conversation_id
    
    # Create a new conversation if needed
    if not conversation_id:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title=request.message[:50] + ("..." if len(request.message) > 50 else ""),
            user_id=None,  # Could be retrieved from auth token in the future
            metadata={}
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conversation_id = conversation.id
    else:
        # Verify conversation exists
        conversation = await db.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Store user message
    user_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        meta_data=request.metadata or {}
    )
    db.add(user_message)
    await db.commit()
    
    # Process message with the AI service
    ai_response = await process_message(
        conversation_id=conversation_id,
        user_message=request.message,
        message_history=await get_conversation_messages(db, conversation_id),
        db=db
    )
    
    # Return the response
    return ChatResponse(
        conversation_id=conversation_id,
        message=MessageResponse(
            id=ai_response.id,
            conversation_id=conversation_id,
            role=ai_response.role,
            content=ai_response.content,
            created_at=ai_response.created_at,
            metadata=ai_response.meta_data
        ),
        recommendations=ai_response.meta_data.get("recommendations") if ai_response.meta_data else None
    )


async def get_conversation_messages(db: AsyncSession, conversation_id: str) -> List[Message]:
    """Helper function to get all messages in a conversation."""
    result = await db.execute(
        "SELECT * FROM messages WHERE conversation_id = :conversation_id ORDER BY created_at ASC",
        {"conversation_id": conversation_id}
    )
    return result.all()