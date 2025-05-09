"""
Chat service for handling message processing in the GenAI Research Assistant.
This file contains functionality for processing user messages through the agent
orchestrator, saving responses to the database, and managing conversation state.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid
import logging
from datetime import datetime

from app.models.conversation import Message
from app.config import settings
from app.services.orchestrator import AgentOrchestrator

# Set up logging
logger = logging.getLogger(__name__)

# Define how many previous messages to include for context
CONTEXT_MESSAGE_LIMIT = 10

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
    
    # Format message history for the LLM context, limiting to the most recent messages
    # Always include at least the system message (if any) and the last few messages
    system_messages = [msg for msg in message_history if msg.role == 'system']
    non_system_messages = [msg for msg in message_history if msg.role != 'system']
    
    # Take the last N non-system messages
    recent_messages = non_system_messages[-CONTEXT_MESSAGE_LIMIT:] if non_system_messages else []
    
    # Combine system messages with recent messages
    context_messages = system_messages + recent_messages
    
    # Format for the LLM
    formatted_history = [
        {"role": msg.role, "content": msg.content}
        for msg in context_messages
    ]
    
    # Log the context size
    logger.info(f"Including {len(formatted_history)} messages as context for the LLM")
    if len(message_history) > len(formatted_history):
        logger.info(f"Truncated {len(message_history) - len(formatted_history)} older messages from context")
    
    # Process the message through the orchestrator
    response_content, metadata = await orchestrator.process(
        user_message=user_message,
        conversation_history=formatted_history
    )
    
    # Add context information to metadata
    metadata["context_size"] = len(formatted_history)
    metadata["total_conversation_messages"] = len(message_history) + 1  # +1 for the current message
    
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
        text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
        {"id": conversation_id}
    )
    await db.commit()
    
    return assistant_message