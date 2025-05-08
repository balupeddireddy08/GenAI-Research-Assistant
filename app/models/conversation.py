from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from app.database import Base


class Conversation(Base):
    """Conversation model representing a chat session."""
    
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(String, nullable=True)  # Can be null for anonymous users
    
    # Relationship: one conversation has many messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # Vector embedding of the conversation for semantic search
    embedding = Column(Text, nullable=True)
    
    # Conversation metadata
    metadata = Column(JSONB, nullable=True)


class Message(Base):
    """Message model representing individual messages in a conversation."""
    
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Message metadata (e.g., thinking process, sources, etc.)
    metadata = Column(JSONB, nullable=True)
    
    # Relationship: many messages belong to one conversation
    conversation = relationship("Conversation", back_populates="messages")