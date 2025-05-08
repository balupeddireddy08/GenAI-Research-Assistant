"""
Chat service for handling message processing in the GenAI Research Assistant.
This file contains functionality for processing user messages through the agent
orchestrator, saving responses to the database, and managing conversation state.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime

from app.models.conversation import Message
from app.config import settings
from app.services.orchestrator import AgentOrchestrator


async def process_message(
    conversation_id: str,
    user_message: str,
    message_history: List[Message],
    db: AsyncSession,
) -> Message:
    """
    Process a user message through the multi-agent system and return an AI response.
    
    Args:
        conversation_id: The ID of the conversation
        user_message: The user's message content
        message_history: List of previous messages in the conversation
        db: Database session
        
    Returns:
        Message: The assistant's response message object
    """
    # Initialize the orchestrator agent
    orchestrator = AgentOrchestrator(settings)
    
    # Format message history for the LLM context
    formatted_history = [
        {"role": msg.role, "content": msg.content}
        for msg in message_history
    ]
    
    # Process the message through the orchestrator
    response_content, metadata = await orchestrator.process(
        user_message=user_message,
        conversation_history=formatted_history
    )
    
    # Create the assistant's response message
    assistant_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        created_at=datetime.now(),
        meta_data=metadata or {}
    )
    
    # Save the message to the database
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    
    # Update conversation's updated_at timestamp
    await db.execute(
        "UPDATE conversations SET updated_at = NOW() WHERE id = :id",
        {"id": conversation_id}
    )
    await db.commit()
    
    return assistant_message