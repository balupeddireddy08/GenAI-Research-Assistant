"""
Model selection schemas for the GenAI Research Assistant.
This file defines the request and response schemas for model selection API endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ModelInfo(BaseModel):
    """Model information."""
    name: str = Field(..., description="Name of the model")
    provider: str = Field(..., description="Provider of the model (OpenAI, Google, Meta)")
    description: str = Field(..., description="Brief description of the model")


class ModelSelectionRequest(BaseModel):
    """Model selection request."""
    primary_model: str = Field(..., description="Primary model for planning and complex tasks")
    secondary_model: str = Field(..., description="Secondary model for simpler agent steps")


class ModelSelectionResponse(BaseModel):
    """Model selection response."""
    primary_model: str = Field(..., description="Primary model selected")
    secondary_model: str = Field(..., description="Secondary model selected")
    success: bool = Field(..., description="Whether the selection was successful")
    message: str = Field(..., description="Status message")


class AvailableModelsResponse(BaseModel):
    """Available models response."""
    openai_models: List[ModelInfo] = Field(..., description="Available OpenAI models")
    google_models: List[ModelInfo] = Field(..., description="Available Google models")
    llama_models: List[ModelInfo] = Field(..., description="Available Meta Llama models") 