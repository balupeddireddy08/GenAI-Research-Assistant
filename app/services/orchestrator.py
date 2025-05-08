"""
Agent orchestration system for the GenAI Research Assistant.
This file implements the central orchestrator that coordinates multiple specialized
agents, analyzes user intent, generates execution plans, and synthesizes responses.
"""
from typing import List, Dict, Any, Tuple, Optional
import json
import asyncio

from app.config import settings
from app.services.search_agent import SearchAgent
from app.services.academic_agent import AcademicAgent
from app.services.synthesis_agent import SynthesisAgent
from app.utils.llm_utils import get_llm_client, get_completion


class AgentOrchestrator:
    """
    Orchestrator agent that coordinates the multi-agent workflow.
    """

    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
        self.search_agent = SearchAgent(settings)
        self.academic_agent = AcademicAgent(settings)
        self.synthesis_agent = SynthesisAgent(settings)
    
    async def process(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process a user message through the multi-agent system.
        
        Args:
            user_message: The user's message content
            conversation_history: List of previous messages in the conversation
            
        Returns:
            Tuple containing:
            - response_content: The text response to show the user
            - metadata: Additional metadata about the response
        """
        # Step 1: Input Analysis - Understand the user's intent and query
        intent_analysis = await self._analyze_intent(user_message, conversation_history)
        
        # Step 2: Plan generation - Plan how to answer the query
        plan = await self._generate_plan(user_message, intent_analysis)
        
        # Step 3: Execute the plan using specialized agents
        results = await self._execute_plan(plan, user_message, intent_analysis)
        
        # Step 4: Synthesize the final response
        response_content, metadata = await self._synthesize_response(
            user_message, 
            results, 
            conversation_history
        )
        
        # Add plan and intent analysis to metadata for transparency
        metadata["intent_analysis"] = intent_analysis
        metadata["execution_plan"] = plan
        
        return response_content, metadata
    
    async def _analyze_intent(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze the user's intent from their message.
        """
        prompt = f"""
        You are an intent analysis agent for a GenAI Research Assistant. 
        Analyze the user's query to identify:
        
        1. Primary intent (e.g., search for papers, explain a concept, compare methods)
        2. Key entities/topics mentioned (e.g., specific papers, authors, research areas)
        3. Type of information needed (e.g., summary, detailed explanation, latest papers)
        4. Relevant time frame (if any)
        5. Research areas involved

        User query: {user_message}
        
        Return your analysis as a JSON object with these fields.
        """
        
        # Include recent conversation history for context if available
        recent_history = conversation_history[-5:] if len(conversation_history) > 0 else []
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                *recent_history,
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Fallback if the LLM doesn't return valid JSON
            return {
                "primary_intent": "general_query",
                "entities": [],
                "info_type": "explanation",
                "time_frame": "any",
                "research_areas": []
            }
    
    async def _generate_plan(
        self, 
        user_message: str, 
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate a plan of actions based on the user's intent.
        """
        prompt = f"""
        Based on the user's query and the intent analysis, create a step-by-step plan to answer the query.
        For each step, specify which agent should be used and what specific task it should perform.
        
        Available agents:
        - search_agent: For web searches and finding general information
        - academic_agent: For searching academic databases like ArXiv
        - synthesis_agent: For combining information and generating the final response
        
        User query: {user_message}
        
        Intent analysis: {json.dumps(intent_analysis, indent=2)}
        
        Return a JSON array of steps, where each step contains:
        1. agent: The agent to use
        2. task: The specific task for the agent
        3. priority: High, medium, or low
        """
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            plan_data = json.loads(result)
            if "steps" in plan_data:
                return plan_data["steps"]
            return plan_data
        except (json.JSONDecodeError, TypeError):
            # Fallback if the LLM doesn't return valid JSON
            return [
                {
                    "agent": "search_agent",
                    "task": f"Search for information about: {user_message}",
                    "priority": "high"
                },
                {
                    "agent": "synthesis_agent",
                    "task": "Synthesize the search results into a comprehensive response",
                    "priority": "high"
                }
            ]
    
    async def _execute_plan(
        self, 
        plan: List[Dict[str, Any]], 
        user_message: str,
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the generated plan using specialized agents.
        """
        results = {}
        tasks = []
        
        # Sort steps by priority
        priority_map = {"high": 0, "medium": 1, "low": 2}
        sorted_plan = sorted(plan, key=lambda x: priority_map.get(x.get("priority", "medium"), 1))
        
        # Create tasks for high priority steps first
        for step in sorted_plan:
            agent_name = step.get("agent")
            task = step.get("task")
            
            if agent_name == "search_agent":
                tasks.append(self.search_agent.search(task, intent_analysis))
            elif agent_name == "academic_agent":
                tasks.append(self.academic_agent.search_papers(task, intent_analysis))
            # Add other agent types as needed
        
        # Execute all tasks concurrently
        if tasks:
            step_results = await asyncio.gather(*tasks)
            
            # Organize results by agent type
            for i, step in enumerate(sorted_plan[:len(step_results)]):
                agent_name = step.get("agent")
                results[f"{agent_name}_{i}"] = step_results[i]
        
        return results
    
    async def _synthesize_response(
        self, 
        user_message: str, 
        results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Synthesize the final response from all agent results.
        """
        # Use the synthesis agent to combine all results
        response_content, metadata = await self.synthesis_agent.synthesize(
            user_message=user_message,
            agent_results=results,
            conversation_history=conversation_history
        )
        
        # Generate recommendations based on the query and results
        recommendations = await self._generate_recommendations(user_message, results)
        if recommendations:
            metadata["recommendations"] = recommendations
            
        return response_content, metadata
    
    async def _generate_recommendations(
        self, 
        user_message: str, 
        results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate content recommendations based on the user's query and search results.
        """
        prompt = f"""
        Based on the user's query and the information gathered, suggest 3-5 related topics 
        or papers that might be of interest to the user.
        
        User query: {user_message}
        
        Return a JSON array of recommendations, where each recommendation contains:
        1. title: Title of the paper or topic
        2. description: Brief description (1-2 sentences)
        3. type: "paper", "topic", or "concept"
        """
        
        # Include summaries of all results in the context
        context = "\n\n".join([f"Result {i}: {str(r)[:500]}" for i, r in enumerate(results.values())])
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"{user_message}\n\nContext:\n{context}"}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            recommendations_data = json.loads(result)
            if "recommendations" in recommendations_data:
                return recommendations_data["recommendations"]
            return recommendations_data
        except (json.JSONDecodeError, TypeError):
            return []