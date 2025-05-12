"""
Conversation history endpoint API for the GenAI Research Assistant.
This file defines API routes for managing conversation history, including listing
conversations, retrieving conversation details, and deleting conversations.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func
from typing import List, Optional
import logging
import datetime

from app.database import get_db
from app.schemas.conversation import ConversationResponse, ConversationDetail
from app.models.conversation import Conversation, Message
from app.services.chat_service import generate_conversation_title

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[dict])
async def get_history(
    skip: int = 0, 
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation history with pagination.
    """
    try:
        # Get current date for filtering out future dates
        current_date = datetime.datetime.now()
        
        # Query conversations ordered by most recent
        # Adding filter to exclude conversations with future dates
        result = await db.execute(
            select(Conversation)
            .where(Conversation.updated_at <= current_date)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        
        conversations = result.scalars().all()
        
        # Format the result
        history = []
        
        for conv in conversations:
            # Get message count
            message_count_query = select(func.count()).select_from(Message).where(Message.conversation_id == conv.id)
            message_count_result = await db.execute(message_count_query)
            message_count = message_count_result.scalar()
            
            # Extract summary from metadata if available
            summary = None
            if conv.meta_data and "summary" in conv.meta_data:
                summary = conv.meta_data["summary"]
                
            # Format date
            created_at = conv.created_at.isoformat() if conv.created_at else None
            updated_at = conv.updated_at.isoformat() if conv.updated_at else None
            
            # Debug logging to help troubleshoot date issues
            logger.info(f"Conversation {conv.id} dates: created={created_at}, updated={updated_at}")
            
            history.append({
                "id": conv.id,
                "title": conv.title,
                "created_at": created_at,
                "updated_at": updated_at,
                "message_count": message_count,
                "summary": summary
            })
            
        return history
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


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


@router.post("/regenerate-titles")
async def regenerate_conversation_titles(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate titles for all existing conversations.
    This is useful for fixing generic titles like "hi" in the history sidebar.
    """
    try:
        # Start the background task to update titles
        background_tasks.add_task(update_all_conversation_titles)
        
        return {"status": "success", "message": "Title regeneration started in the background"}
        
    except Exception as e:
        logger.error(f"Error starting title regeneration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start title regeneration: {str(e)}")


async def update_all_conversation_titles():
    """
    Background task to update all conversation titles.
    """
    from app.database import get_async_session
    
    # Create a new session for this background task
    async_session = await get_async_session()
    
    async with async_session() as db:
        try:
            # Get all conversations
            result = await db.execute(select(Conversation))
            conversations = result.scalars().all()
            
            updated_count = 0
            
            # Process each conversation
            for conversation in conversations:
                # Skip conversations with good titles (longer than 15 chars and not just "hi", etc.)
                if len(conversation.title) > 15 and conversation.title not in ["Research Conversation", "New Conversation"]:
                    continue
                
                # Get messages for this conversation
                msg_result = await db.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.created_at)
                )
                messages = msg_result.scalars().all()
                
                if len(messages) < 2:
                    continue  # Skip conversations with too few messages
                
                # Format messages for title generation
                formatted_messages = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in messages
                ]
                
                # Generate a new title
                new_title = await generate_conversation_title(formatted_messages)
                
                # If title generation failed, use the first user message
                if new_title == "Research Conversation":
                    # Find first user message
                    first_user_message = next((msg.content for msg in messages if msg.role == "user"), "")
                    if first_user_message:
                        # Use truncated user message
                        truncated_msg = first_user_message[:30].strip()
                        if len(first_user_message) > 30:
                            truncated_msg += "..."
                        new_title = truncated_msg
                
                # Update the title
                if new_title != conversation.title:
                    conversation.title = new_title
                    updated_count += 1
            
            # Save all changes
            await db.commit()
            logger.info(f"Updated {updated_count} conversation titles")
            
        except Exception as e:
            logger.error(f"Error updating conversation titles: {str(e)}")
            await db.rollback()


@router.get("/fix-future-dates", response_model=dict)
async def fix_future_dates(
    db: AsyncSession = Depends(get_db)
):
    """
    Diagnostic endpoint to find and fix conversations with future dates.
    """
    try:
        import datetime
        current_date = datetime.datetime.now()
        
        # Query to find conversations with future dates
        result = await db.execute(
            select(Conversation)
            .where(Conversation.updated_at > current_date)
        )
        
        future_conversations = result.scalars().all()
        fixed_count = 0
        
        # Log the future dated conversations
        logger.info(f"Found {len(future_conversations)} conversations with future dates")
        
        # Fix each one by setting updated_at to current date
        for conv in future_conversations:
            logger.info(f"Fixing future date on conversation {conv.id}: {conv.updated_at}")
            conv.updated_at = current_date
            fixed_count += 1
        
        # Commit the changes
        await db.commit()
        
        return {
            "status": "success",
            "found": len(future_conversations),
            "fixed": fixed_count,
            "current_date": current_date.isoformat()
        }
    except Exception as e:
        logger.error(f"Error fixing future dates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fix future dates: {str(e)}")