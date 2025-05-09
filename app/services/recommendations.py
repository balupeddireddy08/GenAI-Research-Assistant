"""
Recommendations service for the GenAI Research Assistant.
This file provides functionality for generating content recommendations based on
conversation history, helping users discover related research and resources.
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import json

from app.models.conversation import Conversation, Message
from app.utils.llm_utils import get_llm_client, get_completion
from app.config import settings


async def get_recommendations_for_conversation(
    conversation_id: str,
    db: AsyncSession
) -> List[Dict[str, Any]]:
    """
    Generate content recommendations based on the conversation history.
    
    Args:
        conversation_id: The ID of the conversation
        db: Database session
        
    Returns:
        List of recommendation objects
    """
    # Get the conversation
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        return []
    
    # Get the messages for this conversation
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    # Format the conversation for analysis
    conversation_text = "\n\n".join([
        f"{msg.role.upper()}: {msg.content}" 
        for msg in messages
    ])
    
    # Check if there are existing recommendations in the latest assistant message
    latest_assistant_messages = [msg for msg in messages if msg.role == "assistant"]
    if latest_assistant_messages:
        latest_message = latest_assistant_messages[-1]
        if latest_message.meta_data and "recommendations" in latest_message.meta_data:
            return latest_message.meta_data["recommendations"]
    
    # Initialize LLM client
    llm_client = get_llm_client(settings)
    
    # Generate recommendations based on conversation content
    recommendations = await _generate_recommendations(llm_client, conversation_text, conversation.title)
    
    return recommendations


async def _generate_recommendations(
    llm_client: Any,
    conversation_text: str,
    conversation_title: str
) -> List[Dict[str, Any]]:
    """
    Generate recommendations using the LLM based on conversation content.
    
    Args:
        llm_client: The LLM client to use
        conversation_text: The text of the conversation
        conversation_title: The title of the conversation
        
    Returns:
        List of recommendation objects
    """
    # Truncate conversation text if it's too long
    max_length = 8000  # Arbitrary limit to avoid context length issues
    if len(conversation_text) > max_length:
        conversation_text = conversation_text[:max_length] + "...[truncated]"
    
    prompt = f"""
    Based on the following conversation, generate 3-5 recommendations for related content 
    that would be valuable for the user to explore next. These could be research papers, 
    topics, concepts, technologies, or resources that are related to what they're interested in.
    
    Conversation title: {conversation_title}
    
    Conversation content:
    {conversation_text}
    
    For each recommendation, provide:
    1. title: A clear, concise title
    2. description: A brief description (1-2 sentences) explaining why it's relevant
    3. type: One of "paper", "topic", "concept", "technology", "resource"
    4. relevance_score: A number between 0 and 1 indicating how relevant this is to the conversation
    
    Return a JSON array of recommendations.
    """
    
    result = await get_completion(
        llm_client,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Generate recommendations based on this conversation"}
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        recommendations_data = json.loads(result)
        if isinstance(recommendations_data, dict) and "recommendations" in recommendations_data:
            return recommendations_data["recommendations"]
        elif isinstance(recommendations_data, list):
            return recommendations_data
        else:
            return []
    except (json.JSONDecodeError, TypeError):
        # Fallback if the LLM doesn't return valid JSON
        return []