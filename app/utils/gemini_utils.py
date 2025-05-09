"""
Google Gemini utility functions for the GenAI Research Assistant.
This file provides utilities for working with Google's Gemini models,
handling client initialization and completions.
"""
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
import logging
import asyncio
from functools import partial

from app.config import settings

# Set up logging
logger = logging.getLogger(__name__)

def get_gemini_client(api_key: str):
    """
    Initialize and return the Google Gemini client.
    
    Args:
        api_key: Google API key for Gemini access
        
    Returns:
        Initialized Gemini client
    """
    if not api_key:
        raise ValueError("Google API key is required for Gemini")
    
    logger.info("Initializing Google Gemini client")
    genai.configure(api_key=api_key)
    return genai


async def get_gemini_completion(
    client: Any,
    model_name: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> str:
    """
    Get a completion from the Gemini model.
    
    Args:
        client: The initialized Gemini client
        model_name: The name of the Gemini model to use
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (0.0 to 1.0)
        
    Returns:
        The generated text response
    """
    # Format messages for Gemini API
    history = []
    system_prompt = ""
    
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        elif msg["role"] in ["user", "assistant"]:
            history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })
    
    try:
        # Get the model
        model = client.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": temperature},
            system_instruction=system_prompt if system_prompt else None
        )
        
        # If there are multiple messages in history, use chat
        if len(history) > 1:
            chat = model.start_chat(history=history[:-1])
            
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(chat.send_message, history[-1]["parts"][0]["text"])
            )
        elif len(history) == 1:
            # Single prompt
            prompt = history[0]["parts"][0]["text"]
            
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(model.generate_content, prompt)
            )
        else:
            # No user messages, just use system prompt if available
            prompt = system_prompt if system_prompt else "No input provided."
            
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(model.generate_content, prompt)
            )
        
        return response.text
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error calling Gemini API: {error_msg}")
        
        # Return a more user-friendly error message
        if "API key not valid" in error_msg:
            return "Error: Invalid Google API key. Please check your credentials."
        elif "model not found" in error_msg.lower():
            return f"Error: Model '{model_name}' not found. Please check available Gemini models."
        elif "rate limit" in error_msg.lower():
            return "Error: Rate limit exceeded for Google Gemini API. Please try again later."
        else:
            return f"Error calling Gemini API: {error_msg}" 