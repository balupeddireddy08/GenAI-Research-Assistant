"""
User database model for the GenAI Research Assistant.
This file defines the SQLAlchemy ORM model for user accounts, including
authentication information, profile data, and user preferences.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import uuid
import os

from app.database import Base


class User(Base):
    """User model for authentication and personalization."""
    
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    
    # User profile
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # User preferences and settings - use JSON for SQLite compatibility
    # Use JSONB for PostgreSQL but fall back to JSON for SQLite
    preferences = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict
    )