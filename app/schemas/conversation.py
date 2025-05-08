from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.schemas.message import MessageResponse


class ConversationBase(BaseModel):
    """Base conversation schema."""
    title: str = Field(..., description="Conversation title")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    user_id: Optional[str] = Field(None, description="User ID (optional)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional conversation metadata")


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(None, description="Conversation title")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional conversation metadata")


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    id: str = Field(..., description="Conversation ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    user_id: Optional[str] = Field(None, description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional conversation metadata")

    class Config:
        orm_mode = True


class ConversationDetail(ConversationResponse):
    """Schema for detailed conversation with messages."""
    messages: List[MessageResponse] = Field(default_factory=list, description="Conversation messages")

    class Config:
        orm_mode = True


class ChatRequest(BaseModel):
    """Schema for chat request."""
    conversation_id: Optional[str] = Field(None, description="Conversation ID (None for new conversation)")
    message: str = Field(..., description="User message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional request metadata")


class ChatResponse(BaseModel):
    """Schema for chat response."""
    conversation_id: str = Field(..., description="Conversation ID")
    message: MessageResponse = Field(..., description="Assistant response")
    recommendations: Optional[List[Dict[str, Any]]] = Field(None, description="Recommendations based on the conversation")