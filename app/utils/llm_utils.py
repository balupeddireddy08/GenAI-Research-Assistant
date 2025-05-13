"""
LLM utility functions for the GenAI Research Assistant.
This file provides utilities for working with Language Learning Models
(OpenAI, Google Gemini, and Meta Llama), handling client initialization, completions, and embeddings.
"""
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

from app.config import settings
from app.utils.gemini_utils import get_gemini_client, get_gemini_completion
from app.utils.llama_utils import get_llama_client, get_llama_completion, get_llama_streaming_completion, close_llama_client

# Set up logging
logger = logging.getLogger(__name__)

def get_llm_client(settings, use_secondary=False):
    """
    Initialize and return the appropriate LLM client based on settings.
    
    Args:
        settings: Application settings
        use_secondary: Whether to use the secondary model instead of primary
        
    Returns:
        Tuple of (LLM client, provider type)
    """
    # Determine which model provider to use
    model_name = settings.SECONDARY_LLM if use_secondary else settings.PRIMARY_LLM
    
    # Add detailed logging for debugging model selection
    logger.info(f"Checking model: '{model_name}'")
    logger.info(f"Available LLAMA_MODELS: {settings.LLAMA_MODELS}")
    
    # Check exact model type and string representation for debugging
    logger.info(f"Model name type: {type(model_name)}, repr: {repr(model_name)}")
    
    # Case-insensitive check for Llama models
    if any(model_name.lower() == llama_model.lower() for llama_model in settings.LLAMA_MODELS):
        logger.info(f"Match found (case-insensitive): '{model_name}' is in LLAMA_MODELS")
        if not settings.META_API_KEY:
            raise ValueError("Meta API key is required for Llama models")
        logger.info(f"Initializing Meta Llama client for model: {model_name}")
        return get_llama_client(settings.META_API_KEY), "llama"
    elif model_name in settings.LLAMA_MODELS:
        logger.info(f"Match found (exact): '{model_name}' is in LLAMA_MODELS")
        if not settings.META_API_KEY:
            raise ValueError("Meta API key is required for Llama models")
        logger.info(f"Initializing Meta Llama client for model: {model_name}")
        return get_llama_client(settings.META_API_KEY), "llama"
    else:
        logger.info(f"No match: '{model_name}' not found in LLAMA_MODELS")
    
    # Case-insensitive check for OpenAI models
    if any(model_name.lower() == openai_model.lower() for openai_model in settings.OPENAI_MODELS):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for OpenAI models")
        logger.info(f"Initializing OpenAI client for model: {model_name}")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), "openai"
    elif model_name in settings.OPENAI_MODELS:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for OpenAI models")
        logger.info(f"Initializing OpenAI client for model: {model_name}")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), "openai"
    
    # Case-insensitive check for Google models
    if any(model_name.lower() == google_model.lower() for google_model in settings.GOOGLE_MODELS):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("Google API key is required for Gemini models")
        logger.info(f"Initializing Google Gemini client for model: {model_name}")
        return get_gemini_client(settings.GOOGLE_API_KEY), "gemini"
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
    response_format: Optional[Dict[str, str]] = None,
    use_secondary: bool = False
) -> str:
    """
    Get a completion from the LLM client.
    
    Args:
        llm_client: Tuple of (initialized LLM client, provider type)
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        response_format: Optional format specification for the response
        use_secondary: Whether to use the secondary model
        
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
    model_name = settings.SECONDARY_LLM if use_secondary else settings.PRIMARY_LLM
    completion_params = {
        "model": model_name,
        "messages": formatted_messages,
        "temperature": temperature,
    }
    
    # Add optional parameters if provided
    if max_tokens:
        completion_params["max_tokens"] = max_tokens
    
    if response_format:
        completion_params["response_format"] = response_format
    
    # Log the request parameters (excluding actual message content for privacy)
    logger.info(f"Sending request to {provider} with model: {model_name}")
    
    try:
        # Use appropriate client based on provider
        if provider == "gemini":
            return await get_gemini_completion(client, model_name, formatted_messages, temperature)
        elif provider == "llama":
            result = await get_llama_completion(
                client, 
                model_name, 
                formatted_messages, 
                temperature,
                max_tokens=max_tokens
            )
            return result
        
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
            return f"Error: Model '{model_name}' not found. Please check available models."
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


async def get_streaming_completion(
    llm_client: Tuple[Any, str],
    messages: List[Dict[str, str]],
    callback,
    temperature: float = 0.7,
    max_tokens: Optional[int] = 256,
    use_secondary: bool = False
) -> str:
    """
    Get a streaming completion from the LLM with token-by-token callback.
    
    Args:
        llm_client: Tuple of (initialized LLM client, provider type)
        messages: List of message dictionaries with 'role' and 'content'
        callback: Function that receives each token as it's generated
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        use_secondary: Whether to use the secondary model
        
    Returns:
        The complete generated text response
    """
    # Unpack client and provider type from tuple
    client, provider = llm_client
    
    # Format messages for API
    formatted_messages = []
    
    for msg in messages:
        if msg["role"] in ["user", "assistant", "system"]:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Set up completion parameters using configured model
    model_name = settings.SECONDARY_LLM if use_secondary else settings.PRIMARY_LLM
    
    # Log the request parameters
    logger.info(f"Sending streaming request to {provider} with model: {model_name}")
    
    try:
        # Use appropriate client based on provider
        if provider == "llama":
            result = await get_llama_streaming_completion(
                client, 
                model_name, 
                formatted_messages, 
                temperature,
                max_tokens,
                callback
            )
            return result
        else:
            # For providers that don't have explicit streaming support yet
            # Fall back to non-streaming completion
            logger.warning(f"Streaming not fully implemented for {provider}, using standard completion")
            result = await get_completion(
                llm_client,
                messages,
                temperature,
                max_tokens,
                None,
                use_secondary
            )
            # Simulate streaming with the full result
            if callback:
                callback(result)
            return result
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in streaming completion for {provider}: {error_msg}")
        error_response = f"Error in streaming completion: {error_msg}"
        if callback:
            callback(error_response)
        return error_response


# Add a new function to cleanup clients
async def cleanup_llm_client(llm_client: Tuple[Any, str]):
    """
    Clean up LLM client resources when done.
    
    Args:
        llm_client: Tuple of (initialized LLM client, provider type)
    """
    if not llm_client:
        return
        
    client, provider = llm_client
    
    try:
        # Handle different provider cleanup
        if provider == "llama":
            await close_llama_client(client)
    except Exception as e:
        logger.error(f"Error cleaning up {provider} client: {str(e)}")
