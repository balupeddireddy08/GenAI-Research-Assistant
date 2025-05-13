"""
Intent Analysis Agent for the GenAI Research Assistant.
This file implements a specialized agent responsible for analyzing user intent
and determining the appropriate approach for handling different types of queries.
"""
from typing import Dict, Any, List, Optional
import json
import logging
import re

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

class IntentAnalysisAgent:
    """
    Agent responsible for analyzing user intent and classifying queries.
    This agent detects whether a query is conversational, identity-related,
    research-oriented, or requires other specialized handling.
    """
    
    def __init__(self, settings):
        self.settings = settings
        # Use secondary model for intent analysis as it's a simpler, classification task
        self.llm_client = get_llm_client(settings, use_secondary=True)
    
    async def analyze_intent(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze the user's intent from their message using LLM.
        
        Args:
            user_message: The user's message content
            conversation_history: Optional list of previous messages for context
            
        Returns:
            Dict containing intent analysis results
        """
        logger.info("Analyzing user intent...")
        
        # Ensure conversation_history is not None
        if conversation_history is None:
            conversation_history = []
            
        # First do a quick check for obvious conversational patterns
        # This is a safety net in case the LLM fails
        quick_check = self._quick_conversational_check(user_message)
        if quick_check:
            logger.info(f"Quick check detected conversational message: {user_message}")
            return quick_check
        
        # Use LLM for all intent analysis, including conversational queries
        return await self._perform_intent_analysis(user_message, conversation_history)
    
    def _quick_conversational_check(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        A lightweight check for obvious conversational patterns.
        This serves as a fallback in case the LLM analysis fails.
        """
        message = user_message.lower().strip().rstrip('?').strip()
        
        # Skip this check for educational explanation queries
        if message.startswith("explain") or "explain this concept" in message:
            return None
        
        # Very basic greetings that are definitely conversational
        basic_greetings = ['hi', 'hello', 'hey', 'greetings', 'howdy', 'hiya', 'whats up', "what's up"]
        
        for greeting in basic_greetings:
            if message == greeting or message.startswith(f"{greeting} "):
                return {
                    "primary_intent": "greeting",
                    "entities": [],
                    "info_type": "conversation",
                    "is_conversational": True,
                    "conversation_type": "greeting",
                    "requires_search": False,
                    "requires_planning": False,
                    "handler": "conversation_handler"
                }
        
        # Short conversational phrases
        if len(message.split()) <= 4 and any(x in message for x in ["how are you", "whats up", "what's up"]):
            return {
                "primary_intent": "greeting",
                "entities": [],
                "info_type": "conversation",
                "is_conversational": True,
                "conversation_type": "greeting",
                "requires_search": False,
                "requires_planning": False,
                "handler": "conversation_handler"
            }
            
        return None
    
    async def _perform_intent_analysis(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Perform a comprehensive analysis of user intent using LLM.
        This handles all types of queries including conversational, identity, and research.
        """
        logger.info("Performing intent analysis with secondary LLM...")
        
        # Pre-check for educational explanation queries 
        explanation_patterns = [
            r"explain\s+(?:to me\s+)?(?:the concept of\s+)?([a-zA-Z0-9\s]+)(?:\s+in simple terms)?",
            r"explain\s+(?:this|the)\s+concept(?:\s+in simple terms)?[:]\s*([a-zA-Z0-9\s]+)",
            r"what\s+is\s+([a-zA-Z0-9\s]+)(?:\s+in simple terms)?",
            r"how\s+does\s+([a-zA-Z0-9\s]+)(?:\s+work)?",
        ]
        
        # Check if the message matches an explanation pattern
        for pattern in explanation_patterns:
            match = re.search(pattern, user_message.lower())
            if match:
                concept = match.group(1).strip()
                if concept and len(concept) > 1:  # Ensure we have a valid concept
                    logger.info(f"Detected educational explanation query for concept: {concept}")
                    return {
                        "primary_intent": "explanation",
                        "entities": [concept],
                        "query_type": "educational",
                        "is_conversational": False,
                        "requires_search": True,
                        "requires_planning": True,
                        "complexity": "moderate",
                        "handler": "research_handler",
                        "concept_to_explain": concept
                    }
        
        # Create a comprehensive prompt for the LLM
        prompt = """
        You are an intent analysis agent for a GenAI Research Assistant. Your task is to analyze the user's message and determine their intent.
        
        Consider these possible intents:
        1. CONVERSATIONAL: Simple greetings ("hi", "hello"), chitchat, or casual questions about the assistant's day
        2. IDENTITY: Questions about the assistant's name, nature, capabilities, or how it works
        3. CAPABILITIES: Questions about what the assistant can do or how to use it
        4. CLARIFICATION: Requests for clarification about previous responses
        5. RESEARCH: Questions requiring academic research, paper analysis, or scholarly information
        6. FACTUAL: Questions requiring factual information that could be found through web search
        7. EXPLANATION: Requests to explain a concept, term, or topic (e.g., "Explain GPT")
        
        Analyze the user message considering these factors:
        - Is this a simple greeting or casual conversation?
        - Is the user asking about the assistant itself?
        - Does the message require searching for information?
        - Is this continuing a previous conversation thread?
        - Does this require complex research or a simple response?
        - Is the user asking for an explanation of a specific concept?
        
        IMPORTANT: For simple conversational queries like greetings, identity questions, or casual conversation,
        classify them appropriately without defaulting to research or search.
        
        IMPORTANT: Be careful with phrases like "what's up", "how are you", etc. These are typically greetings and should be
        classified as conversational, not requiring research or search.
        
        IMPORTANT: When the user asks to "explain" a concept or "what is X", this should be classified as an EXPLANATION intent
        that requires research, not as a conversational query. These should be routed to the research_handler.
        
        Return a detailed JSON with these fields:
        - primary_intent: The main intent category
        - is_conversational: true/false - Is this casual conversation or requires more?
        - requires_search: true/false - Does this need web search?
        - requires_planning: true/false - Does this need complex orchestration?
        - handler: The appropriate handler ("conversation_handler", "identity_handler", "research_handler")
        - Any other relevant fields for understanding the query
        
        Always respond in valid JSON format.
        """
        
        # Include recent conversation history for context
        recent_history = conversation_history[-5:] if len(conversation_history) > 0 else []
        
        # Get the analysis from the secondary LLM
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                *recent_history,
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"} if self.settings.SECONDARY_LLM in self.settings.OPENAI_MODELS else None,
            use_secondary=True
        )
        
        try:
            # Try to extract JSON if it's wrapped in markdown code blocks
            if "```json" in result:
                json_content = re.search(r"```json\s*([\s\S]*?)\s*```", result)
                if json_content:
                    result = json_content.group(1).strip()
            elif "```" in result:
                json_content = re.search(r"```\s*([\s\S]*?)\s*```", result)
                if json_content:
                    result = json_content.group(1).strip()
            
            # Parse the JSON result
            intent_data = json.loads(result)
            
            # Ensure required fields are present
            if "primary_intent" not in intent_data:
                intent_data["primary_intent"] = "unknown"
                
            if "is_conversational" not in intent_data:
                # Determine based on primary intent
                conversational_intents = ["greeting", "chitchat", "conversational", "personal"]
                intent_data["is_conversational"] = intent_data["primary_intent"].lower() in conversational_intents
                
            if "requires_search" not in intent_data:
                # Default based on conversational status
                intent_data["requires_search"] = not intent_data["is_conversational"]
                
            if "requires_planning" not in intent_data:
                # Default based on whether search is required
                intent_data["requires_planning"] = intent_data["requires_search"]
                
            if "handler" not in intent_data:
                # Determine handler
                if intent_data["is_conversational"]:
                    intent_data["handler"] = "conversation_handler"
                elif intent_data["primary_intent"].lower() in ["identity", "capabilities"]:
                    intent_data["handler"] = "identity_handler"
                else:
                    intent_data["handler"] = "research_handler"
            
            logger.info(f"Intent analysis complete. Primary intent: {intent_data['primary_intent']}, Handler: {intent_data['handler']}")
            return intent_data
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing intent analysis JSON: {str(e)}. Raw result: {result}")
            
            # Return a fallback intent analysis
            return {
                "primary_intent": "research",
                "is_conversational": False,
                "requires_search": True,
                "requires_planning": True,
                "handler": "research_handler",
                "error": f"Failed to parse intent: {str(e)}"
            } 