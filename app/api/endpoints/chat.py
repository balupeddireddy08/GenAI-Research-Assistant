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
from pydantic import BaseModel
import datetime
import random

from app.database import get_db
from app.schemas.conversation import ChatRequest, ChatResponse, ConversationCreate, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.services.chat_service import process_message
from app.models.conversation import Conversation, Message
from app.utils.llm_utils import get_llm_client, get_completion
from app.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# New schema for prompt enhancement
class PromptEnhanceRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None

class PromptEnhanceResponse(BaseModel):
    enhanced_prompt: str

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
        # Make sure each conversation gets a unique timestamp
        # First, get the current timestamp
        now = datetime.datetime.now()
        # Add a small random offset to ensure uniqueness (1-1000 milliseconds)
        random_ms = random.randint(1, 1000)
        unique_now = now + datetime.timedelta(milliseconds=random_ms)
        
        await db.execute(
            text("UPDATE conversations SET updated_at = :updated_at WHERE id = :id"),
            {"updated_at": unique_now.isoformat(), "id": conversation_id}
        )
        
        # Extract metadata components
        metadata = ai_response.meta_data or {}
        
        # Log metadata details
        logger.info(f"Response metadata keys: {metadata.keys() if metadata else 'None'}")
        if "sources" in metadata:
            logger.info(f"Found {len(metadata['sources'])} sources in response")
        if "recommendations" in metadata:
            logger.info(f"Found {len(metadata['recommendations'])} recommendations in response")
        
        # Create recommendations array for the response
        recommendations = metadata.get("recommendations", [])
        
        # Extract recommendation tags for UI filtering
        recommendation_tags = []
        if recommendations:
            # Collect unique recommendation types if available
            recommendation_tags = list(set(
                rec.get("type") for rec in recommendations 
                if rec.get("type") and isinstance(rec.get("type"), str)
            ))
            # Add these to metadata for frontend use
            metadata["recommendation_tags"] = recommendation_tags
            logger.info(f"Extracted recommendation tags: {recommendation_tags}")
        
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
            recommendations=recommendations,  # Explicitly include recommendations
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

@router.post("/enhance-prompt", response_model=PromptEnhanceResponse)
async def enhance_prompt(
    request: PromptEnhanceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Enhance a user's prompt to make it more effective for the research assistant.
    Takes the user's input and transforms it into a more effective research query.
    """
    try:
        logger.info(f"Enhancing prompt: {request.prompt[:50]}...")
        
        # Initialize the LLM client directly
        client_tuple = get_llm_client(settings)  # This returns (client, provider_type)
        
        # Get recent conversation messages if available (up to 5 messages)
        recent_messages = []
        if request.conversation_id:
            try:
                conv_messages = await get_conversation_messages(db, request.conversation_id)
                # Format the last 5 messages to provide context
                recent_messages = [
                    f"{msg.role}: {msg.content}"
                    for msg in conv_messages[-5:]
                ]
            except Exception as e:
                logger.warning(f"Could not retrieve conversation history: {e}")
        
        # Create an improved system prompt for enhancement
        system_prompt = """
        You are an expert research prompt enhancer for academic and scientific topics. Your goal is to transform user inputs into highly effective, well-structured research queries.
        
        IMPORTANT INSTRUCTIONS:
        
        1. ANALYZE the user's original query to understand their research intent
        
        2. ENHANCE the prompt by:
           - Making it more specific, focused and academically rigorous
           - Structuring it as a direct question or request for information
           - Adding relevant academic terminology and framing
           - Including specific request for sources, evidence, or explanations
           - Preserving the original intent and core meaning
        
        3. OUTPUT FORMAT: ONLY return the enhanced prompt itself. 
           - DO NOT explain your methodology
           - DO NOT add instructional text about how to search
           - DO NOT provide a response to the query
           - DO NOT structure your response as a tutorial or guide
           - DO NOT include explanations, commentary, or any meta-text
        
        4. CRITICAL: Your task is ONLY to rewrite and improve the query, NOT to answer it or explain how to answer it.
        
        If provided with conversation context, use it to better understand the user's research area and interests.
        
        EXAMPLES OF GOOD TRANSFORMATIONS:
        
        Original: "tell me about transformers"
        Good: "Provide a comprehensive analysis of Transformer architecture in deep learning, including its key components, attention mechanisms, and how it revolutionized NLP tasks. Include comparisons with RNN and LSTM models and cite influential research papers."
        
        Original: "NLP latest techniques"
        Good: "What are the most significant advancements in Natural Language Processing from 2023-2024? Focus on architectural innovations beyond standard Transformer models, emergent capabilities in large language models, and current state-of-the-art approaches for low-resource languages and multimodal integration."
        
        Original: "Find the latest AI research"
        Good: "What are the breakthrough AI research papers published in the past 3 months across major conferences like NeurIPS, ICML, and ACL? Focus on papers with novel methodologies, significant performance improvements, or applications in emerging domains."
        """
        
        # Include recent conversation context if available
        context_text = ""
        if recent_messages:
            context_text = "Recent conversation context:\n" + "\n".join(recent_messages) + "\n\n"
        
        # Get enhanced prompt from LLM
        enhanced_prompt = await get_completion(
            client_tuple,  # Pass the entire tuple (client, provider)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context_text}Original prompt: {request.prompt}\n\nEnhanced prompt: (ONLY return the improved query text, NO explanations or methodology)"}
            ],
        )
        
        # Log the result
        logger.info(f"Enhanced prompt: {enhanced_prompt[:50]}...")
        return PromptEnhanceResponse(enhanced_prompt=enhanced_prompt)
        
    except Exception as e:
        logger.error(f"Error enhancing prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to enhance prompt: {str(e)}")