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
from datetime import datetime, timedelta
import time

from app.models.conversation import Message, Conversation
from app.config import settings
from app.services.orchestrator import AgentOrchestrator
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

# Get context message limit from settings
# CONTEXT_MESSAGE_LIMIT = 10

async def generate_conversation_title(conversation_history: List[Dict[str, str]]) -> str:
    """
    Generate an ultra-concise title (less than 10 words) for a conversation.
    
    Args:
        conversation_history: List of message dictionaries with 'role' and 'content'
        
    Returns:
        A very short title representing the conversation topic
    """
    try:
        # Initialize LLM client
        llm_client = get_llm_client(settings)
        
        # Create a prompt for title generation
        system_prompt = """
        You are an AI assistant that creates extremely concise conversation titles.
        Create a title that is LESS THAN 10 WORDS describing the main topic of the conversation.
        The title should capture the essence of what the user is seeking help with.
        DO NOT use phrases like "Conversation about..." or "Discussion of..."
        ONLY return the title itself - nothing else.
        """
        
        # Format the conversation for the prompt
        conversation_text = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content'][:150]}..." if len(msg['content']) > 150 else f"{msg['role'].upper()}: {msg['content']}"
            for msg in conversation_history
        ])
        
        # Create message payload for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a concise title for this conversation:\n\n{conversation_text}"}
        ]
        
        # Get the title from the LLM
        title = await get_completion(
            llm_client,
            messages=messages,
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=20     # Very strict limit to enforce brevity
        )
        
        # Clean up the title
        title = title.strip().rstrip('.').strip('"')
        
        # Ensure it's really short - truncate if necessary
        words = title.split()
        if len(words) > 10:
            title = " ".join(words[:10]) + "..."
            
        return title
    except Exception as e:
        logger.error(f"Error generating conversation title: {str(e)}", exc_info=True)
        return "Untitled conversation"

async def generate_conversation_summary(conversation_history: List[Dict[str, str]]) -> str:
    """
    Generate a brief summary of the conversation using the LLM.
    
    Args:
        conversation_history: List of message dictionaries with 'role' and 'content'
        
    Returns:
        A concise summary of the conversation
    """
    try:
        # Initialize LLM client
        llm_client = get_llm_client(settings)
        
        # Create a prompt for summarization
        system_prompt = """
        You are an AI assistant that summarizes conversations. Please create a brief 1-2 sentence 
        summary of the following conversation. Focus on the main topics and user's primary questions 
        or interests. Be concise and objective.
        """
        
        # Format the conversation for the prompt
        conversation_text = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in conversation_history
        ])
        
        # Create message payload for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please summarize this conversation:\n\n{conversation_text}"}
        ]
        
        # Get the summary from the LLM
        summary = await get_completion(
            llm_client,
            messages=messages,
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=100    # Limit to a short summary
        )
        
        return summary.strip()
    except Exception as e:
        logger.error(f"Error generating conversation summary: {str(e)}", exc_info=True)
        return "Summary generation failed"

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
    # Track start time for performance metrics
    start_time = time.time()
    
    # Initialize the orchestrator agent
    orchestrator = AgentOrchestrator(settings)
    
    # Get context message limit from settings
    context_limit = settings.CONTEXT_MESSAGE_LIMIT
    
    # Format message history for the LLM context
    # First, ensure system messages are preserved regardless of age
    system_messages = [msg for msg in message_history if msg.role == 'system']
    
    # Then get the most recent non-system messages up to the limit
    non_system_messages = [msg for msg in message_history if msg.role != 'system']
    recent_non_system = non_system_messages[-context_limit:] if non_system_messages else []
    
    # Create final context by combining both, but preserving chronological order
    # First, identify which system messages are already in the recent messages timeline
    system_ids = {msg.id for msg in system_messages}
    
    # Start with all messages in chronological order
    all_messages_chronological = message_history
    
    # If we have too many messages, restrict to the limit while preserving system messages
    if len(all_messages_chronological) > context_limit and len(system_messages) < context_limit:
        # Calculate how many non-system messages we can include
        non_system_slots = context_limit - len(system_messages)
        
        # Get the most recent non-system messages
        recent_non_system = non_system_messages[-non_system_slots:] if non_system_messages else []
        
        # Combine system and recent non-system messages
        included_ids = system_ids.union({msg.id for msg in recent_non_system})
        
        # Filter the chronological list to only include the messages we want
        context_messages = [msg for msg in all_messages_chronological if msg.id in included_ids]
        
        # Sort by creation timestamp to ensure proper chronological order
        context_messages.sort(key=lambda msg: msg.created_at)
    else:
        # If we have few enough messages, include all in chronological order
        context_messages = all_messages_chronological[-context_limit:] if all_messages_chronological else []
    
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
    
    # Calculate processing time
    end_time = time.time()
    processing_time_ms = int((end_time - start_time) * 1000)
    
    # Add context information to metadata
    if metadata is None:
        metadata = {}
        
    # Add basic context information
    metadata["context_size"] = len(formatted_history)
    metadata["total_conversation_messages"] = len(message_history) + 1  # +1 for the current message
    
    # Add model information
    metadata["model_used"] = settings.PRIMARY_LLM
    
    # Add performance metrics
    metadata["processing_time_ms"] = processing_time_ms
    
    # Add message composition statistics
    metadata["message_composition"] = {
        "user_messages": sum(1 for msg in message_history if msg.role == "user"),
        "assistant_messages": sum(1 for msg in message_history if msg.role == "assistant"),
        "system_messages": sum(1 for msg in message_history if msg.role == "system")
    }
    
    # Add agent information if available from orchestrator
    if hasattr(orchestrator, 'get_active_agents'):
        try:
            metadata["agents_used"] = orchestrator.get_active_agents()
        except Exception as e:
            logger.warning(f"Could not retrieve active agents: {str(e)}")
    
    # Generate conversation summary if there are enough messages
    if not "conversation_summary" in metadata and len(message_history) >= 3:
        try:
            # Include the current user message in the summary input
            summary_input = formatted_history + [{"role": "user", "content": user_message}]
            metadata["conversation_summary"] = await generate_conversation_summary(summary_input)
            logger.info("Generated conversation summary")
            
            # Generate concise title for sidebar display
            conversation_title = await generate_conversation_title(summary_input)
            metadata["conversation_title"] = conversation_title
            logger.info(f"Generated conversation title: {conversation_title}")
            
            # Update the conversation title in the database
            try:
                conversation = await db.get(Conversation, conversation_id)
                if conversation:
                    # Only update if the title is generic (likely auto-generated from the first message)
                    if conversation.title.endswith("...") or len(conversation.title.split()) <= 2:
                        conversation.title = conversation_title
                        logger.info(f"Updated conversation title in database to: {conversation_title}")
            except Exception as e:
                logger.warning(f"Could not update conversation title in database: {str(e)}")
            
        except Exception as e:
            logger.warning(f"Could not generate conversation summary: {str(e)}")
            metadata["conversation_summary"] = "Summary generation failed"
    
    # Create the assistant's response message
    assistant_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        created_at=datetime.now(),
        meta_data=metadata
    )
    
    # Save the message to the database
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    
    # Log performance metrics
    logger.info(f"Response generated in {processing_time_ms}ms using {settings.PRIMARY_LLM}")
    
    # Update conversation's updated_at timestamp
    await db.execute(
        text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
        {"id": conversation_id}
    )
    await db.commit()
    
    return assistant_message