from typing import Dict, Any, List, Optional
import json
import aiohttp
import asyncio

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion


class SearchAgent:
    """
    Agent for performing web searches to find general information.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
        self.tavily_api_key = settings.TAVILY_API_KEY
    
    async def search(
        self, 
        task: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform a search based on the given task and intent analysis.
        
        Args:
            task: The specific search task to perform
            intent_analysis: Analysis of the user's intent
            
        Returns:
            Dictionary containing search results and metadata
        """
        # Generate an optimized search query based on the task and intent
        search_query = await self._generate_search_query(task, intent_analysis)
        
        # Perform the search using Tavily if API key is available
        if self.tavily_api_key:
            search_results = await self._tavily_search(search_query)
        else:
            # Simulate search results if no API key is available
            search_results = await self._simulate_search(search_query)
        
        # Process and enhance the search results
        processed_results = await self._process_search_results(search_results, intent_analysis)
        
        return {
            "query": search_query,
            "results": processed_results,
            "source": "tavily" if self.tavily_api_key else "simulated"
        }
    
    async def _generate_search_query(
        self, 
        task: str, 
        intent_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate an optimized search query based on the task and intent analysis.
        """
        prompt = f"""
        Create an optimized search query for finding information about:
        
        Task: {task}
        
        Intent analysis:
        - Primary intent: {intent_analysis.get('primary_intent', 'unknown')}
        - Key entities: {', '.join(intent_analysis.get('entities', []))}
        - Information type: {intent_analysis.get('info_type', 'general')}
        - Time frame: {intent_analysis.get('time_frame', 'any')}
        - Research areas: {', '.join(intent_analysis.get('research_areas', []))}
        
        The query should be clear, specific, and include relevant keywords to maximize search relevance.
        Return just the search query with no additional commentary.
        """
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": task}
            ]
        )
        
        # Clean up the result to ensure it's a proper search query
        return result.strip().strip('"\'')
    
    async def _tavily_search(self, query: str) -> Dict[str, Any]:
        """
        Perform a search using the Tavily API.
        """
        try:
            async with aiohttp.ClientSession() as session:
                api_url = "https://api.tavily.com/search"
                payload = {
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_domains": [],
                    "exclude_domains": [],
                    "max_results": 5
                }
                
                async with session.post(api_url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"Tavily API error: {response.status}",
                            "details": error_text,
                            "results": []
                        }
        except Exception as e:
            return {
                "error": f"Exception during Tavily search: {str(e)}",
                "results": []
            }
    
    async def _simulate_search(self, query: str) -> Dict[str, Any]:
        """
        Simulate search results when no search API is available.
        This is useful for development or when API keys are not configured.
        """
        prompt = f"""
        Simulate search results for the query: "{query}"
        
        Generate 5 search results with:
        1. title - Title of the page/article
        2. url - A plausible URL
        3. content - A short snippet or summary (2-3 sentences)
        4. score - A relevance score between 0 and 1
        
        Return the results as a JSON object with a "results" array containing these fields.
        """
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Fallback if the LLM doesn't return valid JSON
            return {
                "results": [
                    {
                        "title": f"Simulated result for '{query}'",
                        "url": "https://example.com/result",
                        "content": f"This is a simulated search result for the query: {query}. No actual search was performed as this is running in development mode without a search API key.",
                        "score": 0.8
                    }
                ]
            }
    
    async def _process_search_results(
        self, 
        search_results: Dict[str, Any],
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process and enhance the search results to make them more useful.
        """
        if "error" in search_results:
            return [{"error": search_results["error"]}]
        
        results = search_results.get("results", [])
        
        if not results:
            return []
        
        # For each result, add a relevance assessment based on the intent
        for result in results:
            if "content" in result and "title" in result:
                result["relevance_assessment"] = await self._assess_relevance(
                    result["title"], 
                    result["content"], 
                    intent_analysis
                )
        
        # Sort results by relevance (if available) or score
        if all("relevance_assessment" in r and "score" in r["relevance_assessment"] for r in results):
            results.sort(key=lambda x: x["relevance_assessment"]["score"], reverse=True)
        elif all("score" in r for r in results):
            results.sort(key=lambda x: x["score"], reverse=True)
        
        return results
    
    async def _assess_relevance(
        self, 
        title: str, 
        content: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess the relevance of a search result to the user's intent.
        """
        prompt = f"""
        Assess the relevance of this search result to the user's intent:
        
        Title: {title}
        Content: {content}
        
        User's intent:
        - Primary intent: {intent_analysis.get('primary_intent', 'unknown')}
        - Key entities: {', '.join(intent_analysis.get('entities', []))}
        - Information type: {intent_analysis.get('info_type', 'general')}
        - Research areas: {', '.join(intent_analysis.get('research_areas', []))}
        
        Return a JSON object with:
        1. score: A relevance score between 0 and 1
        2. reason: A brief explanation of why this result is or isn't relevant
        """
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Assess relevance of: {title}"}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Fallback if the LLM doesn't return valid JSON
            return {
                "score": 0.5,
                "reason": "Unable to assess relevance accurately."
            }