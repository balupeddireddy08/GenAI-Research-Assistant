"""
LLM utility functions for the GenAI Research Assistant.
This file provides utilities for working with Language Learning Models
(OpenAI and Google Gemini), handling client initialization, completions, and embeddings.
"""
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

from app.config import settings
from app.utils.gemini_utils import get_gemini_client, get_gemini_completion

# Set up logging
logger = logging.getLogger(__name__)

def get_llm_client(settings):
    """
    Initialize and return the appropriate LLM client based on settings.
    """
    # Determine which model provider to use
    model_name = settings.PRIMARY_LLM
    
    if model_name in settings.OPENAI_MODELS:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for OpenAI models")
        logger.info(f"Initializing OpenAI client for model: {model_name}")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), "openai"
    
    elif model_name in settings.GOOGLE_MODELS:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("Google API key is required for Gemini models")
        logger.info(f"Initializing Google Gemini client for model: {model_name}")
        return get_gemini_client(settings.GOOGLE_API_KEY), "gemini"
    
    else:
        # Default to OpenAI if model not recognized
        logger.warning(f"Unrecognized model: {model_name}. Defaulting to OpenAI.")
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), "openai"


async def get_completion(
    llm_client: Tuple[Any, str],
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    """
    Get a completion from the LLM client.
    
    Args:
        llm_client: Tuple of (initialized LLM client, provider type)
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        response_format: Optional format specification for the response
        
    Returns:
        The generated text response
    """
    # Unpack client and provider type from tuple
    client, provider = llm_client
    
    # Format messages for OpenAI API
    formatted_messages = []
    
    for msg in messages:
        if msg["role"] in ["user", "assistant", "system"]:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Set up completion parameters using configured model
    completion_params = {
        "model": settings.PRIMARY_LLM,  # Use configured model name
        "messages": formatted_messages,
        "temperature": temperature,
    }
    
    # Add optional parameters if provided
    if max_tokens:
        completion_params["max_tokens"] = max_tokens
    
    if response_format:
        completion_params["response_format"] = response_format
    
    # Log the request parameters (excluding actual message content for privacy)
    logger.info(f"Sending request to {provider} with model: {settings.PRIMARY_LLM}")
    
    try:
        # Use Gemini client for Google models
        if provider == "gemini":
            return await get_gemini_completion(client, settings.PRIMARY_LLM, formatted_messages, temperature)
        
        # Otherwise use OpenAI client
        # Generate response
        response = await client.chat.completions.create(**completion_params)
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error calling {provider} API: {error_msg}")
        
        # Return a more user-friendly error message
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            return f"Error: Invalid {provider} API key. Please check your credentials."
        elif "model not found" in error_msg.lower():
            return f"Error: Model '{settings.PRIMARY_LLM}' not found. Please check available models."
        elif "rate limit" in error_msg.lower():
            return f"Error: Rate limit exceeded for {provider} API. Please try again later."
        elif "context_length_exceeded" in error_msg.lower():
            return "Error: The input is too long for the model to process. Please shorten your query."
        else:
            return f"Error calling {provider} API: {error_msg}"


async def get_embedding(text: str) -> List[float]:
    """
    Get embeddings for the given text using OpenAI's embedding model.
    
    Args:
        text: The text to generate embeddings for
        
    Returns:
        List of embedding values
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API key is required for embeddings")
    
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,  # Use configured embedding model
            input=text
        )
        
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        raise
