"""
Conversation Handler for the GenAI Research Assistant.
This file implements a specialized handler for conversational interactions
such as greetings, capability inquiries, and other non-research exchanges.
"""
from typing import Dict, Any, List
import json
import logging
import time

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

class ConversationHandler:
    """
    Handler for responding to conversational queries without performing searches.
    Provides appropriate responses to greetings, capability inquiries, and
    other non-research exchanges with users.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
        self.assistant_name = getattr(settings, "ASSISTANT_NAME", "Research Assistant")
        self.start_time = time.time()
    
    async def handle_conversation(
        self, 
        user_message: str, 
        intent_analysis: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Handle a conversational message.
        
        Args:
            user_message: The user's message
            intent_analysis: Intent analysis results
            conversation_history: Conversation history
            
        Returns:
            Dict containing response and metadata
        """
        # Ensure conversation_history is not None
        if conversation_history is None:
            conversation_history = []
        
        # Create a system message based on the conversation type
        conversation_type = intent_analysis.get("conversation_type", "")
        primary_intent = intent_analysis.get("primary_intent", "")
        
        if conversation_type == "greeting" or primary_intent == "greeting":
            system_prompt = """
            You are a helpful GenAI Research Assistant responding to a casual greeting.
            Respond warmly and briefly, mentioning that you're ready to help with research topics.
            Keep your response under 3 sentences and conversational in tone.
            """
        elif conversation_type == "capabilities" or primary_intent == "assistant_capabilities":
            system_prompt = """
            You are a GenAI Research Assistant explaining your capabilities.
            Describe how you can help with academic research, finding papers, summarizing information,
            and answering questions about scientific topics. Be specific about what types of
            research requests you can handle.
            """
        elif conversation_type == "clarification" or primary_intent == "clarification":
            system_prompt = """
            You are a GenAI Research Assistant responding to a request for clarification.
            Look at the previous messages in the conversation history to understand what needs clarification.
            Provide a clear, helpful explanation based on the context of the conversation.
            """
        elif conversation_type == "follow_up" or primary_intent == "follow_up":
            system_prompt = """
            You are a GenAI Research Assistant responding to a follow-up question.
            Look at the previous messages to understand the context, then provide a direct answer
            that builds on the prior conversation. Be concise but thorough.
            """
        else:
            # Default for general casual conversation
            system_prompt = """
            You are a GenAI Research Assistant engaging in casual conversation.
            Respond in a helpful, friendly manner while keeping responses brief and conversational.
            If the message seems to be asking about research but is unclear, gently suggest how
            you could help with more specific research questions.
            """
        
        # Generate a response using the LLM
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history for context (last 5 messages)
        if conversation_history:
            messages.extend([
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_history[-5:]
            ])
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Get completion from LLM
        response_content = await get_completion(
            self.llm_client,
            messages=messages
        )
        
        # Generate a few recommendations based on the conversation
        recommendations = await self._generate_recommendations(user_message, conversation_history)
        
        # Prepare metadata
        metadata = {
            "handler_type": "conversation_handler",
            "conversation_type": conversation_type or "general",
            "primary_intent": primary_intent,
            "recommendations": recommendations,
            "processing_time_ms": int((time.time() - self.start_time) * 1000)
        }
        
        return {
            "response": response_content,
            "metadata": metadata
        }
        
    async def _generate_recommendations(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Generate simple conversation-relevant recommendations.
        """
        import re
        
        # Create a prompt for recommendation generation
        prompt = f"""
        Based on the user's message and the conversation history, suggest 3-5 related topics 
        that might interest them for further research.
        
        User message: {user_message}
        
        Return your response as a JSON array of recommendations, where each includes:
        1. title: A clear, concise title for the recommendation
        2. description: Brief explanation of why this might be interesting (1-2 sentences)
        3. type: Either "topic", "concept", or "research_area"
        4. relevance_score: A number between 0 and 1 indicating relevance
        
        Format as a clean JSON array only, no markdown or explanation.
        """
        
        # Include recent conversation context
        conversation_context = ""
        if conversation_history:
            last_messages = conversation_history[-3:]  # Get last 3 messages
            conversation_context = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in last_messages
            ])
        
        try:
            # Get recommendations from LLM
            result = await get_completion(
                self.llm_client,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Conversation context:\n{conversation_context}\n\nGenerate recommendations:"}
                ],
                response_format={"type": "json_object"} if self.settings.PRIMARY_LLM in self.settings.OPENAI_MODELS else None
            )
            
            # Clean up the result string if needed
            if "```json" in result:
                # Extract content from markdown code blocks
                json_match = re.search(r"```json\s*([\s\S]*?)\s*```", result)
                if json_match:
                    result = json_match.group(1).strip()
            elif "```" in result:
                # Handle generic code blocks
                json_match = re.search(r"```\s*([\s\S]*?)\s*```", result)
                if json_match:
                    result = json_match.group(1).strip()
            
            # Parse and validate the JSON
            recommendations_data = json.loads(result)
            
            # Handle different response formats
            if isinstance(recommendations_data, dict) and "recommendations" in recommendations_data:
                recommendations = recommendations_data["recommendations"]
            elif isinstance(recommendations_data, list):
                recommendations = recommendations_data
            else:
                recommendations = []
            
            # Validate and ensure all fields are present
            for i, rec in enumerate(recommendations):
                if not isinstance(rec, dict):
                    continue
                
                # Ensure all required fields exist
                rec["title"] = rec.get("title", f"Research topic {i+1}")
                rec["description"] = rec.get("description", "An interesting topic related to your conversation.")
                rec["type"] = rec.get("type", "topic")
                rec["relevance_score"] = float(rec.get("relevance_score", 0.7))
            
            # Sort by relevance
            recommendations.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except (json.JSONDecodeError, Exception) as e:
            # Generate default recommendations on error
            logging.warning(f"Error generating conversation recommendations: {str(e)}")
            return self._generate_default_recommendations(user_message)
    
    def _generate_default_recommendations(self, user_message: str) -> List[Dict[str, Any]]:
        """Generate default recommendations if LLM-based generation fails."""
        # Extract key terms from the user message
        words = user_message.lower().split()
        key_terms = [word for word in words if len(word) > 3 and word not in 
                    {'what', 'when', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how',
                     'about', 'from', 'into', 'after', 'with', 'this', 'that', 'these', 'those'}]
        
        # Use the first 3 key terms or fewer if not enough
        key_terms = key_terms[:3] if key_terms else ["research", "help"]
        
        # Generate recommendations based on these terms
        recommendations = []
        types = ["topic", "concept", "research_area"]
        
        for i, term in enumerate(key_terms):
            recommendations.append({
                "title": f"Research about {term}",
                "description": f"Explore academic resources and information related to {term}.",
                "type": types[i % len(types)],
                "relevance_score": 0.8 - (i * 0.1)
            })
        
        # Add a general recommendation
        recommendations.append({
            "title": "Trending research topics",
            "description": "Discover current trends in academic research.",
            "type": "topic",
            "relevance_score": 0.6
        })
        
        return recommendations 