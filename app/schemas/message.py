"""
Pydantic schemas for message-related data structures.
This file defines data validation models for message creation, retrieval,
and responses used throughout the chat API.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime


class MessageBase(BaseModel):
    """Base message schema."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str = Field(..., description="Message ID")
    conversation_id: str = Field(..., description="Conversation ID")
    created_at: Union[datetime, str] = Field(..., description="Creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")

    class Config:
        orm_mode = True