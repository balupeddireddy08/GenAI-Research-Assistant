"""
Synthesis agent for the GenAI Research Assistant.
This file implements a specialized agent responsible for combining information from
other agents, formatting results, extracting sources, and generating comprehensive
responses to user queries.
"""
from typing import Dict, Any, List, Tuple, Optional
import json
from datetime import datetime

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion


class SynthesisAgent:
    """
    Agent responsible for synthesizing information from other agents into a coherent response.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
    
    async def synthesize(
        self, 
        user_message: str, 
        agent_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Synthesize the results from different agents into a coherent response.
        
        Args:
            user_message: The user's original message
            agent_results: Results from various agents (search, academic, etc.)
            conversation_history: Previous messages in the conversation
            
        Returns:
            Tuple containing:
            - The synthesized response text
            - Metadata about the synthesis process
        """
        # Extract and format the relevant information from agent results
        formatted_results = self._format_agent_results(agent_results)
        
        # Generate a comprehensive response based on all available information
        response_content = await self._generate_comprehensive_response(
            user_message, 
            formatted_results, 
            conversation_history
        )
        
        # Extract sources and citations from the results
        sources = self._extract_sources(agent_results)
        
        # Generate metadata about the synthesis process
        metadata = {
            "sources": sources,
            "synthesis_timestamp": datetime.now().isoformat(),
            "agent_results_summary": self._summarize_agent_results(agent_results)
        }
        
        return response_content, metadata
    
    def _format_agent_results(self, agent_results: Dict[str, Any]) -> str:
        """
        Format the results from various agents into a structured text format.
        """
        formatted_text = ""
        
        # Process search agent results
        search_results = [r for k, r in agent_results.items() if k.startswith("search_agent")]
        if search_results:
            formatted_text += "### Web Search Results\n\n"
            for i, result in enumerate(search_results):
                formatted_text += f"Search Query: {result.get('query', 'N/A')}\n\n"
                
                for j, item in enumerate(result.get('results', [])[:3]):  # Limit to top 3 results
                    formatted_text += f"Result {j+1}: {item.get('title', 'No title')}\n"
                    if 'content' in item:
                        formatted_text += f"Content: {item['content']}\n"
                    if 'relevance_assessment' in item:
                        formatted_text += f"Relevance: {item['relevance_assessment'].get('score', 'N/A')} - {item['relevance_assessment'].get('reason', 'N/A')}\n"
                    formatted_text += "\n"
        
        # Process academic agent results
        academic_results = [r for k, r in agent_results.items() if k.startswith("academic_agent")]
        if academic_results:
            formatted_text += "### Academic Paper Results\n\n"
            for i, result in enumerate(academic_results):
                formatted_text += f"Search Query: {result.get('query', 'N/A')}\n\n"
                
                for j, paper in enumerate(result.get('results', [])[:3]):  # Limit to top 3 papers
                    formatted_text += f"Paper {j+1}: {paper.get('title', 'No title')}\n"
                    formatted_text += f"Authors: {', '.join(paper.get('authors', ['Unknown']))}\n"
                    formatted_text += f"Abstract: {paper.get('abstract', 'No abstract')[:300]}...\n"
                    if 'summary' in paper:
                        formatted_text += f"Summary: {paper['summary']}\n"
                    if 'relevance_assessment' in paper:
                        formatted_text += f"Relevance: {paper['relevance_assessment'].get('score', 'N/A')} - {paper['relevance_assessment'].get('reason', 'N/A')}\n"
                        if 'key_insights' in paper['relevance_assessment']:
                            formatted_text += "Key Insights:\n"
                            for insight in paper['relevance_assessment']['key_insights']:
                                formatted_text += f"- {insight}\n"
                    formatted_text += "\n"
        
        return formatted_text
    
    def _extract_sources(self, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and format source information from agent results.
        """
        sources = []
        
        # Extract web search sources
        for k, result in agent_results.items():
            if k.startswith("search_agent") and 'results' in result:
                for item in result['results']:
                    if 'title' in item and 'url' in item:
                        sources.append({
                            "title": item['title'],
                            "url": item['url'],
                            "type": "web",
                            "relevance": item.get('relevance_assessment', {}).get('score', 0.5) if 'relevance_assessment' in item else 0.5
                        })
        
        # Extract academic paper sources
        for k, result in agent_results.items():
            if k.startswith("academic_agent") and 'results' in result:
                for paper in result['results']:
                    if 'title' in paper:
                        # Always include the main link (abstract page)
                        if 'link' in paper:
                            sources.append({
                                "title": paper['title'],
                                "url": paper['link'],
                                "authors": paper.get('authors', []),
                                "published_date": paper.get('published_date'),
                                "type": "academic",
                                "arxiv_id": paper.get('arxiv_id'),
                                "relevance": paper.get('relevance_assessment', {}).get('score', 0.5) if 'relevance_assessment' in paper else 0.5,
                                "description": paper.get('abstract', '')[:200] + '...' if paper.get('abstract') else None
                            })
                        
                        # Also include the PDF link if available
                        if 'pdf_link' in paper:
                            sources.append({
                                "title": f"[PDF] {paper['title']}",
                                "url": paper['pdf_link'],
                                "authors": paper.get('authors', []),
                                "published_date": paper.get('published_date'),
                                "type": "academic_pdf",
                                "arxiv_id": paper.get('arxiv_id'),
                                "relevance": paper.get('relevance_assessment', {}).get('score', 0.5) if 'relevance_assessment' in paper else 0.5
                            })
        
        # Sort sources by relevance
        sources.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        
        return sources
    
    def _summarize_agent_results(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of what each agent found.
        """
        summary = {}
        
        for key, result in agent_results.items():
            if key.startswith("search_agent"):
                summary[key] = {
                    "query": result.get('query', 'N/A'),
                    "result_count": len(result.get('results', [])),
                    "top_result": result.get('results', [{}])[0].get('title', 'None') if result.get('results') else 'None'
                }
            elif key.startswith("academic_agent"):
                summary[key] = {
                    "query": result.get('query', 'N/A'),
                    "paper_count": len(result.get('results', [])),
                    "top_paper": result.get('results', [{}])[0].get('title', 'None') if result.get('results') else 'None'
                }
        
        return summary
    
    async def _generate_comprehensive_response(
        self, 
        user_message: str, 
        formatted_results: str, 
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate a comprehensive response based on all available information.
        """
        # Extract recent conversation context (limit to 5 most recent messages)
        recent_messages = conversation_history[-5:] if len(conversation_history) > 0 else []
        recent_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        # Analyze type of request to tailor the response approach
        is_academic_analysis = any(term in user_message.lower() for term in 
                               ['analyze', 'analysis', 'evaluate', 'review', 'critique', 'summarize', 'summary'])
        is_comparison = any(term in user_message.lower() for term in 
                           ['compare', 'contrast', 'versus', 'vs', 'difference', 'similarities'])
        
        # Determine if sources were found
        has_sources = "Paper" in formatted_results or "Result" in formatted_results
        
        # Handle academic analysis requests (papers, studies, research)
        if is_academic_analysis or is_comparison:
            prompt = f"""
            You are an expert academic research analyst providing detailed analysis of scholarly works.
            
            USER'S REQUEST: {user_message}
            
            RECENT CONVERSATION CONTEXT:
            {recent_context}
            
            RELEVANT RESEARCH PAPERS AND SOURCES:
            {formatted_results}
            
            CRITICAL INSTRUCTION: You MUST ONLY use and cite the papers and sources found in the search results above.
            DO NOT cite papers or sources that aren't in the search results.
            
            Based on the available research papers and sources, provide the analysis requested by the user.
            
            IMPORTANT INSTRUCTIONS:
            
            1. If relevant papers were found in the search results, analyze those papers
               in detail to answer the user's question. Prioritize seminal or foundational papers in the field.
            
            2. If no relevant papers were found for the specific topic, clearly state this limitation and note that
               you can only analyze based on the available papers.
               
            3. When conducting academic analysis:
               - Compare and contrast methodologies when appropriate
               - Examine training or experimental approaches
               - Analyze performance differences and metrics
               - Discuss strengths and limitations
               - Consider implications and applications
            
            4. Structure your response with appropriate academic analysis sections.
            
            5. MOST IMPORTANT: YOU MUST ALWAYS CITE SOURCES PROPERLY. Every major claim should be supported by a citation
               to one of the papers from the search results. Format citations as links to the paper URLs, like this:
               [Paper Title](paper_url)
            
            FORMAT GUIDELINES:
            1. Start with a main heading (using # syntax) that summarizes the topic
            2. Use proper subheadings (using ## syntax) for different sections
            3. Use bullet points (using * or - syntax) for listing key points
            4. ALWAYS provide a "Sources Used" section at the end listing all papers you referenced
            
            Remember: If you have no sources from the search results, acknowledge this limitation and only provide
            general information while stating the need for specific research papers for a more detailed analysis.
            """
        else:
            # General prompt for other types of queries
            prompt = f"""
            You are a helpful research assistant providing information based on search results and academic papers.
            
            USER'S QUESTION: {user_message}
            
            RECENT CONVERSATION CONTEXT:
            {recent_context}
            
            INFORMATION FROM VARIOUS SOURCES:
            {formatted_results}
            
            CRITICAL INSTRUCTION: You MUST ONLY use and cite the papers and sources found in the search results above.
            DO NOT cite papers or sources that aren't in the search results.
            
            Based on the above information, provide a comprehensive, well-structured response to the user's question.
            
            IMPORTANT: You MUST format your response using the following structure:
            1. Start with a main heading (using # syntax) that summarizes the topic
            2. Add relevant subheadings (using ## syntax) to organize different aspects or sections
            3. Use bullet points (using * or - syntax) for listing items, features, or key points
            4. Include direct links to sources when citing specific information
            5. ALWAYS include a "Sources Used" section at the end
            
            Make sure to:
            1. Directly address the user's specific question and intent
            2. ONLY synthesize information from the sources provided
            3. Cite sources when providing specific information using formats like: [Source Title](URL)
            4. Structure your response logically with clear sections
            5. Acknowledge limitations or gaps in the available information
            6. Use an authoritative but conversational tone
            
            If the search results don't provide relevant information to answer the question, CLEARLY STATE THIS
            at the beginning of your response, and then provide only general information while acknowledging
            the limitations.
            """
        
        # Generate the response
        response = await get_completion(
            self.llm_client,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        # Check if the response includes any source citations
        has_citation_links = '[' in response and '](' in response
        
        # Add source usage note if relevant sources were found but no citations were included
        if has_sources and not has_citation_links and formatted_results.strip():
            response += "\n\n---\n**Note:** This response was generated based on academic sources, but specific citations couldn't be formatted properly."
        
        return response