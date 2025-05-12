"""
Task decomposition agent for the GenAI Research Assistant.
This file implements a specialized agent for breaking down complex research tasks 
into atomic operations that can be executed by specialized agents.
"""
from typing import Dict, Any, List, Optional
import json
import logging
import re

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

class ResearchTaskDecomposer:
    """Breaks complex research tasks into atomic operations"""
    
    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
    
    async def decompose(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Decomposes a complex query into atomic research tasks
        
        Args:
            user_query: The user's original research query
            
        Returns:
            List of task dictionaries with operations and dependencies
        """
        logger.info(f"Decomposing research task: {user_query}")
        
        # Check for template queries that might have specific decomposition patterns
        task_type = self._detect_task_type(user_query)
        
        # If it's a template query, use the appropriate template
        if task_type:
            tasks = await self._apply_task_template(task_type, user_query)
        else:
            # For custom queries, use the general decomposition approach
            tasks = await self._general_decomposition(user_query)
            
        logger.info(f"Decomposed into {len(tasks)} sub-tasks")
        return tasks
    
    def _detect_task_type(self, query: str) -> Optional[str]:
        """Detect if the query matches one of our standard templates"""
        query_lower = query.lower()
        
        # Check for standard research templates
        if query_lower.startswith("summarize the following paper"):
            return "paper_summary"
        elif query_lower.startswith("compare these research methods"):
            return "method_comparison"
        elif query_lower.startswith("explain this concept in simple terms"):
            return "concept_explanation"
        elif query_lower.startswith("generate a research question about"):
            return "research_question"
        
        # More complex pattern matching
        if re.search(r"compare\s+(the\s+)?(difference|similarities)?\s*between", query_lower):
            return "method_comparison"
        if re.search(r"explain\s+(what|how|why)\s+(is|are|does)", query_lower):
            return "concept_explanation"
        if re.search(r"summarize\s+(this|the|that|these)\s+(paper|article|publication|study)", query_lower):
            return "paper_summary"
            
        return None
    
    async def _apply_task_template(self, task_type: str, query: str) -> List[Dict[str, Any]]:
        """Apply a predefined task template based on query type"""
        
        if task_type == "paper_summary":
            # Extract paper title or DOI/URL if present
            paper_title = query.replace("Summarize the following paper:", "").strip()
            return [
                {"id": "task1", "operation": "search_papers", "description": f"Find paper: {paper_title}", "dependencies": [], "priority": 1},
                {"id": "task2", "operation": "analyze_paper", "description": "Extract key components from paper", "dependencies": ["task1"], "priority": 2},
                {"id": "task3", "operation": "synthesize_summary", "description": "Create comprehensive paper summary", "dependencies": ["task2"], "priority": 3}
            ]
            
        elif task_type == "method_comparison":
            # Try to extract methods to compare
            methods_text = query.replace("Compare these research methods:", "").strip()
            methods = [m.strip() for m in re.split(r',|\band\b', methods_text) if m.strip()]
            
            tasks = []
            for i, method in enumerate(methods, 1):
                tasks.append({
                    "id": f"search{i}", 
                    "operation": "search_papers", 
                    "description": f"Find papers on {method}", 
                    "dependencies": [], 
                    "priority": 1
                })
                
            # Add the comparison task
            method_search_ids = [f"search{i}" for i in range(1, len(methods) + 1)]
            tasks.append({
                "id": "compare", 
                "operation": "compare_papers", 
                "description": f"Compare the research methods: {', '.join(methods)}", 
                "dependencies": method_search_ids, 
                "priority": 2
            })
            
            return tasks
            
        elif task_type == "concept_explanation":
            # Extract the concept to explain
            concept = query.replace("Explain this concept in simple terms:", "").strip()
            return [
                {"id": "task1", "operation": "search_papers", "description": f"Find papers about {concept}", "dependencies": [], "priority": 1},
                {"id": "task2", "operation": "search_web", "description": f"Find general information about {concept}", "dependencies": [], "priority": 1},
                {"id": "task3", "operation": "explain_concept", "description": f"Create simple explanation of {concept}", "dependencies": ["task1", "task2"], "priority": 2}
            ]
            
        elif task_type == "research_question":
            # Extract the topic for research question generation
            topic = query.replace("Generate a research question about:", "").strip()
            return [
                {"id": "task1", "operation": "search_papers", "description": f"Find recent papers about {topic}", "dependencies": [], "priority": 1},
                {"id": "task2", "operation": "search_web", "description": f"Find current developments in {topic}", "dependencies": [], "priority": 1},
                {"id": "task3", "operation": "analyze_research_gaps", "description": f"Identify research gaps in {topic}", "dependencies": ["task1", "task2"], "priority": 2},
                {"id": "task4", "operation": "generate_question", "description": f"Generate novel research questions about {topic}", "dependencies": ["task3"], "priority": 3}
            ]
            
        else:
            # Fallback to general decomposition
            return await self._general_decomposition(query)
    
    async def _general_decomposition(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Use the LLM to decompose a custom query into atomic tasks
        """
        prompt = f"""
        Decompose this research task into atomic operations:
        
        QUERY: {user_query}
        
        Break this into a JSON array of sub-tasks, where each has:
        1. "id": A unique identifier for the task (e.g., "task1")
        2. "operation": One of [search_papers, search_web, analyze_paper, compare_papers, 
                             synthesize_concept, generate_question]
        3. "description": Specific details for this operation
        4. "dependencies": List of other task IDs this depends on
        5. "priority": Number 1-5 (1 highest)
        
        For example, "Compare BERT and GPT" would decompose into:
        [
          {{"id": "task1", "operation": "search_papers", "description": "Find key papers on BERT", "dependencies": [], "priority": 1}},
          {{"id": "task2", "operation": "search_papers", "description": "Find key papers on GPT", "dependencies": [], "priority": 1}},
          {{"id": "task3", "operation": "analyze_paper", "description": "Extract BERT architectures", "dependencies": ["task1"], "priority": 2}},
          {{"id": "task4", "operation": "analyze_paper", "description": "Extract GPT architectures", "dependencies": ["task2"], "priority": 2}},
          {{"id": "task5", "operation": "compare_papers", "description": "Compare architectures", "dependencies": ["task3", "task4"], "priority": 3}}
        ]
        """
        
        try:
            result = await get_completion(
                self.llm_client,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_query}
                ],
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict) and "tasks" in parsed_result:
                    tasks = parsed_result["tasks"]
                elif isinstance(parsed_result, list):
                    tasks = parsed_result
                else:
                    tasks = []
                
                # Validate tasks
                return self._validate_and_enhance_tasks(tasks)
                
            except json.JSONDecodeError:
                logger.error("Failed to parse task decomposition as JSON")
                # Fallback to simple task
                return [{"id": "task1", "operation": "search_papers", "description": user_query, "dependencies": [], "priority": 1}]
                
        except Exception as e:
            logger.error(f"Error decomposing task: {str(e)}")
            # Fallback to simple task
            return [{"id": "task1", "operation": "search_papers", "description": user_query, "dependencies": [], "priority": 1}]
    
    def _validate_and_enhance_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate task structure and enhance with missing fields
        """
        valid_operations = {
            "search_papers", "search_web", "analyze_paper", "compare_papers",
            "synthesize_concept", "explain_concept", "generate_question"
        }
        
        enhanced_tasks = []
        
        for i, task in enumerate(tasks):
            # Ensure task has all required fields
            enhanced_task = {
                "id": task.get("id", f"task{i+1}"),
                "operation": task.get("operation", "search_papers"),
                "description": task.get("description", "General research task"),
                "dependencies": task.get("dependencies", []),
                "priority": task.get("priority", 1)
            }
            
            # Validate operation
            if enhanced_task["operation"] not in valid_operations:
                enhanced_task["operation"] = "search_papers"
                
            # Ensure dependencies exist in our task list
            task_ids = [t.get("id", f"task{j+1}") for j, t in enumerate(tasks)]
            enhanced_task["dependencies"] = [d for d in enhanced_task["dependencies"] if d in task_ids]
            
            # Add to enhanced tasks
            enhanced_tasks.append(enhanced_task)
            
        # Sort by dependencies and priority
        return self._sort_tasks_by_dependencies(enhanced_tasks)
    
    def _sort_tasks_by_dependencies(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort tasks so that dependencies appear before the tasks that depend on them
        """
        # Create a task ID to index mapping
        task_id_to_index = {task["id"]: i for i, task in enumerate(tasks)}
        
        # Create a directed graph for topological sorting
        graph = {i: [] for i in range(len(tasks))}
        for i, task in enumerate(tasks):
            for dep_id in task["dependencies"]:
                if dep_id in task_id_to_index:
                    graph[task_id_to_index[dep_id]].append(i)
                    
        # Topological sort implementation
        visited = [False] * len(tasks)
        temp = [False] * len(tasks)
        result = []
        
        def dfs(node):
            if temp[node]:
                # Found a cycle, break the dependency
                tasks[node]["dependencies"] = []
                return
            if not visited[node]:
                temp[node] = True
                for neighbor in graph[node]:
                    dfs(neighbor)
                temp[node] = False
                visited[node] = True
                result.append(node)
        
        for i in range(len(tasks)):
            if not visited[i]:
                dfs(i)
                
        # Reverse the result to get correct order
        result.reverse()
        
        # Sort tasks with same dependencies by priority
        sorted_tasks = [tasks[i] for i in result]
        return sorted(sorted_tasks, key=lambda t: t["priority"]) 