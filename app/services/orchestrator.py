"""
Agent orchestration system for the GenAI Research Assistant.
This file implements the central orchestrator that coordinates multiple specialized
agents, analyzes user intent, generates execution plans, and synthesizes responses.
"""
from typing import List, Dict, Any, Tuple, Optional
import json
import asyncio
import logging
import time

from app.config import settings
from app.services.search_agent import SearchAgent
from app.services.academic_agent import AcademicAgent
from app.services.synthesis_agent import SynthesisAgent
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrator agent that coordinates the multi-agent workflow.
    """

    def __init__(self, settings):
        self.settings = settings
        self.processing_status = {
            "current_step": "initializing",
            "steps_completed": [],
            "steps_total": 4,
            "start_time": time.time(),
            "detailed_status": {}
        }
        
        try:
            self.llm_client = get_llm_client(settings)
            self.search_agent = SearchAgent(settings)
            self.academic_agent = AcademicAgent(settings)
            self.synthesis_agent = SynthesisAgent(settings)
        except Exception as e:
            logger.error(f"Error initializing orchestrator: {str(e)}")
            # Still initialize, but we'll handle errors in the process method
            self.llm_client = None
            self.search_agent = None
            self.academic_agent = None
            self.synthesis_agent = None
    
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
        # Reset processing status for this new request
        self.processing_status = {
            "current_step": "starting",
            "steps_completed": [],
            "steps_total": 4,
            "start_time": time.time(),
            "detailed_status": {}
        }
        
        # Initialize default metadata
        metadata = {
            "model_used": self.settings.PRIMARY_LLM,
            "success": True,
            "error": None,
            "processing_status": self.processing_status
        }
        
        # Handle initialization errors
        if self.llm_client is None:
            error_msg = "System initialization failed. Please check your API keys and configuration."
            metadata["success"] = False
            metadata["error"] = error_msg
            self._update_status("error", details={"error": error_msg})
            return error_msg, metadata
        
        try:
            # Step 1: Input Analysis - Understand the user's intent and query
            self._update_status("analyzing_intent", details={"message": "Analyzing your query to understand the intent..."})
            intent_analysis = await self._analyze_intent(user_message, conversation_history)
            
            # Step 2: Plan generation - Plan how to answer the query
            self._update_status("generating_plan", details={"message": "Creating a plan to answer your query..."})
            plan = await self._generate_plan(user_message, intent_analysis)
            
            # Step 3: Execute the plan using specialized agents
            self._update_status("executing_plan", details={"message": "Executing search and retrieval operations...", "plan": plan})
            results = await self._execute_plan(plan, user_message, intent_analysis)
            
            # Step 4: Synthesize the final response
            self._update_status("synthesizing_response", details={"message": "Creating your comprehensive answer..."})
            response_content, synthesis_metadata = await self._synthesize_response(
                user_message, 
                results, 
                conversation_history
            )
            
            # Mark completion
            self._update_status("completed", details={"message": "Response completed", "time_taken": time.time() - self.processing_status["start_time"]})
            
            # Add plan and intent analysis to metadata for transparency
            metadata["intent_analysis"] = intent_analysis
            metadata["execution_plan"] = plan
            metadata.update(synthesis_metadata)
            
            # Check if response indicates an error
            if response_content.startswith("Error:"):
                metadata["success"] = False
                metadata["error"] = response_content
                self._update_status("error", details={"error": response_content})
            
            # Make sure the final processing status is included
            metadata["processing_status"] = self.processing_status
            
            return response_content, metadata
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in orchestrator process: {error_msg}")
            
            # Create error response
            metadata["success"] = False
            metadata["error"] = error_msg
            self._update_status("error", details={"error": error_msg})
            metadata["processing_status"] = self.processing_status
            
            return f"I encountered an error while processing your request: {error_msg}", metadata
    
    def _update_status(self, step: str, details: Dict[str, Any] = None):
        """Update the processing status with the current step and details"""
        self.processing_status["current_step"] = step
        if step not in self.processing_status["steps_completed"] and step != "error":
            self.processing_status["steps_completed"].append(step)
        
        if details:
            self.processing_status["detailed_status"][step] = details
        
        # Calculate progress percentage
        completed = len(self.processing_status["steps_completed"])
        total = self.processing_status["steps_total"]
        self.processing_status["progress_percent"] = min(int((completed / total) * 100), 100)
        
        # Log the status update
        logger.info(f"Processing status: {step} - {self.processing_status['progress_percent']}% complete")
    
    async def _analyze_intent(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze the user's intent from their message.
        """
        self._update_status("analyzing_intent", details={"message": "Analyzing intent and extracting key information..."})
        
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
            response_format={"type": "json_object"} if self.settings.PRIMARY_LLM in self.settings.OPENAI_MODELS else None
        )
        
        try:
            intent = json.loads(result)
            self._update_status("intent_analyzed", details={
                "message": f"Intent identified: {intent.get('primary_intent', 'unknown')}",
                "intent": intent
            })
            return intent
        except json.JSONDecodeError:
            # Fallback if the LLM doesn't return valid JSON
            fallback = {
                "primary_intent": "general_query",
                "entities": [],
                "info_type": "explanation",
                "time_frame": "any",
                "research_areas": []
            }
            self._update_status("intent_analyzed", details={
                "message": "Intent analysis completed with fallback",
                "intent": fallback
            })
            return fallback
    
    async def _generate_plan(
        self, 
        user_message: str, 
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate a plan of actions based on the user's intent.
        """
        self._update_status("planning", details={"message": "Creating a search and analysis plan..."})
        
        prompt = f"""
        Based on the user's query and the intent analysis, create a step-by-step plan to answer the query.
        For each step, specify which agent should be used and what specific task it should perform.
        
        Available agents:
        - academic_agent: For searching academic databases like ArXiv. STRONGLY PREFER THIS AGENT FOR ALL RESEARCH QUERIES.
        - search_agent: For web searches and finding general information. ONLY USE FOR NON-ACADEMIC INFORMATION.
        - synthesis_agent: For combining information and generating the final response.
        
        IMPORTANT: For any research-related queries about papers, articles, scientific topics, or academic concepts,
        ALWAYS use the academic_agent as your first choice. Only use search_agent when the query is clearly
        not academic in nature or requires very recent web information.
        
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
            response_format={"type": "json_object"} if self.settings.PRIMARY_LLM in self.settings.OPENAI_MODELS else None
        )
        
        try:
            plan_data = json.loads(result)
            if "steps" in plan_data:
                plan = plan_data["steps"]
            else:
                plan = plan_data
                
            self._update_status("plan_generated", details={
                "message": f"Search plan created with {len(plan)} steps",
                "plan": plan
            })
            return plan
        except (json.JSONDecodeError, TypeError):
            # Fallback now defaults to using academic_agent instead of search_agent
            fallback_plan = [
                {
                    "agent": "academic_agent",
                    "task": f"Search for academic papers about: {user_message}",
                    "priority": "high"
                },
                {
                    "agent": "synthesis_agent",
                    "task": "Synthesize the results into a comprehensive response",
                    "priority": "high"
                }
            ]
            self._update_status("plan_generated", details={
                "message": "Using fallback search plan",
                "plan": fallback_plan
            })
            return fallback_plan
    
    async def _execute_plan(
        self, 
        plan: List[Dict[str, Any]], 
        user_message: str,
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the generated plan using specialized agents.
        """
        self._update_status("executing", details={"message": "Starting search operations..."})
        
        results = {}
        tasks = []
        
        # Sort steps by priority
        priority_map = {"high": 0, "medium": 1, "low": 2}
        sorted_plan = sorted(plan, key=lambda x: priority_map.get(x.get("priority", "medium"), 1))
        
        # Update status with execution plan
        self._update_status("executing", details={
            "message": f"Executing {len(sorted_plan)} search operations",
            "operations": [f"{step.get('agent')}: {step.get('task')[:50]}..." for step in sorted_plan]
        })
        
        # Create tasks for high priority steps first
        for i, step in enumerate(sorted_plan):
            agent_name = step.get("agent")
            task = step.get("task")
            
            # Update status for this specific task
            subtask_id = f"{agent_name}_{i}"
            self._update_status("subtask_starting", details={
                subtask_id: {
                    "message": f"Starting {agent_name} task: {task[:50]}...",
                    "status": "in_progress"
                }
            })
            
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
                subtask_id = f"{agent_name}_{i}"
                results[subtask_id] = step_results[i]
                
                # Update status for the completed subtask
                self._update_status("subtask_completed", details={
                    subtask_id: {
                        "message": f"Completed {agent_name} task",
                        "status": "completed"
                    }
                })
        
        # Update status when all searches are complete
        result_count = len(results)
        self._update_status("execution_completed", details={
            "message": f"All searches completed, found {result_count} results",
            "result_count": result_count
        })
        
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
        # Update status for synthesis step
        self._update_status("synthesizing", details={
            "message": "Composing a comprehensive answer from search results..."
        })
        
        # Use the synthesis agent to combine all results
        response_content, metadata = await self.synthesis_agent.synthesize(
            user_message=user_message,
            agent_results=results,
            conversation_history=conversation_history
        )
        
        # Generate recommendations based on the query and results
        self._update_status("generating_recommendations", details={
            "message": "Generating related topic recommendations..."
        })
        
        recommendations = await self._generate_recommendations(user_message, results)
        if recommendations:
            metadata["recommendations"] = recommendations
        
        # Update final status
        self._update_status("response_ready", details={
            "message": "Response ready",
            "has_recommendations": bool(recommendations),
            "response_length": len(response_content)
        })
            
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
            response_format={"type": "json_object"} if self.settings.PRIMARY_LLM in self.settings.OPENAI_MODELS else None
        )
        
        try:
            recommendations_data = json.loads(result)
            if "recommendations" in recommendations_data:
                return recommendations_data["recommendations"]
            return recommendations_data
        except (json.JSONDecodeError, TypeError):
            return []