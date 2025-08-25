"""
OpenAlex search node for academic research queries.
Uses the OpenAlex API (free, no API key required).
OpenAlex is an open academic database with comprehensive coverage.
"""

import asyncio
from typing import Dict, Any, List
import requests
from datetime import datetime
from nodes.base_api_search_node import BaseAPISearchNode
from nodes.base import ChatState, logger
from config import SEARCH_RESULTS_LIMIT
import config

# Fixed result key for this search source
RESULT_KEY = "academic_search"


class OpenAlexSearchNode(BaseAPISearchNode):
    """Search node for OpenAlex academic papers."""
    
    def __init__(self):
        super().__init__("OpenAlex")
        self.base_url = "https://api.openalex.org"
        self.headers = {
            "User-Agent": "ResearcherPrototype/1.0 (mailto:researcher@example.com)"
        }
    
    def validate_config(self) -> bool:
        """OpenAlex API is free and doesn't require API keys."""
        return True
    
    async def search(self, query: str, limit: int = SEARCH_RESULTS_LIMIT, **kwargs) -> Dict[str, Any]:
        """
        Search OpenAlex for academic papers.
        
        Args:
            query: Search query
            limit: Maximum number of results (default from SEARCH_RESULTS_LIMIT, max 200)
            
        Returns:
            Dict with search results
        """
        try:
            # Use targeted search strategy for better relevance:
            # 1. First try title search for most relevant results
            # 2. If insufficient results, complement with abstract search
            # This avoids the noise from general fulltext search
            
            # Prepare search parameters for title search
            params = {
                "filter": f"title.search:{query},type:article,is_retracted:false",
                "per-page": min(limit, 200),  # API max is 200
                "sort": "relevance_score:desc",
                # Specify which fields to include in response
                "select": "id,title,display_name,publication_year,publication_date,doi,cited_by_count,abstract_inverted_index,authorships,primary_location,open_access,type"
            }
            
            # Make API request for title search
            response = requests.get(
                f"{self.base_url}/works",
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                title_works = data.get("results", [])
                title_count = data.get("meta", {}).get("count", len(title_works))
                
                # If title search yields few results (less than half of limit), try abstract search too
                if title_count < limit // 2 and title_count < 10:
                    # Try abstract search to supplement results
                    abstract_params = {
                        "filter": f"abstract.search:{query},type:article,is_retracted:false",
                        "per-page": min(limit - len(title_works), 200),
                        "sort": "relevance_score:desc",
                        "select": "id,title,display_name,publication_year,publication_date,doi,cited_by_count,abstract_inverted_index,authorships,primary_location,open_access,type"
                    }
                    
                    try:
                        abstract_response = requests.get(
                            f"{self.base_url}/works",
                            params=abstract_params,
                            headers=self.headers,
                            timeout=30
                        )
                        
                        if abstract_response.status_code == 200:
                            abstract_data = abstract_response.json()
                            abstract_works = abstract_data.get("results", [])
                            
                            # Deduplicate by ID and combine results
                            title_ids = {work.get("id") for work in title_works}
                            unique_abstract_works = [work for work in abstract_works if work.get("id") not in title_ids]
                            
                            works = title_works + unique_abstract_works
                            total_count = title_count + abstract_data.get("meta", {}).get("count", 0)
                        else:
                            # Fall back to title results only
                            works = title_works
                            total_count = title_count
                    except Exception:
                        # Fall back to title results only on any error
                        works = title_works
                        total_count = title_count
                else:
                    # Title search gave sufficient results
                    works = title_works
                    total_count = title_count
                
                return {
                    "success": True,
                    "results": works,
                    "total_count": total_count,
                    "metadata": {
                        "query_used": query,
                        "api_version": "openalex",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "OpenAlex rate limited (429). Please try again later.",
                    "results": [],
                    "total_count": 0
                }
            else:
                return {
                    "success": False,
                    "error": f"OpenAlex API error {response.status_code}: {response.text}",
                    "results": [],
                    "total_count": 0
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "OpenAlex API request timed out",
                "results": [],
                "total_count": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching OpenAlex: {str(e)}",
                "results": [],
                "total_count": 0
            }
    
    def _reconstruct_abstract(self, abstract_inverted_index: Dict[str, List[int]]) -> str:
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not abstract_inverted_index:
            return ""
        
        try:
            # Create list of (position, word) pairs
            word_positions = []
            for word, positions in abstract_inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join words
            word_positions.sort(key=lambda x: x[0])
            abstract = " ".join([word for pos, word in word_positions])
            
            return abstract
        except Exception:
            return ""
    
    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format OpenAlex results into readable text."""
        works = raw_results.get("results", [])
        total_count = raw_results.get("total_count", 0)
        
        if not works:
            return "No academic papers found in OpenAlex."
        
        formatted_output = []
        formatted_output.append(f"OPENALEX ACADEMIC RESEARCH ({len(works)} results shown, of {total_count:,} available):\n")
        
        for i, work in enumerate(works[:10], 1):  # Limit to top 10 for readability
            title = work.get("title", work.get("display_name", "No title"))
            year = work.get("publication_year", "Unknown year")
            citation_count = work.get("cited_by_count", 0)
            doi = work.get("doi", "")
            abstract_inverted = work.get("abstract_inverted_index", {})
            authorships = work.get("authorships", [])
            primary_location = work.get("primary_location", {})
            open_access = work.get("open_access", {})
            
            # Format authors
            author_names = []
            for authorship in authorships[:3]:  # First 3 authors
                author = authorship.get("author", {})
                name = author.get("display_name", "Unknown")
                if name != "Unknown":
                    author_names.append(name)
            
            authors_str = ", ".join(author_names)
            if len(authorships) > 3:
                authors_str += f" et al. ({len(authorships)} authors total)"
            elif not authors_str:
                authors_str = "Unknown authors"
            
            # Get venue information
            venue = "Unknown venue"
            if primary_location:
                source = primary_location.get("source", {})
                if source:
                    venue = source.get("display_name", "Unknown venue")
            
            # Reconstruct abstract
            abstract = self._reconstruct_abstract(abstract_inverted)
            
            formatted_output.append(f"{i}. **{title}** ({year})")
            formatted_output.append(f"   Authors: {authors_str}")
            formatted_output.append(f"   Venue: {venue} | Citations: {citation_count}")
            
            if abstract and len(abstract) > 50:
                # Truncate long abstracts
                abstract_preview = abstract[:300] + "..." if len(abstract) > 300 else abstract
                formatted_output.append(f"   Abstract: {abstract_preview}")
            
            # Add links
            if open_access and open_access.get("oa_url"):
                formatted_output.append(f"   📖 Open Access: {open_access['oa_url']}")
            elif doi:
                formatted_output.append(f"   🔗 DOI: https://doi.org/{doi.replace('https://doi.org/', '')}")
            
            formatted_output.append("")  # Empty line between papers
        
        if len(works) > 10:
            formatted_output.append(f"... and {len(works) - 10} more results in this batch")
        
        return "\n".join(formatted_output)


# Create the search node function
openalex_search_node_instance = OpenAlexSearchNode()

async def openalex_search_node(state: ChatState) -> ChatState:
    """OpenAlex search node entry point."""
    return await openalex_search_node_instance.execute_search_node(state, RESULT_KEY)
