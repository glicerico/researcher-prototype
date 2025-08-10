"""
Semantic Scholar search node for academic research queries.
Uses the Semantic Scholar Academic Graph API (free, no API key required).
"""

import asyncio
from typing import Dict, Any, List
import requests
from datetime import datetime
from nodes.base_api_search_node import BaseAPISearchNode
from nodes.base import ChatState, logger


class SemanticScholarSearchNode(BaseAPISearchNode):
    """Search node for Semantic Scholar academic papers."""
    
    def __init__(self):
        super().__init__("Semantic Scholar")
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            "User-Agent": "ResearcherPrototype/1.0 (researcher@example.com)"
        }
    
    def validate_config(self) -> bool:
        """Semantic Scholar API is free and doesn't require API keys."""
        return True
    
    async def search(self, query: str, limit: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search Semantic Scholar for academic papers.
        
        Args:
            query: Search query
            limit: Maximum number of results (default 20, max 100)
            
        Returns:
            Dict with search results
        """
        try:
            # Prepare search parameters
            params = {
                "query": query,
                "limit": min(limit, 100),  # API max is 100
                "fields": "paperId,title,abstract,authors,year,citationCount,venue,url,openAccessPdf,fieldsOfStudy"
            }
            
            # Add time filters if scope indicates recent research
            scope_filters = kwargs.get("scope_filters", [])
            if "recent" in scope_filters:
                current_year = datetime.now().year
                params["year"] = f"{current_year-2}-{current_year}"  # Last 3 years
            
            # Make API request
            response = requests.get(
                f"{self.base_url}/paper/search",
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                total_count = data.get("total", len(papers))
                
                return {
                    "success": True,
                    "results": papers,
                    "total_count": total_count,
                    "metadata": {
                        "query_used": query,
                        "api_version": "v1",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Semantic Scholar API error {response.status_code}: {response.text}",
                    "results": [],
                    "total_count": 0
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Semantic Scholar API request timed out",
                "results": [],
                "total_count": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching Semantic Scholar: {str(e)}",
                "results": [],
                "total_count": 0
            }
    
    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format Semantic Scholar results into readable text."""
        papers = raw_results.get("results", [])
        total_count = raw_results.get("total_count", 0)
        
        if not papers:
            return "No academic papers found in Semantic Scholar."
        
        formatted_output = []
        formatted_output.append(f"SEMANTIC SCHOLAR ACADEMIC RESEARCH ({len(papers)} papers shown, {total_count} total):\n")
        
        for i, paper in enumerate(papers[:10], 1):  # Limit to top 10 for readability
            title = paper.get("title", "No title")
            authors = paper.get("authors", [])
            year = paper.get("year", "Unknown year")
            citation_count = paper.get("citationCount", 0)
            venue = paper.get("venue", "Unknown venue")
            abstract = paper.get("abstract", "No abstract available")
            url = paper.get("url", "")
            open_access = paper.get("openAccessPdf", {})
            fields_of_study = paper.get("fieldsOfStudy", [])
            
            # Format authors
            author_names = [author.get("name", "Unknown") for author in authors[:3]]
            authors_str = ", ".join(author_names)
            if len(authors) > 3:
                authors_str += f" et al. ({len(authors)} authors total)"
            
            # Format fields of study
            fields_str = ", ".join(fields_of_study[:3]) if fields_of_study else "General"
            
            formatted_output.append(f"{i}. **{title}** ({year})")
            formatted_output.append(f"   Authors: {authors_str}")
            formatted_output.append(f"   Venue: {venue} | Citations: {citation_count} | Fields: {fields_str}")
            
            if abstract and len(abstract) > 50:
                # Truncate long abstracts
                abstract_preview = abstract[:300] + "..." if len(abstract) > 300 else abstract
                formatted_output.append(f"   Abstract: {abstract_preview}")
            
            if open_access and open_access.get("url"):
                formatted_output.append(f"   📖 Open Access PDF: {open_access['url']}")
            elif url:
                formatted_output.append(f"   🔗 Paper URL: {url}")
            
            formatted_output.append("")  # Empty line between papers
        
        if len(papers) > 10:
            formatted_output.append(f"... and {len(papers) - 10} more papers available")
        
        return "\n".join(formatted_output)


# Create the search node function
semantic_scholar_search_node_instance = SemanticScholarSearchNode()

async def semantic_scholar_search_node(state: ChatState) -> ChatState:
    """Semantic Scholar search node entry point."""
    # Extract scope filters for specialized search
    scope_filters = semantic_scholar_search_node_instance.extract_scope_filters(state)
    
    # Pass scope filters to the search
    modified_state = await semantic_scholar_search_node_instance.execute_search_node(state)
    
    # Override the search method call to pass scope filters
    if "semantic_scholar" in modified_state["module_results"] and modified_state["module_results"]["semantic_scholar"]["success"]:
        # Re-run search with proper scope filters if needed
        refined_query = state.get("workflow_context", {}).get("refined_search_query")
        original_query = modified_state["module_results"]["semantic_scholar"]["query_used"]
        query = refined_query if refined_query else original_query
        
        search_results = await semantic_scholar_search_node_instance.search(
            query, 
            scope_filters=scope_filters
        )
        
        if search_results.get("success", False):
            formatted_content = semantic_scholar_search_node_instance.format_results(search_results)
            modified_state["module_results"]["semantic_scholar"]["result"] = formatted_content
            modified_state["module_results"]["semantic_scholar"]["total_count"] = search_results.get("total_count", 0)
    
    return modified_state