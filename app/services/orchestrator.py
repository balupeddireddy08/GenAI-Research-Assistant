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
from app.services.task_decomposer import ResearchTaskDecomposer
from app.services.comparison_agent import PaperComparisonAgent
from app.services.intent_analysis_agent import IntentAnalysisAgent
from app.services.identity_handler import IdentityHandler
from app.services.conversation_handler import ConversationHandler
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
            # Core LLM clients - primary for complex tasks, secondary for simpler steps
            self.primary_llm_client = get_llm_client(settings, use_secondary=False)
            self.secondary_llm_client = get_llm_client(settings, use_secondary=True)
            
            # Initialize specialized agents
            self.search_agent = SearchAgent(settings)
            self.academic_agent = AcademicAgent(settings)
            self.synthesis_agent = SynthesisAgent(settings)
            self.task_decomposer = ResearchTaskDecomposer(settings)
            self.comparison_agent = PaperComparisonAgent(settings)
            
            # New components for improved intent analysis and response handling
            self.intent_analysis_agent = IntentAnalysisAgent(settings)
            self.identity_handler = IdentityHandler(settings)
            self.conversation_handler = ConversationHandler(settings)
        except Exception as e:
            logger.error(f"Error initializing orchestrator: {str(e)}")
            # Still initialize, but we'll handle errors in the process method
            self.primary_llm_client = None
            self.secondary_llm_client = None
            self.search_agent = None
            self.academic_agent = None
            self.synthesis_agent = None
            self.task_decomposer = None
            self.comparison_agent = None
            self.intent_analysis_agent = None
            self.identity_handler = None
            self.conversation_handler = None
    
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
            "primary_model": self.settings.PRIMARY_LLM,
            "secondary_model": self.settings.SECONDARY_LLM,
            "success": True,
            "error": None,
            "processing_status": self.processing_status
        }
        
        # Handle initialization errors
        if self.primary_llm_client is None or self.secondary_llm_client is None:
            error_msg = "System initialization failed. Please check your API keys and configuration."
            metadata["success"] = False
            metadata["error"] = error_msg
            self._update_status("error", details={"error": error_msg})
            return error_msg, metadata
        
        try:
            # Step 1: Intent Analysis - Use secondary model for intent analysis
            self._update_status("analyzing_intent", details={"message": "Analyzing your query to understand the intent..."})
            intent_analysis = await self.intent_analysis_agent.analyze_intent(user_message, conversation_history)
            
            # Store intent analysis in metadata
            metadata["intent_analysis"] = intent_analysis
            
            # Update status with intent information
            self._update_status("intent_analyzed", details={
                "message": f"Intent identified: {intent_analysis.get('primary_intent', 'unknown')}",
                "intent": intent_analysis
            })
            
            # Step 2: Route to appropriate handler based on intent
            handler = intent_analysis.get("handler", "research_handler")
            
            # Handle identity questions with the identity handler
            if handler == "identity_handler":
                self._update_status("handling_identity", details={"message": "Processing identity question..."})
                handler_result = await self.identity_handler.handle_identity_question(user_message, intent_analysis)
                response_content = handler_result.get("response", "")
                
                # Add handler metadata to main metadata
                metadata.update(handler_result.get("metadata", {}))
                metadata["handler_used"] = "identity_handler"
                
                # Mark completion
                self._update_status("completed", details={
                    "message": "Identity response completed", 
                    "time_taken": time.time() - self.processing_status["start_time"]
                })
                
                # Update final processing status
                metadata["processing_status"] = self.processing_status
                return response_content, metadata
            
            # Handle conversational queries with the conversation handler
            elif handler == "conversation_handler":
                self._update_status("handling_conversation", details={"message": "Processing conversational message..."})
                handler_result = await self.conversation_handler.handle_conversation(
                    user_message, 
                    intent_analysis,
                    conversation_history
                )
                response_content = handler_result.get("response", "")
                
                # Add handler metadata to main metadata
                metadata.update(handler_result.get("metadata", {}))
                metadata["handler_used"] = "conversation_handler"
                
                # Mark completion
                self._update_status("completed", details={
                    "message": "Conversational response completed", 
                    "time_taken": time.time() - self.processing_status["start_time"]
                })
                
                # Update final processing status
                metadata["processing_status"] = self.processing_status
                return response_content, metadata
            
            # For research queries, continue with the research pipeline
            # Step 3: Determine if task decomposition is needed
            requires_planning = intent_analysis.get("requires_planning", True)
            
            # Initialize is_complex_task with default value of False
            is_complex_task = False
            
            if requires_planning:
                # Check if this is a complex research task that needs decomposition
                is_complex_task = self._is_complex_research_task(user_message, intent_analysis)
            
            if is_complex_task and self.task_decomposer:
                # For complex tasks, use the task decomposer with primary model
                self._update_status("decomposing_task", details={"message": "Breaking down your complex research query..."})
                decomposed_tasks = await self.task_decomposer.decompose(user_message)
                
                # Store decomposition in metadata
                metadata["task_decomposition"] = decomposed_tasks
                
                # Create execution plan from decomposed tasks
                plan = self._convert_decomposed_tasks_to_plan(decomposed_tasks)
            else:
                # For simpler tasks, use the standard plan generator with reasoning
                self._update_status("generating_plan", details={"message": "Creating a plan to answer your query..."})
                plan = await self._generate_plan_with_reasoning(user_message, intent_analysis)
            
            # Store plan in metadata
            metadata["execution_plan"] = plan
            
            # Step 4: Execute the plan
            self._update_status("executing_plan", details={"message": "Executing research plan..."})
            execution_results = await self._execute_plan(plan, user_message, intent_analysis)
            
            # Store execution results in metadata
            metadata["execution_results"] = execution_results
            
            # Step 5: Synthesize the final response from all results
            self._update_status("synthesizing_response", details={"message": "Synthesizing final response..."})
            response_content, synthesis_metadata = await self._synthesize_response(
                user_message,
                execution_results,
                conversation_history
            )
            
            # Merge synthesis metadata with main metadata
            metadata.update(synthesis_metadata)
            
            # Generate recommendations based on the query and results
            self._update_status("generating_recommendations", details={"message": "Generating follow-up recommendations..."})
            recommendations = await self._generate_recommendations(user_message, execution_results)
            
            # Add recommendations to metadata
            metadata["recommendations"] = recommendations
            
            # Mark completion
            self._update_status("completed", details={
                "message": "Research completed successfully", 
                "time_taken": time.time() - self.processing_status["start_time"]
            })
            
            # Update final processing status
            metadata["processing_status"] = self.processing_status
            
            return response_content, metadata
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            
            # Update metadata with error information
            metadata["success"] = False
            metadata["error"] = error_msg
            
            # Update status
            self._update_status("error", details={"error": error_msg})
            metadata["processing_status"] = self.processing_status
            
            # Fallback response using the primary model
            fallback_response = await self._generate_fallback_response(user_message, conversation_history, error_msg)
            
            return fallback_response, metadata
    
    def _is_complex_research_task(self, user_message: str, intent_analysis: Dict[str, Any]) -> bool:
        """Determine if a user query is a complex research task that needs decomposition"""
        # Look for comparison terms
        comparison_terms = ['compare', 'difference', 'similarities', 'versus', 'vs']
        has_comparison = any(term in user_message.lower() for term in comparison_terms)
        
        # Look for explanation terms
        explanation_terms = ['explain', 'what is', 'how does', 'why is', 'describe']
        has_explanation = any(term in user_message.lower() for term in explanation_terms)
        
        # Look for multiple entities (often indicates comparison)
        entities = intent_analysis.get('entities', [])
        has_multiple_entities = isinstance(entities, list) and len(entities) > 1
        
        # Check primary intent from analysis
        primary_intent = intent_analysis.get('primary_intent', '').lower()
        is_comparison_intent = 'compar' in primary_intent or 'contrast' in primary_intent
        is_explanation_intent = 'explain' in primary_intent or 'describ' in primary_intent
        
        # Check complexity level from intent analysis
        complexity = intent_analysis.get('complexity', 'simple').lower()
        is_complex = complexity in ['complex', 'moderate']
        
        # Decide if this is a complex task
        return (has_comparison or is_comparison_intent or 
                (has_explanation and has_multiple_entities) or
                is_explanation_intent or
                is_complex)
    
    def _convert_decomposed_tasks_to_plan(self, decomposed_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert decomposed tasks from task_decomposer to execution plan format"""
        execution_plan = []
        
        # Map operations to agents
        operation_to_agent = {
            "search_papers": "academic_agent",
            "search_web": "search_agent",
            "analyze_paper": "academic_agent",
            "compare_papers": "comparison_agent",
            "compare_research_methods": "comparison_agent",
            "explain_concept": "comparison_agent",
            "synthesize_concept": "synthesis_agent",
            "generate_question": "synthesis_agent"
        }
        
        # Convert each task to the plan format
        for task in decomposed_tasks:
            operation = task.get("operation", "search_papers")
            agent = operation_to_agent.get(operation, "search_agent")
            
            execution_plan.append({
                "agent": agent,
                "task": task.get("description", "Search for information"),
                "priority": task.get("priority", 2),
                "operation": operation,  # Keep the original operation for specialized handling
                "task_id": task.get("id", "unknown"),  # Keep original task ID for dependency tracking
                "dependencies": task.get("dependencies", [])  # Keep dependencies for execution order
            })
        
        return execution_plan
    
    def _update_status(self, step: str, details: Dict[str, Any] = None):
        """Update the processing status with a new step and optional details."""
        # If this is the first time we're seeing this step, add it to completed steps
        if step not in self.processing_status["steps_completed"]:
            self.processing_status["steps_completed"].append(step)
            
        # Update current step
        self.processing_status["current_step"] = step
        
        # Add or update detailed status
        if details:
            if "detailed_status" not in self.processing_status:
                self.processing_status["detailed_status"] = {}
            
            # Add timestamp
            details["timestamp"] = time.time()
            
            # Store details
            self.processing_status["detailed_status"][step] = details
        
        # Calculate progress percentage
        completed = len(self.processing_status["steps_completed"])
        total = self.processing_status["steps_total"]
        self.processing_status["progress_percent"] = min(int((completed / total) * 100), 100)
        
        # Only log major status updates, not subtasks
        if not step.startswith("subtask_"):
            logger.info(f"Processing status: {step} - {self.processing_status['progress_percent']}% complete")
    
    async def _generate_simple_plan(
        self, 
        user_message: str, 
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate a simple execution plan for the user query.
        Uses the secondary model for this simpler task.
        
        Args:
            user_message: The user's message
            intent_analysis: Results of intent analysis
            
        Returns:
            List of plan steps
        """
        try:
            # For simple plans, use the secondary model
            prompt = f"""
            You are a research planning assistant. Generate a simple execution plan for the following query.
            The plan should be a JSON list of steps, where each step has:
            - "step_id": a unique identifier (integer)
            - "task": a short description of what needs to be done
            - "agent": which agent should handle it ("search", "academic", "synthesis")
            - "dependencies": list of step_ids this step depends on (can be empty)
            
            User Query: {user_message}
            
            Intent Analysis: {json.dumps(intent_analysis)}
            
            Response format example:
            [
                {{"step_id": 1, "task": "Search for recent papers on X", "agent": "search", "dependencies": []}},
                {{"step_id": 2, "task": "Analyze key findings from papers", "agent": "academic", "dependencies": [1]}},
                {{"step_id": 3, "task": "Synthesize comprehensive answer", "agent": "synthesis", "dependencies": [2]}}
            ]
            """
            
            # Use secondary model for plan generation
            response = await get_completion(
                self.secondary_llm_client,
                messages=[
                    {"role": "system", "content": "You are a helpful research planning assistant."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                use_secondary=True
            )
            
            # Parse the JSON response
            try:
                plan = json.loads(response)
                # Ensure we have a list
                if not isinstance(plan, list):
                    if isinstance(plan, dict) and "plan" in plan:
                        plan = plan["plan"]
                    else:
                        plan = []
                        
                return plan
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse plan JSON, using fallback plan: {response}")
                # Return a fallback plan
                return [
                    {"step_id": 1, "task": "Search for information", "agent": "search", "dependencies": []},
                    {"step_id": 2, "task": "Synthesize answer", "agent": "synthesis", "dependencies": [1]}
                ]
                
        except Exception as e:
            logger.error(f"Error generating simple plan: {str(e)}")
            # Return a minimal fallback plan
            return [
                {"step_id": 1, "task": "Search for information", "agent": "search", "dependencies": []},
                {"step_id": 2, "task": "Synthesize answer", "agent": "synthesis", "dependencies": [1]}
            ]
    
    async def _generate_plan_with_reasoning(
        self, 
        user_message: str, 
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate an execution plan with explicit reasoning.
        Uses the primary model for this complex task.
        
        Args:
            user_message: The user's message
            intent_analysis: Results of intent analysis
            
        Returns:
            List of plan steps
        """
        try:
            prompt = f"""
            You are a meticulous research planning assistant. Given a user query, generate a detailed execution plan.
            
            First, analyze the query and explain your reasoning about:
            1. What information needs to be gathered
            2. What analysis needs to be performed
            3. How the results should be synthesized
            
            Then, generate a JSON execution plan with these steps:
            - "step_id": A unique identifier (integer)
            - "task": A clear description of what needs to be done 
            - "agent": Which agent should handle it (search, academic, synthesis, or comparison)
            - "dependencies": List of step_ids this step depends on
            - "reasoning": Why this step is necessary
            
            User Query: {user_message}
            
            Intent Analysis: {json.dumps(intent_analysis)}
            """
            
            # Use primary model for complex reasoning task
            response = await get_completion(
                self.primary_llm_client,
                messages=[
                    {"role": "system", "content": "You are a helpful research planning assistant."},
                    {"role": "user", "content": prompt}
                ],
                use_secondary=False
            )
            
            # Extract the JSON plan from the response
            # Find JSON part in the response (between ```json and ```)
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            
            if json_match:
                plan_json = json_match.group(1).strip()
            else:
                # Try to find an array in the text
                array_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
                if array_match:
                    plan_json = array_match.group(0)
                else:
                    # Use regex to find all JSON-like objects and try to construct a plan
                    object_matches = re.findall(r'\{\s*"step_id"\s*:.*?\}', response, re.DOTALL)
                    if object_matches:
                        plan_json = "[" + ",".join(object_matches) + "]"
                    else:
                        # No JSON found, use simple plan generation
                        logger.warning("No JSON plan found in response, falling back to simple plan")
                        return await self._generate_simple_plan(user_message, intent_analysis)
            
            # Parse the JSON
            try:
                plan = json.loads(plan_json)
                # Ensure we have a list
                if not isinstance(plan, list):
                    if isinstance(plan, dict) and "plan" in plan:
                        plan = plan["plan"]
                    else:
                        plan = []
                        
                # Ensure each step has the required fields
                for step in plan:
                    if "dependencies" not in step:
                        step["dependencies"] = []
                    if "reasoning" not in step:
                        step["reasoning"] = "Supporting the research process"
                        
                return plan
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse complex plan JSON: {plan_json}")
                # Fall back to simple plan generation
                return await self._generate_simple_plan(user_message, intent_analysis)
                
        except Exception as e:
            logger.error(f"Error generating plan with reasoning: {str(e)}")
            # Fall back to simple plan
            return await self._generate_simple_plan(user_message, intent_analysis)
    
    async def _execute_plan(
        self, 
        plan: List[Dict[str, Any]], 
        user_message: str,
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a plan by dispatching tasks to the appropriate agents.
        
        Args:
            plan: The execution plan
            user_message: The original user message
            intent_analysis: Analysis of the user's intent
            
        Returns:
            Dictionary containing execution results
        """
        self._update_status("executing_plan", details={
            "plan": plan,
            "message": "Executing search and retrieval operations..."
        })
        
        # Track dependencies
        task_results = {}
        completed_task_ids = set()
        
        # Group tasks by priority
        tasks_by_priority = {}
        for task in plan:
            priority = task.get("priority", 1)
            if priority not in tasks_by_priority:
                tasks_by_priority[priority] = []
            tasks_by_priority[priority].append(task)
        
        # Execute tasks in priority order
        priorities = sorted(tasks_by_priority.keys())
        
        operations = []
        for task in plan:
            agent_name = task.get('agent', 'unknown')
            task_desc = task.get('task', '')[:50]
            operations.append(f"{agent_name}: {task_desc}...")
            
            # Add each agent to the detailed status for better frontend display
            self._update_status(f"agent_{agent_name}", details={
                "status": "pending",
                "task": task.get('task', ''),
                "operations": [f"{task.get('operation', 'unknown')}: {task_desc}..."]
            })
        
        self._update_status("executing", details={
            "message": f"Executing {len(operations)} search operations",
            "operations": operations
        })
        
        for priority in priorities:
            tasks = tasks_by_priority[priority]
            
            # Collect tasks at this priority level that have all dependencies satisfied
            executable_tasks = []
            for task in tasks:
                dependencies = task.get("dependencies", [])
                if all(dep in completed_task_ids for dep in dependencies):
                    executable_tasks.append(task)
            
            # Execute tasks in parallel
            task_futures = []
            for task in executable_tasks:
                task_id = task.get("task_id", f"task_{len(task_results)}")
                agent_name = task.get("agent", "")
                operation = task.get("operation", "")
                
                # Update status for this subtask
                self._update_status("subtask_starting", details={
                    f"{agent_name}_{task_id}": {
                        "status": "in_progress",
                        "message": f"Starting {agent_name} task: {task.get('task', '')[:50]}..."
                    }
                })
                
                # Dispatch task to the appropriate agent
                if agent_name == "academic_agent" and operation == "search_papers":
                    future = asyncio.ensure_future(
                        self.academic_agent.search_papers(task.get("task", ""), intent_analysis)
                    )
                elif agent_name == "search_agent" and (operation == "web_search" or operation == "search_web"):
                    future = asyncio.ensure_future(
                        self.search_agent.search(task.get("task", ""), intent_analysis)
                    )
                elif agent_name == "comparison_agent" and (operation == "compare_papers" or operation == "compare_research_methods"):
                    # Get results from dependent tasks
                    paper_sets = []
                    for dep in task.get("dependencies", []):
                        if dep in task_results:
                            papers = task_results[dep].get("papers", [])
                            paper_sets.append(papers)
                    
                    future = asyncio.ensure_future(
                        self._handle_comparison_task(task, paper_sets, user_message, intent_analysis)
                    )
                else:
                    # Unknown agent/operation
                    future = asyncio.Future()
                    future.set_result({
                        "error": f"Unknown agent or operation: {agent_name}/{operation}"
                    })
                
                task_futures.append((task_id, agent_name, future))
            
            # Wait for all tasks at this priority level to complete
            for task_id, agent_name, future in task_futures:
                try:
                    result = await future
                    
                    # Fallback to search agent if academic agent found insufficient results
                    if agent_name == "academic_agent" and operation == "search_papers":
                        papers = result.get("papers", [])
                        if not papers or len(papers) < 2:
                            self._update_status("fallback_to_search", details={
                                "message": f"Academic agent found insufficient results, falling back to search agent",
                                "papers_found": len(papers)
                            })
                            
                            # Execute the same query with the search agent as fallback
                            search_result = await self.search_agent.search(task.get("task", ""), intent_analysis)
                            
                            # Combine the results
                            search_items = search_result.get("results", [])
                            for item in search_items:
                                if "title" in item and "content" in item:
                                    papers.append({
                                        "title": item["title"],
                                        "summary": item.get("content", ""),
                                        "link": item.get("url", ""),
                                        "source": "web_search",
                                        "source_operation": "search_web",
                                        "relevance_assessment": item.get("relevance_assessment", {})
                                    })
                            
                            result["papers"] = papers
                            result["used_fallback"] = True
                    
                    task_results[task_id] = result
                    completed_task_ids.add(task_id)
                    
                    # Update status for the completed subtask
                    self._update_status("subtask_completed", details={
                        f"{agent_name}_{task_id}": {
                            "status": "completed",
                            "message": f"Completed {agent_name} task"
                        }
                    })
                    
                    # Also update the agent status for the frontend display
                    agent_status = self.processing_status.get("detailed_status", {}).get(f"agent_{agent_name}", {})
                    if agent_status:
                        # Update operations to include results if appropriate
                        if "results" in result:
                            agent_status["results"] = result.get("results", [])
                        if "papers" in result:
                            agent_status["sources"] = result.get("papers", [])
                        
                        agent_status["status"] = "completed"
                        self._update_status(f"agent_{agent_name}", details=agent_status)
                except Exception as e:
                    logger.error(f"Error executing task {task_id}: {str(e)}")
                    task_results[task_id] = {"error": str(e)}
                    completed_task_ids.add(task_id)
        
        self._update_status("execution_completed", details={
            "message": f"Completed {len(task_results)} search operations",
            "result_count": len(task_results)
        })
        
        return task_results
    
    async def _handle_comparison_task(
        self,
        task: Dict[str, Any],
        paper_sets: List[List[Dict[str, Any]]],
        user_message: str,
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle comparison tasks based on the operation type
        
        Args:
            task: The comparison task details
            paper_sets: Lists of papers from dependency tasks
            user_message: The original user query
            intent_analysis: The intent analysis results
            
        Returns:
            Dictionary containing comparison results
        """
        operation = task.get("operation", "")
        task_description = task.get("task", "")
        
        # Flatten papers from all sets
        all_papers = []
        for paper_set in paper_sets:
            all_papers.extend(paper_set)
            
        if not all_papers:
            # If no papers were found, attempt to get information from the web
            self._update_status("fallback_to_web_search", details={
                "message": "No papers found for comparison, searching the web for information",
                "comparison_task": task_description
            })
            
            # Extract comparison topics from the task or intent analysis
            topics = []
            if intent_analysis.get("topic_a"):
                topics.append(intent_analysis.get("topic_a"))
            if intent_analysis.get("topic_b"):
                topics.append(intent_analysis.get("topic_b"))
                
            if not topics and "compare" in task_description.lower():
                # Try to extract topics from the task description
                task_lower = task_description.lower()
                compare_idx = task_lower.find("compare")
                if compare_idx >= 0:
                    topics_text = task_description[compare_idx + 8:]  # Skip "compare "
                    if ":" in topics_text:
                        topics_text = topics_text.split(":", 1)[1]
                    if "," in topics_text:
                        topics = [t.strip() for t in topics_text.split(",")]
            
            # Search for each topic
            papers_by_method = {}
            for topic in topics:
                search_result = await self.search_agent.search(topic, intent_analysis)
                search_items = search_result.get("results", [])
                
                topic_papers = []
                for item in search_items:
                    if "title" in item and "content" in item:
                        topic_papers.append({
                            "title": item["title"],
                            "summary": item.get("content", ""),
                            "link": item.get("url", ""),
                            "source": "web_search",
                            "source_operation": "search_web",
                            "relevance_assessment": item.get("relevance_assessment", {})
                        })
                
                papers_by_method[topic] = topic_papers
                all_papers.extend(topic_papers)
        
        if operation == "compare_papers":
            comparison_criteria = task_description
            if all_papers:
                return await self.comparison_agent.compare_papers(all_papers, comparison_criteria)
            else:
                return {
                    "comparison_summary": "No papers found to compare.",
                    "error": "No papers found for comparison"
                }
        elif operation == "compare_research_methods":
            # Extract methods to compare
            methods = []
            papers_by_method = {}
        
            # Try to get methods from intent analysis
            if intent_analysis.get("topic_a") and intent_analysis.get("topic_b"):
                methods = [intent_analysis.get("topic_a"), intent_analysis.get("topic_b")]
                
                # Split papers by method if we have papers and methods
                if all_papers and methods:
                    # Basic approach: assign papers to methods based on title/summary matching
                    for method in methods:
                        method_lower = method.lower()
                        method_papers = []
                        
                        for paper in all_papers:
                            title = paper.get("title", "").lower()
                            summary = paper.get("summary", "").lower()
                            
                            if method_lower in title or method_lower in summary:
                                method_papers.append(paper)
                                
                        papers_by_method[method] = method_papers
            
            return await self.comparison_agent.compare_research_methods(user_message, methods, papers_by_method)
        elif operation == "explain_concept":
            # Extract concept from task description
            concept = task_description.replace("Explain", "").replace("concept", "").strip()
            if concept:
                return await self.comparison_agent.explain_concept(concept, all_papers)
            else:
                return {
                    "explanation": "Could not identify concept to explain.",
                    "error": "No concept specified"
                }
        else:
            return {
                "error": f"Unknown comparison operation: {operation}"
            }
    
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
        synthesis_result = await self.synthesis_agent.synthesize(
            user_message=user_message,
            agent_results=results,
            conversation_history=conversation_history
        )
        
        # Extract response content and metadata
        response_content = synthesis_result.get("response", "No response was generated.")
        metadata = synthesis_result
        
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
        import re
        import json
        import logging
        
        prompt = f"""
        Based on the user's query and the information gathered, suggest exactly 5 related topics 
        or papers that might be of interest to the user.
        
        User query: {user_message}
        
        Return a JSON array of recommendations, where each recommendation contains:
        1. title: Title of the paper or topic
        2. description: Brief description (1-2 sentences)
        3. type: "paper", "topic", or "concept"
        4. relevance_score: A number between 0 and 1 indicating how relevant this is to the query
        
        Each recommendation MUST include all these fields. Format your response as a valid JSON array.
        IMPORTANT: Do NOT wrap your response in additional explanation or markdown. Return ONLY the JSON array.
        """
        
        # Include summaries of all results in the context
        context = "\n\n".join([f"Result {i}: {str(r)[:500]}" for i, r in enumerate(results.values())])
        
        # Try multiple times to get valid JSON
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                result = await get_completion(
                    self.primary_llm_client,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"{user_message}\n\nContext:\n{context}"}
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
                return json.loads(result)
            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                return []