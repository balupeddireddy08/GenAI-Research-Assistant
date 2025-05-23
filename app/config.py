"""
Configuration settings for the GenAI Research Assistant application.
This file defines environment-based settings including database connections,
API keys for LLM services, and application parameters using Pydantic.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    APP_NAME: str = "GenAI Research Assistant"
    ASSISTANT_NAME: str = "Research Assistant"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:password@localhost:5432/research_assistant"
    )
    
    # LLM settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    META_API_KEY: Optional[str] = os.getenv("META_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    
    # LLM configuration
    PRIMARY_LLM: str = os.getenv("PRIMARY_LLM", "gemini-2.0-flash-lite")
    SECONDARY_LLM: str = os.getenv("SECONDARY_LLM", "gemini-2.0-flash-lite")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    CONTEXT_MESSAGE_LIMIT: int = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "10"))
    
    # Supported model lists for validation
    OPENAI_MODELS: List[str] = [
        "gpt-3.5-turbo", 
        "gpt-3.5-turbo-16k", 
        "gpt-4", 
        "gpt-4o",
        "gpt-4-32k"
    ]
    
    GOOGLE_MODELS: List[str] = [
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.5-flash-preview-04-17"
    ]
    
    LLAMA_MODELS: List[str] = [
        "llama-3-8b-instant",
        "llama-3-70b-instant", 
        "llama-3-8b",
        "llama-3-70b",
        "Llama-4-Scout-17B-16E-Instruct-FP8",
        "Llama-4-Maverick-17B-128E-Instruct-FP8",
        "Llama-3.3-70B-Instruct",
        "Llama-3.3-8B-Instruct"
    ]
    
    # External services
    ARXIV_API_URL: str = "http://export.arxiv.org/api/query"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in environment


# Initialize settings
settings = Settings()