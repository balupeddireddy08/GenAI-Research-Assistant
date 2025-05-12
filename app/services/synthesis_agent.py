"""
Synthesis agent for the GenAI Research Assistant.
This file implements a specialized agent responsible for combining information from
other agents, formatting results, extracting sources, and generating comprehensive
responses to user queries.
"""
from typing import Dict, Any, List, Tuple, Optional
import json
import logging
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
        self.logger = logging.getLogger(__name__)
    
    async def synthesize(
        self, 
        user_message: str, 
        agent_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Synthesize a comprehensive response from multiple agent results
        
        Args:
            user_message: The original user message
            agent_results: Dictionary of results from different agents
            conversation_history: List of previous conversation turns
            
        Returns:
            Dictionary containing the synthesized response and metadata
        """
        self.logger.info("Synthesizing response from agent results")
        
        # Extract papers and other relevant information from agent results
        papers = []
        web_results = []
        comparisons = []
        explanations = []
        error_messages = []
        
        # Process agent results to extract key information
        for agent_id, result in agent_results.items():
            # Skip empty results
            if not result:
                continue
                
            # Extract papers from academic agent results
            if "papers" in result:
                # Check if these papers came from a fallback to web search
                if result.get("used_fallback"):
                    # Mark these papers specially
                    for paper in result["papers"]:
                        if paper.get("source") == "web_search":
                            web_results.append(paper)
                        else:
                            papers.append(paper)
                else:
                    papers.extend(result["papers"])
            
            # Extract web search results
            if "results" in result:
                for item in result["results"]:
                    if "title" in item and "content" in item:
                        web_results.append(item)
            
            # Extract comparison results
            if "comparison_summary" in result:
                comparisons.append(result)
                
            # Extract concept explanations
            if "explanation" in result:
                explanations.append(result)
                
            # Track any errors
            if "error" in result:
                error_messages.append(result["error"])

        # Determine information sources for prompt construction
        has_academic_papers = len(papers) > 0
        has_web_results = len(web_results) > 0
        has_comparisons = len(comparisons) > 0
        has_explanations = len(explanations) > 0
        
        # Track metadata about sources used
        sources_used = {
            "academic_papers": has_academic_papers,
            "web_results": has_web_results,
            "comparisons": has_comparisons,
            "explanations": has_explanations,
            "paper_count": len(papers),
            "web_result_count": len(web_results)
        }
        
        # Prepare source tracking for citation
        sources = []
        
        # Add academic papers as sources
        if papers:
            for i, paper in enumerate(papers):
                source_info = {
                    "id": f"paper_{i+1}",
                    "type": "academic",
                    "title": paper.get("title", "Unknown Title"),
                    "url": paper.get("url", paper.get("link", "")),
                    "description": paper.get("abstract", paper.get("summary", "")),
                    "authors": paper.get("authors", []),
                    "arxiv_id": paper.get("arxiv_id", ""),
                    "year": paper.get("year", "Unknown"),
                    "source_operation": "search_papers"
                }
                sources.append(source_info)
        
        # Add web results as sources
        if web_results:
            for i, result in enumerate(web_results):
                source_info = {
                    "id": f"web_{i+1}",
                    "type": "web",
                    "title": result.get("title", "Unknown Title"),
                    "url": result.get("url", result.get("link", "")),
                    "description": result.get("content", result.get("summary", "")),
                    "source_operation": "search_web"
                }
                sources.append(source_info)
        
        # Build a structured representation of all collected information
        collected_info = {
            "papers": [self._extract_paper_data(paper) for paper in papers],
            "web_results": [self._extract_web_result(result) for result in web_results],
            "comparisons": comparisons,
            "explanations": explanations,
            "errors": error_messages if error_messages else None
        }
        
        # Build the system prompt based on available information
        prompt = self._build_synthesis_prompt(user_message, collected_info, conversation_history)
        
        # Generate the response
        try:
            response = await get_completion(
                self.llm_client,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Post-process the response to fix markdown table formatting
            processed_response = self._fix_markdown_tables(response)
            
            return {
                "response": processed_response,
                "sources_used": sources_used,
                "sources": sources,  # Add explicit sources list
                "source_count": len(sources),  # Add count for frontend display
                "citation_count": len(papers) + len(web_results),
                "model": self.settings.PRIMARY_LLM
            }
        except Exception as e:
            self.logger.error(f"Error in synthesis: {str(e)}")
            return {
                "response": f"I encountered an error while synthesizing the research information: {str(e)}",
                "sources_used": sources_used,
                "sources": sources,  # Include sources even in error case
                "source_count": len(sources),
                "error": str(e)
            }
    
    def _extract_paper_data(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized data from a paper object"""
        return {
            "title": paper.get("title", "Unknown Title"),
            "authors": paper.get("authors", []),
            "summary": paper.get("summary", paper.get("abstract", "")),
            "year": paper.get("year", "Unknown"),
            "url": paper.get("url", paper.get("link", "")),
            "source": paper.get("source", "academic"),
            "key_insights": paper.get("relevance_assessment", {}).get("key_insights", [])
        }
        
    def _extract_web_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized data from a web search result"""
        return {
            "title": result.get("title", "Unknown Title"),
            "content": result.get("content", result.get("summary", "")),
            "url": result.get("url", ""),
            "source": "web",
            "relevance": result.get("relevance_assessment", {}).get("score", result.get("score", 0.5))
        }
    
    def _build_synthesis_prompt(
        self, 
        user_message: str, 
        collected_info: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Build a detailed prompt for response synthesis based on available information
        """
        papers = collected_info["papers"]
        web_results = collected_info["web_results"]
        comparisons = collected_info["comparisons"]
        explanations = collected_info["explanations"]
        errors = collected_info["errors"]
        
        # Start with the base prompt
        prompt = f"""You are an academic research assistant helping with the following query:

"{user_message}"

Your task is to synthesize a comprehensive, accurate response using the information provided.
"""

        # Add context about available information sources
        source_context = []
        if papers:
            source_context.append(f"{len(papers)} academic papers")
        if web_results:
            source_context.append(f"{len(web_results)} web search results")
        if comparisons:
            source_context.append(f"{len(comparisons)} comparative analyses")
        if explanations:
            source_context.append(f"{len(explanations)} concept explanations")
            
        if source_context:
            prompt += f"\nThe following information has been collected: {', '.join(source_context)}.\n"
            
            # Add a note about fallback search if applicable
            if len(papers) == 0 and len(web_results) > 0:
                prompt += "\nNOTE: No academic papers were found, so web search was used as a fallback to provide information.\n"
        
        # Add papers section if available
        if papers:
            prompt += "\n## ACADEMIC PAPERS\n"
            for i, paper in enumerate(papers[:10]):  # Limit to 10 papers to avoid context overflow
                prompt += f"\nPAPER {i+1}:\n"
                prompt += f"Title: {paper['title']}\n"
                if paper.get("authors"):
                    prompt += f"Authors: {', '.join(paper['authors'][:3])}{' et al.' if len(paper['authors']) > 3 else ''}\n"
                if paper.get("year"):
                    prompt += f"Year: {paper['year']}\n"
                if paper.get("url"):
                    prompt += f"URL: {paper['url']}\n"
                prompt += f"Summary: {paper['summary'][:500]}...\n"
                if paper.get("key_insights"):
                    prompt += "Key insights:\n"
                    for j, insight in enumerate(paper['key_insights'][:5]):  # Limit to 5 insights
                        prompt += f"- {insight}\n"
        
        # Add web results if available
        if web_results:
            prompt += "\n## WEB SEARCH RESULTS\n"
            if len(papers) == 0:
                prompt += "(Used as fallback since no academic papers were found)\n"
            for i, result in enumerate(web_results[:10]):  # Limit to 10 results
                prompt += f"\nRESULT {i+1}:\n"
                prompt += f"Title: {result['title']}\n"
                if result.get("url"):
                    prompt += f"URL: {result['url']}\n"
                prompt += f"Content: {result['content'][:500]}...\n"
        
        # Add comparison results if available
        if comparisons:
            prompt += "\n## COMPARATIVE ANALYSES\n"
            for i, comparison in enumerate(comparisons):
                prompt += f"\nCOMPARISON {i+1}:\n"
                if "comparison_summary" in comparison:
                    prompt += f"Summary: {comparison['comparison_summary'][:1000]}...\n"
                if "method_descriptions" in comparison:
                    prompt += "Method descriptions:\n"
                    for method, desc in comparison["method_descriptions"].items():
                        prompt += f"- {method}: {str(desc)[:300]}...\n"
                if "key_differences" in comparison and isinstance(comparison["key_differences"], list):
                    prompt += "Key differences:\n"
                    for diff in comparison["key_differences"][:5]:  # Limit to 5 differences
                        prompt += f"- {diff}\n"
        
        # Add explanations if available
        if explanations:
            prompt += "\n## CONCEPT EXPLANATIONS\n"
            for i, explanation in enumerate(explanations):
                prompt += f"\nEXPLANATION {i+1}:\n"
                if "explanation" in explanation:
                    prompt += f"{explanation['explanation'][:1000]}...\n"
        
        # Add info about errors if any occurred
        if errors:
            prompt += "\n## SEARCH LIMITATIONS\n"
            prompt += "Note: Some information sources had issues:\n"
            for error in errors[:3]:  # Limit to first 3 errors
                prompt += f"- {error}\n"
            
        # Add instructions for synthesis
        prompt += """
## RESPONSE GUIDELINES

1. Synthesize a comprehensive response that directly addresses the user's query
2. Use the most relevant information from the provided sources
3. Combine academic and web-based information appropriately
4. Clearly identify any areas where information is limited or unavailable
5. Use an academic, informative style with precise terminology
6. Structure the response with clear sections and logical flow
7. If relevant to the query, include a proper markdown comparison table that looks like this:

```
| Feature | Option A | Option B |
|---------|----------|----------|
| Feature 1 | Value A1 | Value B1 |
| Feature 2 | Value A2 | Value B2 |
```

IMPORTANT: When formatting comparison tables, ensure they render correctly:
- Each row MUST be on its own line - do not put the entire table on a single line
- Begin and end each line with a vertical bar (|)
- Ensure the header separator row (|---|---|---|) is on its own line
- Align columns consistently for readability
- Make sure each row has the same number of columns
- Avoid using | characters within cell text as they break table formatting
- Add an empty line before and after the table

8. When citing sources, use the following format: 
   - For academic papers: [Source: "Title"]
   - For web results: [Source: "Title"]
   - Make sure to cite sources consistently throughout your response
   - DO NOT use placeholder citations like [Unknown agent]

9. When comparing research methods or topics, clearly highlight key similarities and differences

Your response should be thorough yet concise, focused on addressing the user's specific query.
Use objective, evidence-based language and avoid speculation where information is limited.
"""

        return prompt
    
    def _fix_markdown_tables(self, text: str) -> str:
        """
        Ensure markdown tables have proper line breaks and formatting.
        
        Args:
            text: The original response text
            
        Returns:
            Text with properly formatted markdown tables
        """
        import re
        
        # First check if the text already contains properly formatted tables with newlines
        if re.search(r'\|\s*\n\s*\|', text):
            # If so, no need for extensive processing
            return text
        
        # Find markdown table patterns
        # This pattern looks for sequences starting with | and containing multiple | characters
        # that might represent a table
        table_pattern = r'(\|[^\n]+\|[^\n]+\|[^\n]*)'
        
        # Function to process each found table
        def process_table(match):
            table_text = match.group(0)
            
            # Skip if it already has newlines
            if '\n' in table_text:
                return table_text
                
            # Split the table into rows by detecting complete row patterns
            # A row starts with | and ends with | with content in between
            row_pattern = r'\|[^|]*(?:\|[^|]*)+\|'
            rows = re.findall(row_pattern, table_text)
            
            if not rows or len(rows) < 2:
                # Not enough rows for a proper table
                return table_text
            
            # Check if we have a proper table structure (header + separator + data rows)
            header_row = rows[0]
            
            # Try to identify or create a separator row
            separator_row = ""
            if len(rows) > 1:
                if re.match(r'\|[\s-:|]+\|', rows[1]):
                    # Second row looks like a separator
                    separator_row = rows[1]
                else:
                    # Create a separator row based on the header
                    columns = header_row.count('|') - 1
                    separator_row = '|' + '---|' * columns
            else:
                # Create a separator row based on the header
                columns = header_row.count('|') - 1
                separator_row = '|' + '---|' * columns
            
            # Reconstruct the table with proper formatting
            if len(rows) <= 2:
                # Only header row found, create a minimal table
                formatted_table = header_row + '\n' + separator_row
            else:
                data_rows = rows[1:] if not re.match(r'\|[\s-:|]+\|', rows[1]) else rows[2:]
                formatted_table = header_row + '\n' + separator_row + '\n' + '\n'.join(data_rows)
            
            # Ensure the table has proper spacing
            return '\n\n' + formatted_table + '\n\n'
        
        # Replace all tables in the text
        processed_text = re.sub(table_pattern, process_table, text)
        
        # If the text contains table-like content but our regex didn't match properly,
        # try a more aggressive approach with a single pass through the text
        if '|' in processed_text and not re.search(r'\|\s*\n\s*\|', processed_text):
            lines = processed_text.split('\n')
            table_lines = []
            in_table = False
            result_lines = []
            
            for line in lines:
                # Detect potential table lines (containing multiple | characters)
                if line.count('|') >= 2:
                    if not in_table:
                        in_table = True
                        # Add an empty line before table if not already there
                        if result_lines and result_lines[-1]:
                            result_lines.append('')
                    table_lines.append(line)
                else:
                    if in_table:
                        # Process the collected table lines
                        if len(table_lines) >= 1:
                            # Add header row
                            result_lines.append(table_lines[0])
                            
                            # Check if there's a separator row, add one if not
                            if len(table_lines) > 1 and re.match(r'^\s*\|[\s-:|]+\|\s*$', table_lines[1]):
                                result_lines.append(table_lines[1])
                            else:
                                # Create a separator row
                                columns = table_lines[0].count('|') - 1
                                result_lines.append('|' + '---|' * columns)
                            
                            # Add remaining rows
                            if len(table_lines) > 1:
                                start_idx = 2 if re.match(r'^\s*\|[\s-:|]+\|\s*$', table_lines[1]) else 1
                                for table_line in table_lines[start_idx:]:
                                    result_lines.append(table_line)
                            
                            # Add an empty line after the table
                            result_lines.append('')
                        
                        table_lines = []
                        in_table = False
                    
                    result_lines.append(line)
            
            # Handle case where table is at the end of the text
            if in_table and table_lines:
                # Process the collected table lines
                if len(table_lines) >= 1:
                    # Add header row
                    result_lines.append(table_lines[0])
                    
                    # Check if there's a separator row, add one if not
                    if len(table_lines) > 1 and re.match(r'^\s*\|[\s-:|]+\|\s*$', table_lines[1]):
                        result_lines.append(table_lines[1])
                    else:
                        # Create a separator row
                        columns = table_lines[0].count('|') - 1
                        result_lines.append('|' + '---|' * columns)
                    
                    # Add remaining rows
                    if len(table_lines) > 1:
                        start_idx = 2 if re.match(r'^\s*\|[\s-:|]+\|\s*$', table_lines[1]) else 1
                        for table_line in table_lines[start_idx:]:
                            result_lines.append(table_line)
                    
                    # Add an empty line after the table
                    result_lines.append('')
            
            processed_text = '\n'.join(result_lines)
        
        return processed_text