"""
Configuration settings for the GenAI Research Assistant application.
This file defines environment-based settings including database connections,
API keys for LLM services, and application parameters using Pydantic.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    APP_NAME: str = "GenAI Research Assistant"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:password@localhost:5432/research_assistant"
    )
    
    # LLM settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    
    # LLM configuration
    PRIMARY_LLM: str = os.getenv("PRIMARY_LLM", "gpt-4")  # Options: gpt-4, claude-3-opus, gemini-1.5-pro
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # External services
    ARXIV_API_URL: str = "http://export.arxiv.org/api/query"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Initialize settings
settings = Settings()