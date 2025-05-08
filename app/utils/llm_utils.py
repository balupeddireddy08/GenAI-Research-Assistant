"""
LLM utility functions for the GenAI Research Assistant.
This file provides a unified interface for interacting with various LLM providers
(OpenAI, Anthropic, Google), handling client initialization, completions, and embeddings.
"""
from typing import Any, Dict, List, Optional, Union
import openai
import anthropic
import google.generativeai as genai
from app.config import settings


def get_llm_client(settings: Any) -> Any:
    """
    Initialize and return the appropriate LLM client based on settings.
    
    Args:
        settings: Application settings containing API keys and configuration
        
    Returns:
        The initialized LLM client
    """
    primary_llm = settings.PRIMARY_LLM.lower()
    
    if primary_llm.startswith("gpt"):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for GPT models")
        openai.api_key = settings.OPENAI_API_KEY
        return openai
        
    elif primary_llm.startswith("claude"):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("Anthropic API key is required for Claude models")
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
    elif primary_llm.startswith("gemini"):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("Google API key is required for Gemini models")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        return genai
        
    else:
        raise ValueError(f"Unsupported LLM model: {primary_llm}")


async def get_completion(
    llm_client: Any,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    """
    Get a completion from the LLM client.
    
    Args:
        llm_client: The initialized LLM client
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        response_format: Optional format specification for the response
        
    Returns:
        The generated text response
    """
    # Determine which client we're using
    if isinstance(llm_client, openai.OpenAI) or llm_client == openai:
        # OpenAI client
        response = await llm_client.chat.completions.create(
            model=settings.PRIMARY_LLM,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
        return response.choices[0].message.content
        
    elif isinstance(llm_client, anthropic.Anthropic):
        # Anthropic client
        # Convert messages to Anthropic format
        prompt = "\n\n".join([
            f"{'Human' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in messages
        ])
        
        response = await llm_client.messages.create(
            model=settings.PRIMARY_LLM,
            max_tokens=max_tokens or 1000,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
        
    elif llm_client == genai:
        # Google Gemini client
        model = genai.GenerativeModel(settings.PRIMARY_LLM)
        
        # Convert messages to Gemini format
        chat = model.start_chat(history=[])
        for msg in messages:
            if msg["role"] == "user":
                chat.send_message(msg["content"])
            else:
                # Store assistant messages in history
                chat.history.append({
                    "role": "model",
                    "parts": [msg["content"]]
                })
        
        response = await chat.send_message_async(
            messages[-1]["content"],
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        return response.text
        
    else:
        raise ValueError("Unsupported LLM client type")


def get_embedding(text: str) -> List[float]:
    """
    Get embeddings for the given text using the configured embedding model.
    
    Args:
        text: The text to generate embeddings for
        
    Returns:
        List of embedding values
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API key is required for embeddings")
    
    response = openai.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding
