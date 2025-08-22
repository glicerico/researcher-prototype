"""
Base class for API search nodes with shared execution logic.
Each subclass implements API-specific search and formatting methods.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any
from nodes.base import ChatState, logger, queue_status
from utils import get_last_user_message


class BaseAPISearchNode(ABC):
    """
    Abstract base class for API-based search nodes.
    Provides shared execution logic while allowing API-specific implementations.
    """
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that the API configuration is available and correct."""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Perform the actual API search.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            **kwargs: Additional search parameters
            
        Returns:
            Dict with 'success', 'results', and optional 'error' keys
        """
        pass
    
    @abstractmethod
    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format search results into readable text for LLM processing."""
        pass
    
    async def execute_search_node(self, state: ChatState, storage_key: str) -> ChatState:
        """
        Common search node execution logic with hardcoded storage key.
        
        Args:
            state: The current chat state
            storage_key: Where to store results (e.g., "academic_search")
            
        Returns:
            Updated chat state with search results
        """
        logger.info(f"🔍 {self.source_name}: Preparing to search")
        queue_status(state.get("thread_id"), f"Searching {self.source_name.lower()}...")
        
        # Get search query (shared logic)
        refined_query = state.get("workflow_context", {}).get("refined_search_query")
        original_user_query = get_last_user_message(state.get("messages", []))
        query_to_search = refined_query if refined_query else original_user_query
        
        if not query_to_search:
            state["module_results"][storage_key] = {
                "success": False,
                "error": f"No query found for {self.source_name} search (neither refined nor original).",
            }
            return state
        
        # Log the search query (shared logic)
        display_msg = query_to_search[:75] + "..." if len(query_to_search) > 75 else query_to_search
        logger.info(f'🔍 {self.source_name}: Searching for: "{display_msg}"')
        
        # Validate configuration (API-specific)
        if not self.validate_config():
            error_message = f"{self.source_name} API configuration not available or incomplete."
            logger.warning(error_message)
            state["module_results"][storage_key] = {
                "success": False, 
                "error": error_message
            }
            return state
        
        try:
            # Perform the search with max 10 results (API-specific)
            search_results = await self.search(query_to_search, limit=10)
            
            if search_results.get("success", False):
                # Format results for readability (API-specific)
                formatted_content = self.format_results(search_results)
                
                # Store successful results directly to hardcoded key (shared structure)
                state["module_results"][storage_key] = {
                    "success": True,
                    "content": formatted_content,
                    "raw_results": search_results,
                    "source": self.source_name,
                    "query_used": query_to_search
                }
                
                result_count = len(search_results.get('results', []))
                logger.info(f"🔍 {self.source_name}: ✅ Found {result_count} results")
            else:
                error_msg = search_results.get("error", "Unknown search error")
                state["module_results"][storage_key] = {
                    "success": False,
                    "error": error_msg
                }
                logger.warning(f"🔍 {self.source_name}: ❌ Search failed: {error_msg}")
                
        except Exception as e:
            error_message = f"{self.source_name} search error: {str(e)}"
            logger.error(f"🔍 {self.source_name}: ❌ Exception: {error_message}")
            state["module_results"][storage_key] = {
                "success": False,
                "error": error_message
            }
        
        return state
