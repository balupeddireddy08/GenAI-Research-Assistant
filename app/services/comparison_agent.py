"""
Comparison agent for the GenAI Research Assistant.
This file implements a specialized agent for comparing multiple research papers,
methods, or concepts, generating structured comparisons and analytical insights.
"""
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

from app.config import settings
from app.utils.llm_utils import get_llm_client, get_completion

# Set up logging
logger = logging.getLogger(__name__)

class PaperComparisonAgent:
    """Agent specifically for comparing multiple papers or research methods"""
    
    def __init__(self, settings):
        self.settings = settings
        self.llm_client = get_llm_client(settings)
    
    async def compare_papers(self, papers: List[Dict[str, Any]], comparison_criteria: str) -> Dict[str, Any]:
        """
        Compare multiple papers based on specified criteria
        
        Args:
            papers: List of paper data dictionaries
            comparison_criteria: Specific aspects to compare
            
        Returns:
            Dictionary containing structured comparison results
        """
        logger.info(f"Comparing {len(papers)} papers on criteria: {comparison_criteria}")
        
        # Extract key information from each paper
        paper_data = []
        for paper in papers:
            paper_data.append({
                "title": paper.get("title", "Unknown Title"),
                "authors": paper.get("authors", []),
                "summary": paper.get("summary", ""),
                "abstract": paper.get("abstract", ""),
                "key_findings": paper.get("relevance_assessment", {}).get("key_insights", []),
                "arxiv_id": paper.get("arxiv_id", ""),
                "categories": paper.get("categories", []),
                "url": paper.get("link", paper.get("url", ""))
            })
        
        prompt = f"""
        Compare the following research papers with respect to: {comparison_criteria}
        
        PAPERS:
        {json.dumps(paper_data, indent=2)}
        
        Provide a comprehensive comparison addressing:
        1. Methodological differences
        2. Results and performance metrics
        3. Theoretical foundations
        4. Practical applications
        5. Limitations and strengths
        
        Structure as a JSON with:
        - comparison_summary: Overall comparison (2-3 paragraphs)
        - comparison_table: Table comparing key aspects
        - key_differences: Array of major distinctions
        - synthesis: Which approaches work best for which scenarios
        """
        
        try:
            result = await get_completion(
                self.llm_client,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Compare these papers on {comparison_criteria}"}
                ],
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_result = json.loads(result)
                logger.info(f"Successfully generated comparison for {len(papers)} papers")
                return parsed_result
            except json.JSONDecodeError:
                logger.error("Failed to parse comparison result as JSON")
                return {
                    "comparison_summary": result[:1000],  # Use the raw text as fallback
                    "error": "Could not generate structured comparison"
                }
        except Exception as e:
            logger.error(f"Error in paper comparison: {str(e)}")
            return {
                "comparison_summary": "Could not generate structured comparison due to an error.",
                "error": str(e)
            }
    
    async def compare_research_methods(self, user_query: str, methods: List[str], papers_by_method: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Compare multiple research methods using papers found for each method
        
        Args:
            user_query: The original user query
            methods: List of method names to compare
            papers_by_method: Dictionary mapping method names to lists of papers
            
        Returns:
            Dictionary containing structured comparison results
        """
        logger.info(f"Comparing {len(methods)} research methods: {', '.join(methods)}")
        
        # Prepare method summaries from their respective papers
        method_summaries = {}
        for method in methods:
            method_papers = papers_by_method.get(method, [])
            if not method_papers:
                method_summaries[method] = {"description": f"No papers found for {method}"}
                continue
                
            # Summarize each method based on its papers
            paper_descriptions = []
            for paper in method_papers[:3]:  # Limit to 3 papers per method
                paper_descriptions.append({
                    "title": paper.get("title", "Unknown Title"),
                    "summary": paper.get("summary", paper.get("abstract", "No summary available"))[:300],
                    "key_points": paper.get("relevance_assessment", {}).get("key_insights", [])
                })
                
            method_summaries[method] = {
                "papers": paper_descriptions,
                "paper_count": len(method_papers)
            }
        
        prompt = f"""
        Compare these research methods based on the user's query:
        
        USER QUERY: {user_query}
        
        METHODS TO COMPARE:
        {json.dumps(methods, indent=2)}
        
        PAPERS FOR EACH METHOD:
        {json.dumps(method_summaries, indent=2)}
        
        Provide a comprehensive comparison that addresses:
        1. Core principles of each method
        2. Strengths and weaknesses
        3. Applications and use cases
        4. Performance characteristics
        5. Implementation considerations
        
        Structure as a JSON with:
        - method_descriptions: Object with descriptions of each method
        - comparison_table: Table with methods as columns and comparison aspects as rows
        - key_differences: Array of major distinctions
        - recommendations: When to use each method
        - method_rankings: Object with rankings by different criteria (efficiency, accuracy, etc.)
        """
        
        try:
            result = await get_completion(
                self.llm_client,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Compare these research methods: {', '.join(methods)}"}
                ],
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_result = json.loads(result)
                logger.info(f"Successfully generated method comparison for {len(methods)} methods")
                return parsed_result
            except json.JSONDecodeError:
                logger.error("Failed to parse method comparison result as JSON")
                return {
                    "comparison_summary": result[:1000],  # Use the raw text as fallback
                    "error": "Could not generate structured comparison"
                }
        except Exception as e:
            logger.error(f"Error in method comparison: {str(e)}")
            return {
                "comparison_summary": "Could not generate method comparison due to an error.",
                "error": str(e)
            }
    
    async def explain_concept(self, concept: str, related_papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Explain a research concept using related papers
        
        Args:
            concept: The concept to explain
            related_papers: Papers related to the concept
            
        Returns:
            Dictionary containing the explanation and related insights
        """
        logger.info(f"Generating explanation for concept: {concept}")
        
        # Extract relevant passages from papers
        concept_context = []
        for paper in related_papers:
            if concept.lower() in paper.get('title', '').lower() or concept.lower() in paper.get('abstract', '').lower():
                concept_context.append({
                    "title": paper.get("title", "Unknown Title"),
                    "excerpt": paper.get("abstract", "")[:300],
                    "authors": paper.get("authors", []),
                    "url": paper.get("link", paper.get("url", ""))
                })
        
        prompt = f"""
        Explain this academic concept in simple terms:
        
        CONCEPT: {concept}
        
        CONTEXT FROM ACADEMIC PAPERS:
        {json.dumps(concept_context, indent=2)}
        
        Your explanation should:
        1. Start with a simple definition anyone can understand
        2. Explain why this concept matters and its applications
        3. Use analogies or examples to illustrate the concept
        4. Mention any key debates or developments in this area
        5. Use plain language while being scientifically accurate
        
        Structure as a JSON with:
        - simple_definition: A one-sentence definition in simple terms
        - detailed_explanation: A more thorough explanation (2-3 paragraphs)
        - real_world_examples: 2-3 concrete examples of the concept in action
        - key_papers: References to seminal or important papers in this area
        - related_concepts: Other concepts that are closely related
        """
        
        try:
            result = await get_completion(
                self.llm_client,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Explain {concept} in simple terms"}
                ],
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_result = json.loads(result)
                logger.info(f"Successfully generated explanation for concept: {concept}")
                return parsed_result
            except json.JSONDecodeError:
                logger.error("Failed to parse concept explanation as JSON")
                return {
                    "simple_definition": concept,
                    "detailed_explanation": result[:1000],  # Use the raw text as fallback
                    "error": "Could not generate structured explanation"
                }
        except Exception as e:
            logger.error(f"Error explaining concept: {str(e)}")
            return {
                "simple_definition": concept,
                "detailed_explanation": "Could not generate explanation due to an error.",
                "error": str(e)
            } 