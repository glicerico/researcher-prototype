"""
Source coordinator node for managing parallel execution of multiple search sources.
"""

import asyncio
from typing import Dict, Any
from nodes.base import (
    ChatState,
    logger,
    queue_status,
)

# Import search services
from services.search_services import (
    PerplexitySearchService,
    OpenAlexSearchService,
    HackerNewsSearchService,
    PubMedSearchService
)


async def source_coordinator_node(state: ChatState) -> ChatState:
    """Coordinates parallel execution of selected search sources using service classes."""
    logger.info("🎛️ Source Coordinator: Managing parallel search execution")
    queue_status(state.get("thread_id"), "Coordinating searches...")
    
    selected_sources = state.get("selected_sources", [])
    if not selected_sources:
        logger.warning("🎛️ Source Coordinator: No sources selected, skipping coordination")
        return state
        
    logger.info(f"🎛️ Source Coordinator: Executing {len(selected_sources)} sources: {selected_sources}")
    
    # Map source names to their corresponding service instances
    service_map = {
        "search": PerplexitySearchService(),
        "academic_search": OpenAlexSearchService(),
        "social_search": HackerNewsSearchService(),
        "medical_search": PubMedSearchService(),
    }
    
    # Create tasks for parallel execution
    tasks = []
    valid_sources = []
    
    for source in selected_sources:
        if source in service_map:
            service = service_map[source]
            tasks.append(_execute_search_service(service, state, source))
            valid_sources.append(source)
        else:
            logger.warning(f"🎛️ Source Coordinator: Unknown source '{source}', skipping")
    
    if not tasks:
        logger.warning("🎛️ Source Coordinator: No valid sources to execute")
        return state
    
    # Initialize module_results if not present
    state.setdefault("module_results", {})
    
    # Run all sources in parallel
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and store in state
        for i, result in enumerate(results):
            source_name = valid_sources[i]
            result_key = _get_result_key(source_name)
            
            if isinstance(result, Exception):
                logger.error(f"🎛️ Source Coordinator: Error in {source_name}: {str(result)}")
                state["module_results"][result_key] = {
                    "success": False,
                    "error": f"Exception in {source_name}: {str(result)}",
                    "source": source_name
                }
            elif isinstance(result, dict):
                # Store the search result directly
                state["module_results"][result_key] = result
            else:
                logger.warning(f"🎛️ Source Coordinator: Unexpected result type from {source_name}: {type(result)}")
                state["module_results"][result_key] = {
                    "success": False,
                    "error": f"Unexpected result type from {source_name}",
                    "source": source_name
                }
        
        logger.info(f"🎛️ Source Coordinator: ✅ Completed parallel execution of {len(valid_sources)} sources")
        
    except Exception as e:
        logger.error(f"🎛️ Source Coordinator: ❌ Error in parallel execution: {str(e)}")
        # Ensure we have error results for all sources
        for source in valid_sources:
            result_key = _get_result_key(source)
            if result_key not in state.get("module_results", {}):
                state["module_results"][result_key] = {
                    "success": False,
                    "error": f"Parallel execution error: {str(e)}",
                    "source": source
                }
    
    return state


async def _execute_search_service(service, state: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """Execute a single search service and return the results."""
    try:
        logger.debug(f"🔍 Executing {source_name} service")
        # Call the service's search method directly
        result = await service.search(state)
        logger.debug(f"✅ Completed {source_name} service")
        return result
    except Exception as e:
        logger.error(f"❌ Error in {source_name} service: {str(e)}")
        return {
            "success": False,
            "error": f"Service execution error: {str(e)}",
            "source": source_name
        }


def _get_result_key(source_name: str) -> str:
    """Get the result key for a source name."""
    # Map source names to their result keys (same as used in original nodes)
    key_map = {
        "search": "search",
        "academic_search": "academic_search", 
        "social_search": "social_search",
        "medical_search": "medical_search"
    }
    return key_map.get(source_name, source_name)
