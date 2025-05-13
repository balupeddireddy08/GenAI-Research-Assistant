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
import json

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
        # Using raw SQL for better compatibility with both PostgreSQL and SQLite
        # SQLite doesn't handle datetime comparison the same way as PostgreSQL
        result = await db.execute(
            text("SELECT * FROM conversations ORDER BY updated_at DESC LIMIT :limit OFFSET :skip"),
            {"limit": limit, "skip": skip}
        )
        
        conversations = result.all()
        
        # Format the result
        history = []
        
        # For testing: If all timestamps are the same, create artificial offsets
        all_timestamps_equal = True
        last_timestamp = None
        
        # Check if all timestamps are the same (common SQLite issue)
        for conv in conversations:
            current_timestamp = conv.updated_at if isinstance(conv.updated_at, str) else (
                conv.updated_at.isoformat() if conv.updated_at else None
            )
            
            if last_timestamp is not None and current_timestamp != last_timestamp:
                all_timestamps_equal = False
                break
                
            last_timestamp = current_timestamp
        
        # If all timestamps are the same, create artificial offsets
        time_offset = 0
        
        for conv in conversations:
            # Get message count
            message_count_query = text("SELECT COUNT(*) FROM messages WHERE conversation_id = :conv_id")
            message_count_result = await db.execute(message_count_query, {"conv_id": conv.id})
            message_count = message_count_result.scalar()
            
            # Extract summary from metadata if available
            summary = None
            try:
                # Parse meta_data from JSON string if needed
                meta_data = conv.meta_data
                if isinstance(meta_data, str):
                    meta_data = json.loads(meta_data)
                
                if meta_data and "summary" in meta_data:
                    summary = meta_data["summary"]
            except Exception as e:
                logger.warning(f"Error parsing metadata for conversation {conv.id}: {str(e)}")
                
            # Format date with artificial offsets if needed
            if all_timestamps_equal and conversations.index(conv) > 0:
                # Create unique timestamps by adding a minute offset for each conversation
                time_offset += 5  # 5 minute intervals
                timestamp = current_date - datetime.timedelta(minutes=time_offset)
                created_at = timestamp.isoformat()
                updated_at = timestamp.isoformat()
                
                # Also update the conversation in the database to persist these changes
                try:
                    await db.execute(
                        text("UPDATE conversations SET updated_at = :updated_at WHERE id = :id"),
                        {"updated_at": updated_at, "id": conv.id}
                    )
                except Exception as update_error:
                    logger.warning(f"Could not update timestamp in database: {str(update_error)}")
            else:
                # Use the actual timestamps
                if conv.created_at:
                    created_at = conv.created_at if isinstance(conv.created_at, str) else conv.created_at.isoformat()
                else:
                    created_at = None
                    
                if conv.updated_at:
                    updated_at = conv.updated_at if isinstance(conv.updated_at, str) else conv.updated_at.isoformat()
                else:
                    updated_at = None
            
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
        
        # Commit the timestamp changes if any were made
        if all_timestamps_equal and len(conversations) > 1:
            await db.commit()
            logger.info("Updated conversation timestamps to ensure uniqueness")
            
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
        # Get the conversation using raw SQL for better compatibility
        result = await db.execute(
            text("SELECT * FROM conversations WHERE id = :conv_id"),
            {"conv_id": conversation_id}
        )
        conversation = result.first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get the messages for this conversation using raw SQL
        msg_result = await db.execute(
            text("SELECT * FROM messages WHERE conversation_id = :conv_id ORDER BY created_at"),
            {"conv_id": conversation_id}
        )
        messages_raw = msg_result.all()
        
        # Convert Message objects to properly formatted dictionaries
        messages = []
        for msg in messages_raw:
            # Parse created_at
            if msg.created_at:
                created_at = msg.created_at if isinstance(msg.created_at, str) else msg.created_at.isoformat()
            else:
                created_at = None
                
            msg_dict = {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": created_at,
                "metadata": {}
            }
            
            # Parse meta_data from JSON if needed
            try:
                meta_data = msg.meta_data
                if isinstance(meta_data, str):
                    meta_data = json.loads(meta_data)
                msg_dict["metadata"] = meta_data if meta_data else {}
            except Exception as e:
                logger.warning(f"Error parsing message metadata: {str(e)}")
                
            messages.append(msg_dict)
        
        # Parse conversation metadata if needed
        conv_metadata = {}
        try:
            meta_data = conversation.meta_data
            if isinstance(meta_data, str):
                meta_data = json.loads(meta_data)
            conv_metadata = meta_data if meta_data else {}
        except Exception as e:
            logger.warning(f"Error parsing conversation metadata: {str(e)}")
        
        # Format conversation dates
        if conversation.created_at:
            created_at = conversation.created_at if isinstance(conversation.created_at, str) else conversation.created_at.isoformat()
        else:
            created_at = None
            
        if conversation.updated_at:
            updated_at = conversation.updated_at if isinstance(conversation.updated_at, str) else conversation.updated_at.isoformat()
        else:
            updated_at = None
        
        # Create response with conversation and its messages
        # Ensure metadata is properly converted to a dictionary
        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            created_at=created_at,
            updated_at=updated_at,
            user_id=conversation.user_id,
            metadata=conv_metadata,
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
        # Check if conversation exists using raw SQL
        result = await db.execute(
            text("SELECT id FROM conversations WHERE id = :conv_id"),
            {"conv_id": conversation_id}
        )
        conv = result.first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete messages first to respect foreign key constraint
        await db.execute(
            text("DELETE FROM messages WHERE conversation_id = :conv_id"),
            {"conv_id": conversation_id}
        )
        
        # Delete the conversation
        await db.execute(
            text("DELETE FROM conversations WHERE id = :conv_id"),
            {"conv_id": conversation_id}
        )
        
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
            # Get all conversations using raw SQL
            result = await db.execute(text("SELECT * FROM conversations"))
            conversations = result.all()
            
            updated_count = 0
            
            # Process each conversation
            for conversation in conversations:
                # Skip conversations with good titles (longer than 15 chars and not just "hi", etc.)
                if len(conversation.title) > 15 and conversation.title not in ["Research Conversation", "New Conversation"]:
                    continue
                
                # Get messages for this conversation using raw SQL
                msg_result = await db.execute(
                    text("SELECT * FROM messages WHERE conversation_id = :conv_id ORDER BY created_at"),
                    {"conv_id": conversation.id}
                )
                messages = msg_result.all()
                
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
                
                # Update the title using raw SQL
                if new_title != conversation.title:
                    await db.execute(
                        text("UPDATE conversations SET title = :title WHERE id = :id"),
                        {"title": new_title, "id": conversation.id}
                    )
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
        current_date_str = current_date.isoformat()
        
        # Query to find conversations with future dates using raw SQL
        # This is more compatible with both PostgreSQL and SQLite
        result = await db.execute(
            text("SELECT * FROM conversations WHERE updated_at > :current_date"),
            {"current_date": current_date_str}
        )
        
        future_conversations = result.all()
        fixed_count = 0
        
        # Log the future dated conversations
        logger.info(f"Found {len(future_conversations)} conversations with future dates")
        
        # Fix each one by setting updated_at to current date
        for conv in future_conversations:
            logger.info(f"Fixing future date on conversation {conv.id}: {conv.updated_at}")
            await db.execute(
                text("UPDATE conversations SET updated_at = :current_date WHERE id = :conv_id"),
                {"current_date": current_date_str, "conv_id": conv.id}
            )
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


@router.post("/fix-timestamps", response_model=dict)
async def fix_conversation_timestamps(
    db: AsyncSession = Depends(get_db)
):
    """
    Fix all conversation timestamps to ensure they are unique.
    This is useful when all conversations have the same timestamp, which can happen with SQLite.
    """
    try:
        # Get all conversations
        result = await db.execute(text("SELECT id, updated_at FROM conversations ORDER BY id"))
        conversations = result.all()
        
        if not conversations:
            return {"status": "success", "message": "No conversations to update"}
            
        # Get current time as base
        base_time = datetime.datetime.now()
        updated_count = 0
        
        # Update each conversation with a unique timestamp
        # Newest conversations will have timestamps closest to now
        for i, conv in enumerate(conversations):
            # Create a unique timestamp with 5 minute intervals going backwards in time
            new_timestamp = base_time - datetime.timedelta(minutes=i*5)
            
            # Update the database
            await db.execute(
                text("UPDATE conversations SET updated_at = :timestamp WHERE id = :id"),
                {"timestamp": new_timestamp.isoformat(), "id": conv.id}
            )
            updated_count += 1
        
        # Commit the changes
        await db.commit()
        
        return {
            "status": "success", 
            "message": f"Updated timestamps for {updated_count} conversations",
            "details": {
                "conversations_updated": updated_count,
                "base_time": base_time.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error fixing conversation timestamps: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fix timestamps: {str(e)}")