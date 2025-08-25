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
from nodes.base import ChatState, logger, queue_status
from config import SEARCH_RESULTS_LIMIT
from utils import get_last_user_message
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
            # Smart search strategy: try title/abstract search first, then general search
            # 1. Try title search for high precision
            title_params = {
                "filter": f"title.search:{query},type:article,is_retracted:false",
                "per-page": min(limit, 200),
                "sort": "relevance_score:desc",
                "select": "id,title,display_name,publication_year,publication_date,doi,cited_by_count,abstract_inverted_index,authorships,primary_location,open_access,type"
            }
            
            response = requests.get(
                f"{self.base_url}/works",
                params=title_params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                works = data.get("results", [])
                total_count = data.get("meta", {}).get("count", len(works))
                
                # If title search yields insufficient results, supplement with abstract search
                if len(works) < limit // 2 and len(works) < 10:
                    abstract_params = {
                        "filter": f"abstract.search:{query},type:article,is_retracted:false",
                        "per-page": min(limit - len(works), 200),
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
                            title_ids = {work.get("id") for work in works}
                            unique_abstract_works = [work for work in abstract_works if work.get("id") not in title_ids]
                            
                            works = works + unique_abstract_works
                            total_count = total_count + abstract_data.get("meta", {}).get("count", 0)
                    except Exception:
                        # Keep title results only on any error
                        pass
                
                # If still insufficient results, try general search as final fallback
                if len(works) < limit // 3 and len(works) < 5:
                    general_params = {
                        "search": query,
                        "filter": "type:article,is_retracted:false",
                        "per-page": min(limit - len(works), 200),
                        "sort": "relevance_score:desc",
                        "select": "id,title,display_name,publication_year,publication_date,doi,cited_by_count,abstract_inverted_index,authorships,primary_location,open_access,type"
                    }
                    
                    try:
                        general_response = requests.get(
                            f"{self.base_url}/works",
                            params=general_params,
                            headers=self.headers,
                            timeout=30
                        )
                        
                        if general_response.status_code == 200:
                            general_data = general_response.json()
                            general_works = general_data.get("results", [])
                            
                            # Deduplicate and combine with existing results
                            existing_ids = {work.get("id") for work in works}
                            unique_general_works = [work for work in general_works if work.get("id") not in existing_ids]
                            
                            works = works + unique_general_works
                            total_count = total_count + general_data.get("meta", {}).get("count", 0)
                    except Exception:
                        # Keep existing results on any error
                        pass
                
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
    """OpenAlex search node entry point with academic query optimization."""
    logger.info(f"🔍 {openalex_search_node_instance.source_name}: Preparing to search")
    queue_status(state.get("thread_id"), f"Searching {openalex_search_node_instance.source_name.lower()}...")
    
    # Get academic-optimized query first, then fall back to refined, then original
    academic_query = state.get("workflow_context", {}).get("academic_search_query")
    refined_query = state.get("workflow_context", {}).get("refined_search_query")
    original_user_query = get_last_user_message(state.get("messages", []))
    
    # Priority: academic_query > refined_query > original_query
    query_to_search = academic_query if academic_query else (refined_query if refined_query else original_user_query)
    
    if not query_to_search:
        state["module_results"][RESULT_KEY] = {
            "success": False,
            "error": f"No query found for {openalex_search_node_instance.source_name} search (no academic, refined, or original query).",
        }
        return state
    
    # Log which query type is being used
    if academic_query:
        logger.info(f"🔍 {openalex_search_node_instance.source_name}: Using academic-optimized query")
    elif refined_query:
        logger.info(f"🔍 {openalex_search_node_instance.source_name}: Using refined query (no academic optimization)")
    else:
        logger.info(f"🔍 {openalex_search_node_instance.source_name}: Using original user query (no optimization)")
    
    # Log the search query
    display_msg = query_to_search[:75] + "..." if len(query_to_search) > 75 else query_to_search
    logger.info(f'🔍 {openalex_search_node_instance.source_name}: Searching for: "{display_msg}"')
    
    # Validate configuration
    if not openalex_search_node_instance.validate_config():
        error_message = f"{openalex_search_node_instance.source_name} API configuration not available or incomplete."
        logger.warning(error_message)
        state["module_results"][RESULT_KEY] = {
            "success": False, 
            "error": error_message
        }
        return state
    
    try:
        # Perform the search with max results limit
        search_results = await openalex_search_node_instance.search(query_to_search, limit=SEARCH_RESULTS_LIMIT)
        
        if search_results.get("success", False):
            # Format results for readability
            formatted_content = openalex_search_node_instance.format_results(search_results)
            
            # Store successful results
            state["module_results"][RESULT_KEY] = {
                "success": True,
                "content": formatted_content,
                "raw_results": search_results,
                "source": openalex_search_node_instance.source_name,
                "query_used": query_to_search
            }
            
            result_count = len(search_results.get('results', []))
            logger.info(f"🔍 {openalex_search_node_instance.source_name}: ✅ Found {result_count} results")
        else:
            error_msg = search_results.get("error", "Unknown search error")
            state["module_results"][RESULT_KEY] = {
                "success": False,
                "error": error_msg
            }
            logger.warning(f"🔍 {openalex_search_node_instance.source_name}: ❌ Search failed: {error_msg}")
            
    except Exception as e:
        error_message = f"{openalex_search_node_instance.source_name} search error: {str(e)}"
        logger.error(f"🔍 {openalex_search_node_instance.source_name}: ❌ Exception: {error_message}")
        state["module_results"][RESULT_KEY] = {
            "success": False,
            "error": error_message
        }
    
    return state
