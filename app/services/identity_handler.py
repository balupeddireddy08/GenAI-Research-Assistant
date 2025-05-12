"""
Identity Handler for the GenAI Research Assistant.
This file implements a specialized handler for responding to questions about
the assistant's identity, name, nature, and other self-referential inquiries.
"""
from typing import Dict, Any, List
import logging

from app.config import settings

# Set up logging
logger = logging.getLogger(__name__)

class IdentityHandler:
    """
    Handler for responding to questions about the assistant's identity.
    Provides consistent responses about the assistant's name, nature, capabilities,
    without performing unnecessary searches.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.assistant_name = getattr(settings, "ASSISTANT_NAME", "Research Assistant")
        self.model_info = getattr(settings, "PRIMARY_LLM", "Large Language Model")
    
    async def handle_identity_question(
        self, 
        user_message: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle identity-related questions without performing searches.
        
        Args:
            user_message: The user's message
            intent_analysis: Intent analysis results from the intent analysis agent
            
        Returns:
            Dict containing the response and metadata
        """
        logger.info(f"Handling identity question: {intent_analysis.get('question_type', 'unknown')}")
        
        question_type = intent_analysis.get("question_type", "general")
        
        if question_type == "name":
            return self._handle_name_question()
        elif question_type == "nature":
            return self._handle_nature_question()
        else:
            return self._handle_general_identity_question()
    
    def _handle_name_question(self) -> Dict[str, Any]:
        """Handle questions about the assistant's name."""
        response = f"I'm {self.assistant_name}, a GenAI Research Assistant designed to help with academic research, literature exploration, and knowledge discovery. How can I assist with your research today?"
        
        return {
            "response": response,
            "metadata": {
                "response_type": "identity",
                "question_type": "name",
                "assistant_name": self.assistant_name
            }
        }
    
    def _handle_nature_question(self) -> Dict[str, Any]:
        """Handle questions about the assistant's nature or how it works."""
        response = f"""I'm a specialized GenAI Research Assistant built on a large language model ({self.model_info}). 

I've been designed to help with academic research by finding and analyzing academic papers, explaining scientific concepts, comparing research methodologies, and synthesizing information from multiple sources.

Unlike a simple chatbot, I'm specifically optimized for research-oriented tasks and can help you explore scholarly literature, understand complex academic topics, and discover relevant research in your field of interest."""
        
        return {
            "response": response,
            "metadata": {
                "response_type": "identity",
                "question_type": "nature",
                "model_info": self.model_info
            }
        }
    
    def _handle_general_identity_question(self) -> Dict[str, Any]:
        """Handle general questions about the assistant's identity."""
        response = f"""I'm {self.assistant_name}, a specialized GenAI Research Assistant built to help with academic and research-oriented tasks.

I can assist with finding relevant academic papers, explaining scientific concepts, comparing research methodologies, and synthesizing information from multiple sources.

My primary goal is to make research easier and more efficient by helping you navigate the scholarly landscape and find the information you need."""
        
        return {
            "response": response,
            "metadata": {
                "response_type": "identity",
                "question_type": "general",
                "assistant_name": self.assistant_name
            }
        } 