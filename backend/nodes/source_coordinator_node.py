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

# Import all search nodes
from nodes.search_node import search_node
from nodes.semantic_scholar_node import semantic_scholar_search_node  
from nodes.reddit_search_node import reddit_search_node
from nodes.pubmed_search_node import pubmed_search_node
from nodes.analyzer_node import analyzer_node
from nodes.analysis_refiner_node import analysis_task_refiner_node


async def source_coordinator_node(state: ChatState) -> ChatState:
    """Coordinates parallel execution of selected search sources."""
    logger.info("🎛️ Source Coordinator: Managing parallel search execution")
    queue_status(state.get("thread_id"), "Coordinating searches...")
    
    selected_sources = state.get("selected_sources", [])
    if not selected_sources:
        logger.warning("🎛️ Source Coordinator: No sources selected, skipping coordination")
        return state
        
    logger.info(f"🎛️ Source Coordinator: Executing {len(selected_sources)} sources: {selected_sources}")
    
    # Map source names to their corresponding node functions
    source_map = {
        "search": search_node,
        "academic_search": semantic_scholar_search_node,
        "social_search": reddit_search_node,
        "medical_search": pubmed_search_node,
    }
    
    # Execute all selected sources in parallel
    tasks = []
    for source in selected_sources:
        if source in source_map:
            tasks.append(_execute_source(source_map[source], state.copy(), source))
        else:
            logger.warning(f"🎛️ Source Coordinator: Unknown source '{source}', skipping")
    
    if not tasks:
        logger.warning("🎛️ Source Coordinator: No valid sources to execute")
        return state
    
    # Run all sources in parallel
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results back into main state
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = selected_sources[i]
                logger.error(f"🎛️ Source Coordinator: Error in {source_name}: {str(result)}")
            elif isinstance(result, dict):
                # Merge the state from each source
                if "module_results" in result:
                    state.setdefault("module_results", {}).update(result["module_results"])
                if "workflow_context" in result:
                    state.setdefault("workflow_context", {}).update(result["workflow_context"])
        
        logger.info(f"🎛️ Source Coordinator: ✅ Completed parallel execution of {len(selected_sources)} sources")
        
    except Exception as e:
        logger.error(f"🎛️ Source Coordinator: ❌ Error in parallel execution: {str(e)}")
    
    return state


async def _execute_source(source_func, state: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """Execute a single source function and return the updated state."""
    try:
        logger.debug(f"🔍 Executing {source_name}")
        result_state = await source_func(state)
        logger.debug(f"✅ Completed {source_name}")
        return result_state
    except Exception as e:
        logger.error(f"❌ Error in {source_name}: {str(e)}")
        # Return state with error recorded
        state.setdefault("module_results", {})[source_name] = {
            "success": False,
            "error": str(e)
        }
        return state


# Removed _analyzer_with_refiner since analyzer is now handled as separate intent path
