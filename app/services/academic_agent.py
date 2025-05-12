"""
Academic search agent for the GenAI Research Assistant.
This file implements a specialized agent for searching academic papers from ArXiv,
parsing academic data, assessing relevance, and generating scholarly summaries.
"""
from typing import Dict, Any, List, Optional
import json
import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

class AcademicAgent:
    """
    Agent for searching academic papers and scholarly resources.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
        self.arxiv_api_url = settings.ARXIV_API_URL
        self.logger = logging.getLogger(__name__)
    
    async def search_papers(
        self, 
        task: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search for academic papers based on the given task and intent analysis.
        
        Args:
            task: The specific search task to perform
            intent_analysis: Analysis of the user's intent
            
        Returns:
            Dictionary containing search results and metadata
        """
        # Generate an optimized search query based on the task and intent
        search_query = await self._generate_search_query(task, intent_analysis)
        
        # Search for papers using ArXiv API
        arxiv_results = await self._search_arxiv(search_query, intent_analysis)
        
        # Process and enhance the search results
        processed_results = await self._process_paper_results(arxiv_results, intent_analysis)
        
        return {
            "query": search_query,
            "results": processed_results,
            "source": "arxiv",
            "sources": [
                {
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "description": result.get("abstract"),
                    "type": "academic",
                    "arxiv_id": result.get("id"),
                    "authors": result.get("authors"),
                    "published_date": result.get("published")
                }
                for result in processed_results
            ]
        }
    
    async def _generate_search_query(
        self, 
        task: str, 
        intent_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate an optimized academic search query based on the task and intent analysis.
        """
        # Extract domain-specific terms for query enhancement
        domains = intent_analysis.get('research_areas', [])
        entities = intent_analysis.get('entities', [])
        
        prompt = f"""
        Create an optimized academic search query for finding scholarly papers about:
        
        Task: {task}
        
        Intent analysis:
        - Primary intent: {intent_analysis.get('primary_intent', 'unknown')}
        - Key entities: {', '.join(entities)}
        - Information type: {intent_analysis.get('info_type', 'general')}
        - Time frame: {intent_analysis.get('time_frame', 'any')}
        - Research areas: {', '.join(domains)}
        
        IMPORTANT INSTRUCTIONS:
        1. The query should be concise, clear, specific, and include relevant academic keywords to maximize relevance
        2. If this is about comparing different models, methods, or technologies, make sure to include ALL the relevant terms
        3. Include foundational papers or seminal works in this field when appropriate
        4. Add domain-specific technical terminology that would appear in academic literature
        5. Format the query optimally for academic database search
        
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
        return result.strip().strip('"\'\'`')
    
    async def _search_arxiv(
        self, 
        query: str, 
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using the ArXiv API.
        """
        # Determine the time frame for filtering papers
        time_frame = intent_analysis.get('time_frame', 'any')
        
        # Set up max results based on the query complexity
        max_results = 10
        
        try:
            async with aiohttp.ClientSession() as session:
                # Construct the ArXiv API query URL
                params = {
                    'search_query': f'all:{query}',
                    'start': 0,
                    'max_results': max_results,
                    'sortBy': 'relevance',
                    'sortOrder': 'descending'
                }
                
                async with session.get(self.arxiv_api_url, params=params) as response:
                    if response.status == 200:
                        xml_response = await response.text()
                        return self._parse_arxiv_response(xml_response, time_frame)
                    else:
                        error_text = await response.text()
                        return [{
                            "error": f"ArXiv API error: {response.status}",
                            "details": error_text[:500]  # Limit error details length
                        }]
        except Exception as e:
            return [{
                "error": f"Exception during ArXiv search: {str(e)}"
            }]
    
    def _parse_arxiv_response(
        self, 
        xml_response: str, 
        time_frame: str
    ) -> List[Dict[str, Any]]:
        """
        Parse the XML response from the ArXiv API.
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_response)
            
            # ArXiv API uses the Atom namespace
            namespace = {'atom': 'http://www.w3.org/2005/Atom',
                        'arxiv': 'http://arxiv.org/schemas/atom'}
            
            # Filter based on time frame if specified
            cutoff_date = None
            if time_frame != 'any':
                now = datetime.now()
                if time_frame == 'past_week':
                    cutoff_date = now - timedelta(days=7)
                elif time_frame == 'past_month':
                    cutoff_date = now - timedelta(days=30)
                elif time_frame == 'past_year':
                    cutoff_date = now - timedelta(days=365)
            
            results = []
            entries = root.findall('.//atom:entry', namespace)
            
            for entry in entries:
                # Extract basic metadata
                title = entry.find('./atom:title', namespace).text.strip()
                abstract = entry.find('./atom:summary', namespace).text.strip()
                published_text = entry.find('./atom:published', namespace).text
                published_date = datetime.fromisoformat(published_text.replace('Z', '+00:00'))
                
                # Skip if outside the time frame
                if cutoff_date and published_date < cutoff_date:
                    continue
                
                # Get authors
                authors = []
                author_elements = entry.findall('./atom:author/atom:name', namespace)
                for author_el in author_elements:
                    authors.append(author_el.text.strip())
                
                # Get ArXiv ID
                id_text = entry.find('./atom:id', namespace).text
                arxiv_id = id_text.split('/')[-1]
                
                # Get all links with their types
                links = {}
                link_elements = entry.findall('./atom:link', namespace)
                for link_el in link_elements:
                    link_title = link_el.get('title')
                    link_url = link_el.get('href')
                    if link_title:
                        links[link_title] = link_url
                    elif link_el.get('rel') == 'alternate':
                        links['alternate'] = link_url
                
                # Get abstract link (HTML version on arxiv.org)
                abstract_link = links.get('alternate', f"https://arxiv.org/abs/{arxiv_id}")
                
                # Get PDF link
                pdf_link = links.get('pdf', f"https://arxiv.org/pdf/{arxiv_id}.pdf")
                
                # Get categories/tags
                categories = []
                category_elements = entry.findall('./atom:category', namespace)
                for cat_el in category_elements:
                    categories.append(cat_el.get('term'))
                
                results.append({
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "published_date": published_date.isoformat(),
                    "link": abstract_link,  # Main link is the abstract page
                    "pdf_link": pdf_link,   # Also include direct PDF link
                    "arxiv_id": arxiv_id,
                    "categories": categories
                })
            
            return results
        
        except Exception as e:
            return [{
                "error": f"Error parsing ArXiv response: {str(e)}"
            }]
    
    async def _process_paper_results(
        self, 
        paper_results: List[Dict[str, Any]],
        intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process and enhance the paper search results to make them more useful.
        """
        if not paper_results or "error" in paper_results[0]:
            return paper_results
        
        # For each paper, add a relevance assessment based on the intent
        enhanced_results = []
        for paper in paper_results:
            if "title" in paper and "abstract" in paper:
                relevance = await self._assess_paper_relevance(
                    paper["title"], 
                    paper["abstract"], 
                    intent_analysis
                )
                
                # Add a brief summary to make the results more useful
                summary = await self._generate_paper_summary(paper)
                
                enhanced_results.append({
                    **paper,
                    "relevance_assessment": relevance,
                    "summary": summary
                })
            else:
                enhanced_results.append(paper)
        
        # Sort results by relevance score if available
        if all("relevance_assessment" in r and "score" in r["relevance_assessment"] for r in enhanced_results):
            enhanced_results.sort(key=lambda x: x["relevance_assessment"]["score"], reverse=True)
        
        return enhanced_results
    
    async def _assess_paper_relevance(
        self, 
        title: str, 
        abstract: str, 
        intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess the relevance of a paper to the user's intent.
        """
        prompt = f"""
        Assess the relevance of this academic paper to the user's intent:
        
        Title: {title}
        Abstract: {abstract[:500]}...
        
        User's intent:
        - Primary intent: {intent_analysis.get('primary_intent', 'unknown')}
        - Key entities: {', '.join(intent_analysis.get('entities', []))}
        - Information type: {intent_analysis.get('info_type', 'general')}
        - Research areas: {', '.join(intent_analysis.get('research_areas', []))}
        
        Return a JSON object with:
        1. score: A relevance score between 0 and 1
        2. reason: A brief explanation of why this paper is or isn't relevant
        3. key_insights: 1-2 key insights from this paper relevant to the user's query
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
                "reason": "Unable to assess relevance accurately.",
                "key_insights": ["The paper may contain relevant information to your query."]
            }
    
    async def _generate_paper_summary(self, paper: Dict[str, Any]) -> str:
        """
        Generate a concise summary of a paper focusing on key findings.
        """
        prompt = f"""
        Provide a concise summary (3-4 sentences) of the following academic paper, 
        focusing on its key findings, methodology, and implications:
        
        Title: {paper['title']}
        Authors: {', '.join(paper['authors'])}
        Abstract: {paper['abstract'][:800]}...
        Categories: {', '.join(paper['categories'])}
        
        Focus on the most important and practical aspects that would be relevant to someone 
        researching this topic.
        """
        
        result = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Summarize: {paper['title']}"}
            ]
        )
        
        return result.strip()