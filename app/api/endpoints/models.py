"""
API endpoints for model selection in the GenAI Research Assistant.
This file defines routes for retrieving available models and setting model preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import settings
from app.database import get_async_session
from app.schemas.model_selection import (
    ModelInfo, 
    ModelSelectionRequest, 
    ModelSelectionResponse,
    AvailableModelsResponse
)

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/available", response_model=AvailableModelsResponse)
async def get_available_models():
    """
    Get list of available models from all providers.
    """
    try:
        # Construct model info for OpenAI models
        openai_models = [
            ModelInfo(
                name=model,
                provider="OpenAI",
                description=get_model_description("openai", model)
            )
            for model in settings.OPENAI_MODELS
        ]
        
        # Construct model info for Google models
        google_models = [
            ModelInfo(
                name=model,
                provider="Google",
                description=get_model_description("google", model)
            )
            for model in settings.GOOGLE_MODELS
        ]
        
        # Construct model info for Llama models
        llama_models = [
            ModelInfo(
                name=model,
                provider="Meta",
                description=get_model_description("meta", model)
            )
            for model in settings.LLAMA_MODELS
        ]
        
        return AvailableModelsResponse(
            openai_models=openai_models,
            google_models=google_models,
            llama_models=llama_models
        )
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting available models: {str(e)}"
        )


@router.post("/select", response_model=ModelSelectionResponse)
async def select_models(
    request: ModelSelectionRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Select primary and secondary models for the assistant.
    """
    try:
        # Log the incoming model selection request
        logger.info(f"Model selection request - Primary: '{request.primary_model}', Secondary: '{request.secondary_model}'")
        
        # Convert lists to lowercase for case-insensitive comparison
        openai_models_lower = [m.lower() for m in settings.OPENAI_MODELS]
        google_models_lower = [m.lower() for m in settings.GOOGLE_MODELS]
        llama_models_lower = [m.lower() for m in settings.LLAMA_MODELS]
        
        # Detailed validation logging
        primary_model_lower = request.primary_model.lower()
        logger.info(f"Checking primary model '{request.primary_model}' (lower: '{primary_model_lower}'):")
        logger.info(f"In OpenAI models: {primary_model_lower in openai_models_lower}")
        logger.info(f"In Google models: {primary_model_lower in google_models_lower}")
        logger.info(f"In Llama models: {primary_model_lower in llama_models_lower}")
        
        # Validate primary model (case-insensitive)
        if (
            primary_model_lower not in openai_models_lower and
            primary_model_lower not in google_models_lower and
            primary_model_lower not in llama_models_lower
        ):
            raise ValueError(f"Invalid primary model: {request.primary_model}")
        
        # Validate secondary model (case-insensitive)
        secondary_model_lower = request.secondary_model.lower()
        logger.info(f"Checking secondary model '{request.secondary_model}' (lower: '{secondary_model_lower}'):")
        logger.info(f"In OpenAI models: {secondary_model_lower in openai_models_lower}")
        logger.info(f"In Google models: {secondary_model_lower in google_models_lower}")
        logger.info(f"In Llama models: {secondary_model_lower in llama_models_lower}")
        
        if (
            secondary_model_lower not in openai_models_lower and
            secondary_model_lower not in google_models_lower and
            secondary_model_lower not in llama_models_lower
        ):
            raise ValueError(f"Invalid secondary model: {request.secondary_model}")
        
        # Update application settings
        # Note: This will update the settings for the current session only
        # In a production app, you would save this to a database or config file
        settings.PRIMARY_LLM = request.primary_model
        settings.SECONDARY_LLM = request.secondary_model
        
        logger.info(f"Models selected - Primary: '{settings.PRIMARY_LLM}', Secondary: '{settings.SECONDARY_LLM}'")
        
        # Return success response
        return ModelSelectionResponse(
            primary_model=request.primary_model,
            secondary_model=request.secondary_model,
            success=True,
            message="Models selected successfully"
        )
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error selecting models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting models: {str(e)}"
        )


def get_model_description(provider: str, model_name: str) -> str:
    """
    Get a descriptive text for a given model.
    
    Args:
        provider: The model provider (openai, google, meta)
        model_name: The name of the model
        
    Returns:
        A descriptive string for the model
    """
    descriptions = {
        "openai": {
            "gpt-3.5-turbo": "Fast and cost-effective model for general tasks",
            "gpt-3.5-turbo-16k": "Extended context model for longer conversations",
            "gpt-4": "Advanced reasoning and instruction following capabilities",
            "gpt-4o": "Latest multimodal model with strong capabilities",
            "gpt-4-32k": "Extended context model with advanced reasoning",
        },
        "google": {
            "gemini-pro": "Balanced model for various tasks",
            "gemini-1.5-pro": "Advanced model with long context support",
            "gemini-1.5-flash": "Fast, cost-effective model for routine tasks",
            "gemini-2.0-flash": "Latest fast model with improved capabilities",
            "gemini-2.0-flash-lite": "Efficient model for simple agent steps",
        },
        "meta": {
            "llama-3-8b-instant": "Fast response model for routine tasks (8B parameters)",
            "llama-3-70b-instant": "Fast response model with strong capabilities (70B parameters)",
            "llama-3-8b": "Balanced model for various tasks (8B parameters)",
            "llama-3-70b": "Advanced model for complex reasoning (70B parameters)",
        }
    }
    
    # Return the description if found, otherwise a generic description
    return descriptions.get(provider, {}).get(
        model_name, 
        f"{model_name} from {provider}"
    ) 