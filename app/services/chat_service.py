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
import asyncio

from app.models.conversation import Message, Conversation
from app.config import settings
from app.services.orchestrator import AgentOrchestrator
from app.utils.llm_utils import get_llm_client, get_completion
from app.services.recommendations import get_recommendations_for_conversation
from app.database import get_async_session

# Set up logging
logger = logging.getLogger(__name__)

async def generate_conversation_title(conversation_messages: List[Any]) -> str:
    """
    Generate a title for the conversation.
    
    Args:
        conversation_messages: List of conversation messages
        
    Returns:
        A concise title string for the conversation
    """
    try:
        # Initialize LLM client
        llm_client = get_llm_client(settings)
        
        # Create a prompt for title generation
        prompt = """
        Generate a very brief, concise title (5 words maximum) for the following conversation.
        The title should capture the main topic or theme of the conversation.
        DO NOT use phrases like "Conversation about..." or "Discussion of...".
        Just provide the topic itself, like a document title or article headline.
        """
        
        # Extract main content from user messages
        user_content = []
        for msg in conversation_messages:
            # Handle both dictionary and SQLAlchemy result objects
            if isinstance(msg, dict) and msg.get("role") == "user" and msg.get("content", ""):
                user_content.append(msg.get("content", "")[:200])
            elif hasattr(msg, "role") and msg.role == "user" and msg.content:
                user_content.append(msg.content[:200])
        
        user_content_text = "\n".join(user_content)
        
        # Add a sample of assistant responses
        assistant_sample = []
        for msg in conversation_messages[-3:]:
            # Handle both dictionary and SQLAlchemy result objects
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content", ""):
                assistant_sample.append(msg.get("content", "")[:100])
            elif hasattr(msg, "role") and msg.role == "assistant" and msg.content:
                assistant_sample.append(msg.content[:100])
        
        assistant_sample_text = "\n".join(assistant_sample)
        
        # Combine for context
        content_for_title = f"USER MESSAGES:\n{user_content_text}\n\nASSISTANT RESPONSES (SAMPLE):\n{assistant_sample_text}"
        
        # Get completion from LLM
        title = await get_completion(
            llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content_for_title}
            ]
        )
        
        # Clean up the title - remove quotes and periods
        title = title.strip().strip('"\'').rstrip('.')
        
        # Enforce maximum length
        if len(title) > 50:
            title = title[:47] + "..."
            
        return title
    except Exception as e:
        logger.warning(f"Error generating conversation title: {str(e)}")
        return "Research Conversation"

async def generate_conversation_summary(conversation_messages: List[Any]) -> str:
    """
    Generate a summary of the conversation.
    
    Args:
        conversation_messages: List of conversation messages
        
    Returns:
        A string summary of the conversation
    """
    try:
        # Initialize LLM client
        llm_client = get_llm_client(settings)
        
        # Create a prompt for summarization
        prompt = """
        Summarize the following conversation between a user and an AI assistant. 
        Focus on the main topics, questions asked, and information provided.
        Keep your summary concise (3-4 sentences maximum) and factual.
        """
        
        # Format the conversation for the LLM, using the last 6 messages at most
        formatted_messages = []
        for msg in conversation_messages[-6:]:
            # Handle both dictionary and SQLAlchemy result objects
            if isinstance(msg, dict):
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
            else:
                role = getattr(msg, "role", "unknown").upper()
                content = getattr(msg, "content", "")
                
            if len(content) > 300:
                formatted_content = f"{content[:300]}..."
            else:
                formatted_content = content
                
            formatted_messages.append(f"{role}: {formatted_content}")
            
        formatted_conversation = "\n\n".join(formatted_messages)
        
        # Get completion from LLM
        summary = await get_completion(
            llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": formatted_conversation}
            ]
        )
        
        return summary.strip()
    except Exception as e:
        logger.warning(f"Error generating conversation summary: {str(e)}")
        return "Conversation about various research topics."

async def process_message(
    conversation_id: str,
    user_message: str,
    message_history: List[Any],
    db: AsyncSession
) -> Message:
    """
    Process a user message and generate an AI response.
    
    Args:
        conversation_id: The conversation ID
        user_message: The content of the user's message
        message_history: List of previous messages in the conversation
        db: Database session
        
    Returns:
        The created AI message
    """
    try:
        # Format message history for the orchestrator
        formatted_history = []
        for msg in message_history:
            # Messages from the database have slightly different field names than dict
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                formatted_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            else:
                formatted_history.append(msg)
        
        logger.info(f"Including {len(formatted_history)} messages as context for the LLM")
        
        # Initialize the orchestrator
        orchestrator = AgentOrchestrator(settings)
    
        # Process the message through the orchestrator
        response_content, metadata = await orchestrator.process(
            user_message=user_message,
            conversation_history=formatted_history
        )
    
        # Ensure recommendations are included in metadata if they're not already
        if "recommendations" not in metadata:
            # Generate fallback recommendations
            try:
                # Create simple recommendations based on the user message
                words = user_message.lower().split()
                key_terms = [word for word in words if len(word) > 3 and word not in 
                            {'what', 'when', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how',
                             'about', 'from', 'into', 'after', 'with', 'this', 'that', 'these', 'those'}]
                
                # Generate basic recommendations
                recommendations = []
                types = ["topic", "concept", "research_area"]
                
                for i, term in enumerate(key_terms[:3]):
                    recommendations.append({
                        "title": f"More about {term}",
                        "description": f"Explore related information about {term}.",
                        "type": types[i % len(types)],
                        "relevance_score": 0.8 - (i * 0.1)
                    })
                
                if recommendations:
                    metadata["recommendations"] = recommendations
            except Exception as e:
                logger.warning(f"Error generating fallback recommendations: {str(e)}")
        
        # Create the assistant message
        ai_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            meta_data=metadata
        )
    
        # Save to database
        db.add(ai_message)
        await db.commit()
        await db.refresh(ai_message)
        
        # Generate and update the conversation summary and title in the background
        # Pass only conversation ID and messages, not the DB session
        asyncio.create_task(update_conversation_info(
            conversation_id, 
            message_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response_content}
            ]
        ))
        
        return ai_message
    except Exception as e:
        logger.error(f"Error in chat service: {str(e)}", exc_info=True)
        raise

async def update_conversation_info(
    conversation_id: str,
    conversation_messages: List[Dict[str, str]]
) -> None:
    """
    Update conversation metadata like summary and title in the background.
    
    Args:
        conversation_id: The conversation ID
        conversation_messages: Complete list of messages in the conversation
    """
    # Create a new database session for this background task
    async_session = await get_async_session()
    
    async with async_session() as db:
        try:
            # Only generate summaries when there are enough messages
            if len(conversation_messages) < 3:
                return
                
            # Initialize LLM client
            llm_client = get_llm_client(settings)
            
            # Generate conversation summary
            summary = await generate_conversation_summary(conversation_messages)
            
            # Generate a title based on the conversation content
            title = await generate_conversation_title(conversation_messages)
            
            # Get the conversation from the database
            conversation = await db.get(Conversation, conversation_id)
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found when updating metadata")
                return
            
            # Always update the title for new conversations (default title is "Research Conversation")    
            should_update_title = True
            
            # For existing conversations with custom titles, only update if current title is generic
            if conversation.title != "Research Conversation" and not conversation.title.endswith("..."):
                # Only update title if it's still a generic one
                generic_titles = ["Research Conversation", "New Conversation", "Conversation"]
                should_update_title = conversation.title in generic_titles
            
            # Update the title if needed
            if should_update_title and title:
                # Extract the first user message to use as a fallback title
                first_user_message = ""
                for msg in conversation_messages:
                    # Handle both dictionary and SQLAlchemy result objects
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        first_user_message = msg.get("content", "")
                        break
                    elif hasattr(msg, "role") and msg.role == "user":
                        first_user_message = msg.content
                        break
                
                # Use a shortened version of the first message if title generation failed
                if title == "Research Conversation" and first_user_message:
                    # Use the first 30 chars of user message as a title if LLM title failed
                    truncated_msg = first_user_message[:30].strip()
                    if len(first_user_message) > 30:
                        truncated_msg += "..."
                    title = truncated_msg
                
                conversation.title = title
                logger.info(f"Updated conversation title to: {title}")
            
            # Store the summary in the conversation metadata
            if not conversation.meta_data:
                conversation.meta_data = {}
                
            conversation.meta_data["summary"] = summary
            
            # Save changes
            await db.commit()
            logger.info(f"Successfully updated metadata for conversation {conversation_id}")
        
        except Exception as e:
            logger.error(f"Error updating conversation info: {str(e)}", exc_info=True)
            await db.rollback()
            # Don't propagate the exception since this runs in the background 