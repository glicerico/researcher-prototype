"""
Base class for API search nodes to ensure consistent interface across different sources.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from nodes.base import (
    ChatState,
    logger,
    config,
    get_current_datetime_str,
    queue_status,
)
from utils import get_last_user_message


class BaseAPISearchNode(ABC):
    """Base class for all API search nodes with consistent interface."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        
    @abstractmethod
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform the actual API search.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
            
        Returns:
            Dict containing search results with structure:
            {
                "success": bool,
                "results": List[Dict],  # List of search results
                "total_count": int,
                "error": str,  # Only present if success=False
                "metadata": Dict  # Any additional metadata
            }
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that required configuration/API keys are available."""
        pass
    
    @abstractmethod
    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format search results into readable text for LLM processing."""
        pass
    
    async def execute_search_node(self, state: ChatState) -> ChatState:
        """
        Common search node execution logic.
        This method should be called by specific search node implementations.
        """
        logger.info(f"🔍 {self.source_name}: Preparing to search for information")
        queue_status(state.get("thread_id"), f"Searching {self.source_name}...")
        await asyncio.sleep(0.1)  # Small delay to ensure status is visible
        
        # Use the refined query if available, otherwise get the last user message
        refined_query = state.get("workflow_context", {}).get("refined_search_query")
        original_user_query = get_last_user_message(state.get("messages", []))
        
        query_to_search = refined_query if refined_query else original_user_query
        
        if not query_to_search:
            state["module_results"][self.source_name.lower()] = {
                "success": False,
                "error": f"No query found for {self.source_name} search (neither refined nor original).",
            }
            return state
        
        # Log the search query
        display_msg = query_to_search[:75] + "..." if len(query_to_search) > 75 else query_to_search
        logger.info(f'🔍 {self.source_name}: Searching for: "{display_msg}"')
        
        # Validate configuration
        if not self.validate_config():
            error_message = f"{self.source_name} API configuration not available or incomplete."
            logger.warning(error_message)
            state["module_results"][self.source_name.lower()] = {
                "success": False, 
                "error": error_message
            }
            return state
        
        try:
            # Perform the search
            search_results = await self.search(query_to_search)
            
            if search_results.get("success", False):
                # Format results for readability
                formatted_content = self.format_results(search_results)
                
                # Log success
                result_count = search_results.get("total_count", len(search_results.get("results", [])))
                logger.info(f'🔍 {self.source_name}: Found {result_count} results')
                
                state["module_results"][self.source_name.lower()] = {
                    "success": True,
                    "result": formatted_content,
                    "query_used": query_to_search,
                    "total_count": result_count,
                    "source": self.source_name,
                    "metadata": search_results.get("metadata", {})
                }
            else:
                error_message = search_results.get("error", f"Unknown error in {self.source_name} search")
                logger.error(f"{self.source_name} search failed: {error_message}")
                state["module_results"][self.source_name.lower()] = {
                    "success": False,
                    "error": error_message,
                    "source": self.source_name
                }
                
        except Exception as e:
            error_message = f"Error in {self.source_name} search: {str(e)}"
            logger.error(error_message, exc_info=True)
            state["module_results"][self.source_name.lower()] = {
                "success": False, 
                "error": error_message,
                "source": self.source_name
            }
        
        return state
    
    def extract_scope_filters(self, state: ChatState) -> List[str]:
        """Extract scope filters from routing analysis."""
        routing_analysis = state.get("routing_analysis", {})
        return routing_analysis.get("scope_filters", [])
    
    def get_source_preference(self, state: ChatState) -> str:
        """Get preferred source from routing analysis."""
        routing_analysis = state.get("routing_analysis", {})
        return routing_analysis.get("source_preference", "auto")