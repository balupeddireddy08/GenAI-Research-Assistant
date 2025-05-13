"""
Meta Llama utility functions for the GenAI Research Assistant.
This file provides utilities for working with Meta's Llama models,
handling client initialization and completions.
"""
import aiohttp
from typing import List, Dict, Any, Optional
import json
import logging
import asyncio

from app.config import settings

# Set up logging
logger = logging.getLogger(__name__)

def get_llama_client(api_key: str):
    """
    Initialize and return the Meta Llama client.
    
    Args:
        api_key: Meta API key for Llama access
        
    Returns:
        Initialized Llama client session
    """
    if not api_key:
        raise ValueError("Meta API key is required for Llama")
    
    logger.info("Initializing Meta Llama client")
    # For Llama, we'll use aiohttp session with API key in headers
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    return session


async def close_llama_client(client: aiohttp.ClientSession):
    """
    Properly close the Llama client session.
    
    Args:
        client: The aiohttp client session to close
    """
    if client and not client.closed:
        await client.close()
        logger.info("Closed Meta Llama client session")


async def get_llama_completion(
    client: aiohttp.ClientSession,
    model_name: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = 256,
    stream: bool = False
) -> str:
    """
    Get a completion from the Llama model.
    
    Args:
        client: The initialized aiohttp client session
        model_name: The name of the Llama model to use
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate (default: 256)
        stream: Whether to stream the response (default: False)
        
    Returns:
        The generated text response
    """
    try:
        # Format messages for Llama API
        formatted_messages = []
        system_content = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] in ["user", "assistant"]:
                formatted_messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"]
                })
        
        # Prepare the request payload
        payload = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # Add system message if present
        if system_content:
            payload["messages"].insert(0, {
                "role": "system",
                "content": system_content
            })
        
        # Send request to Llama API endpoint
        async with client.post(
            "https://api.llama.com/v1/chat/completions",
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Error from Llama API: {error_text}")
                return f"Error calling Llama API: {response.status} - {error_text}"
            
            # Handle streaming response if enabled
            if stream:
                full_response = ""
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Skip 'data: ' prefix
                            if "event" in data and data["event"]["event_type"] == "progress":
                                token = data["event"]["delta"]["text"]
                                full_response += token
                        except json.JSONDecodeError:
                            continue
                return full_response
            else:
                # Handle regular response
                result = await response.json()
                try:
                    # Try new format first
                    if "completion_message" in result:
                        return result["completion_message"]["content"]["text"]
                    # Fall back to old format
                    elif "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    else:
                        logger.error(f"Unexpected response format: {result}")
                        return "Error: Unexpected response format from Llama API"
                except KeyError as e:
                    logger.error(f"Error parsing Llama API response: {e}")
                    return f"Error parsing Llama API response: {e}"
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error calling Llama API: {error_msg}")
        
        # Return a more user-friendly error message
        if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return "Error: Invalid Meta API key. Please check your credentials."
        elif "model not found" in error_msg.lower():
            return f"Error: Model '{model_name}' not found. Please check available Llama models."
        elif "rate limit" in error_msg.lower():
            return "Error: Rate limit exceeded for Meta Llama API. Please try again later."
        else:
            return f"Error calling Llama API: {error_msg}"


async def get_llama_streaming_completion(
    client: aiohttp.ClientSession,
    model_name: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 256,
    callback = None
) -> str:
    """
    Get a streaming completion from the Llama model with callback support.
    
    Args:
        client: The initialized aiohttp client session
        model_name: The name of the Llama model to use
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        callback: Optional callback function that receives each token
        
    Returns:
        The complete generated text response
    """
    try:
        # Format messages for Llama API
        formatted_messages = []
        system_content = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] in ["user", "assistant"]:
                formatted_messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"]
                })
        
        # Prepare the request payload
        payload = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        # Add system message if present
        if system_content:
            payload["messages"].insert(0, {
                "role": "system",
                "content": system_content
            })
            
        # Set additional headers for streaming
        headers = {
            "Accept": "text/event-stream"
        }
        
        # Send request to Llama API endpoint
        async with client.post(
            "https://api.llama.com/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Error from Llama API streaming: {error_text}")
                return f"Error calling Llama API streaming: {response.status} - {error_text}"
            
            full_response = ""
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # Skip 'data: ' prefix
                        if "event" in data:
                            if data["event"]["event_type"] == "progress":
                                token = data["event"]["delta"]["text"]
                                full_response += token
                                if callback:
                                    callback(token)
                            elif data["event"]["event_type"] == "complete":
                                break
                    except json.JSONDecodeError:
                        continue
            
            return full_response
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in Llama streaming: {error_msg}")
        
        # Return a more user-friendly error message
        if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return "Error: Invalid Meta API key. Please check your credentials."
        elif "model not found" in error_msg.lower():
            return f"Error: Model '{model_name}' not found. Please check available Llama models."
        elif "rate limit" in error_msg.lower():
            return "Error: Rate limit exceeded for Meta Llama API. Please try again later."
        else:
            return f"Error in Llama streaming: {error_msg}" 