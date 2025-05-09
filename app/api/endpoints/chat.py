"""
Chat endpoint API for the GenAI Research Assistant.
This file defines the API routes for chat functionality, including sending messages,
creating conversations, and retrieving AI responses.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
import uuid
import logging

from app.database import get_db
from app.schemas.conversation import ChatRequest, ChatResponse, ConversationCreate, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.services.chat_service import process_message
from app.models.conversation import Conversation, Message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        conversation_id = request.conversation_id
        
        # Create a new conversation if needed
        if not conversation_id:
            logger.info("Creating new conversation")
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
            logger.info(f"Created new conversation with ID: {conversation_id}")
        else:
            # Verify conversation exists
            logger.info(f"Looking up existing conversation: {conversation_id}")
            conversation = await db.get(Conversation, conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Store user message
        logger.info("Storing user message")
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
        logger.info("Processing message with AI service")
        ai_response = await process_message(
            conversation_id=conversation_id,
            user_message=request.message,
            message_history=await get_conversation_messages(db, conversation_id),
            db=db
        )
        
        # Update conversation timestamp
        logger.info("Updating conversation timestamp")
        await db.execute(
            text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
            {"id": conversation_id}
        )
        
        # Log metadata details
        logger.info(f"Response metadata keys: {ai_response.meta_data.keys() if ai_response.meta_data else 'None'}")
        if "sources" in (ai_response.meta_data or {}):
            logger.info(f"Found {len(ai_response.meta_data['sources'])} sources in response")
        
        # Extract metadata components
        metadata = ai_response.meta_data or {}
        
        # Return the response
        logger.info("Returning response")
        return ChatResponse(
            conversation_id=conversation_id,
            message=MessageResponse(
                id=ai_response.id,
                conversation_id=conversation_id,
                role=ai_response.role,
                content=ai_response.content,
                created_at=ai_response.created_at,
                metadata=metadata
            ),
            recommendations=metadata.get("recommendations"),
            processing_status=metadata.get("processing_status"),
            sources=metadata.get("sources", [])
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_conversation_messages(db: AsyncSession, conversation_id: str) -> List[Message]:
    """Helper function to get all messages in a conversation."""
    try:
        query = text("SELECT * FROM messages WHERE conversation_id = :conversation_id ORDER BY created_at ASC")
        result = await db.execute(query, {"conversation_id": conversation_id})
        return result.all()
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving conversation messages")