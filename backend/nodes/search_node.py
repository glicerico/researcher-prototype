"""
Search node for performing web searches and retrieving information.
"""

import asyncio
from nodes.base import (
    ChatState,
    logger,
    PERPLEXITY_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
    personalization_manager,
)
from utils import get_last_user_message
import requests


def _get_source_preferences(user_id: str) -> dict:
    """Get user's source preferences from personalization context."""
    if not user_id:
        return {}
    
    try:
        logger.info(f"🔍 Search: Retrieving personalization context for user {user_id}")
        personalization_context = personalization_manager.get_personalization_context(user_id)
        content_prefs = personalization_context.get("content_preferences", {})
        source_preferences = content_prefs.get("source_types", {})
        logger.debug(f"🔍 Search: Retrieved source preferences for user {user_id}: {source_preferences}")
        return source_preferences
    except Exception as e:
        logger.warning(f"🔍 Search: ⚠️ Could not retrieve personalization context for user {user_id}: {str(e)}")
        return {}


def _get_content_preferences(user_id: str) -> dict:
    """Get full content preferences (including research_depth) from personalization context."""
    if not user_id:
        return {}
    try:
        personalization_context = personalization_manager.get_personalization_context(user_id)
        return personalization_context.get("content_preferences", {})
    except Exception as e:
        logger.warning(f"🔍 Search: ⚠️ Could not retrieve content preferences for user {user_id}: {str(e)}")
        return {}


def _merge_search_parameters_with_optimizer(
    source_preferences: dict,
    optimizer_mode: str | None,
    optimizer_context_size: str | None,
    optimizer_confidence: dict | None,
    research_depth: str | None,
) -> tuple[str, dict]:
    """Merge optimizer suggestions with user preferences for mode and context size."""
    # Defaults
    search_mode = "web"
    web_search_options = {"search_context_size": "medium"}

    # User prefs
    academic_weight = source_preferences.get("academic_papers", 0.5)
    # research_depth provided separately (lives under content_preferences)

    # Confidence
    confidence = optimizer_confidence or {}

    # Mode: use optimizer if confident, else prefs
    if optimizer_mode and confidence.get("search_mode", 0.0) >= 0.7:
        search_mode = optimizer_mode
    else:
        search_mode = "academic" if academic_weight >= 0.7 else "web"

    # Context size: use optimizer if confident, else map from research_depth
    if optimizer_context_size and confidence.get("context_size", 0.0) >= 0.7:
        size = optimizer_context_size
    else:
        depth_to_size = {"shallow": "low", "balanced": "medium", "deep": "high"}
        size = depth_to_size.get((research_depth or "balanced").lower(), "medium")
    web_search_options["search_context_size"] = size

    # If academic mode, bias to high context
    if search_mode == "academic" and web_search_options["search_context_size"] != "high":
        web_search_options["search_context_size"] = "high"

    return search_mode, web_search_options





async def search_node(state: ChatState) -> ChatState:
    """Performs web search for user queries requiring up-to-date information."""
    logger.info("🔍 Search: Preparing to search for information")
    queue_status(state.get("thread_id"), "Searching the web...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible
    
    # Get search query
    refined_query = state.get("workflow_context", {}).get("refined_search_query")
    original_user_query = get_last_user_message(state.get("messages", []))
    query_to_search = refined_query if refined_query else original_user_query

    if not query_to_search:
        state["module_results"]["search"] = {
            "success": False,
            "error": "No query found for search (neither refined nor original).",
        }
        return state

    # Log the search query
    display_msg = query_to_search[:75] + "..." if len(query_to_search) > 75 else query_to_search
    logger.info(f'🔍 Search: Searching for: "{display_msg}"')

    # Check API key
    if not config.PERPLEXITY_API_KEY:
        error_message = "Perplexity API key not configured. Please set the PERPLEXITY_API_KEY environment variable."
        logger.error(f"🔍 Search: ❌ {error_message}")
        state["module_results"]["search"] = {"success": False, "error": error_message}
        return state

    try:
        # Get personalization context for search mode (but not recency)
        user_id = state.get("user_id")
        source_preferences = _get_source_preferences(user_id)
        
        # Merge optimizer suggestions with user preferences
        wc = state.get("workflow_context", {})
        optimizer_mode = wc.get("optimizer_search_mode")
        optimizer_context_size = wc.get("optimizer_context_size")
        optimizer_confidence = wc.get("optimizer_confidence", {})
        content_prefs = _get_content_preferences(user_id)
        research_depth = content_prefs.get("research_depth", "balanced")
        search_mode, web_search_options = _merge_search_parameters_with_optimizer(
            source_preferences, optimizer_mode, optimizer_context_size, optimizer_confidence, research_depth
        )
        
        # Get recency filter from search optimizer instead of user preferences
        search_recency_filter = state.get("workflow_context", {}).get("search_recency_filter")
        if search_recency_filter:
            logger.info(f"🔍 Search: Using optimizer-determined recency filter: {search_recency_filter}")
        else:
            logger.info("🔍 Search: No recency filter (optimizer determined content is timeless)")
        
        # Prepare API request
        headers = {"Authorization": f"Bearer {config.PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
        perplexity_system_prompt = PERPLEXITY_SYSTEM_PROMPT.format(current_time=get_current_datetime_str())
        perplexity_messages = [
            {"role": "system", "content": perplexity_system_prompt},
            {"role": "user", "content": query_to_search},
        ]

        payload = {
            "model": config.PERPLEXITY_MODEL, 
            "messages": perplexity_messages, 
            "stream": False,
            "search_mode": search_mode,
            "web_search_options": web_search_options
        }
        
        # Add optional parameters
        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter
            

        # Make API request
        logger.debug(f"🔍 Search: Payload to Perplexity: {payload}")
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)

        # Process response
        if response.status_code == 200:
            response_data = response.json()
            search_result = response_data["choices"][0]["message"]["content"]
            citations = response_data.get("citations", [])
            search_results = response_data.get("search_results", [])

            # Log results
            display_result = search_result[:75] + "..." if len(search_result) > 75 else search_result
            logger.info(f'🔍 Search: ✅ Result received: "{display_result}"')
            if citations:
                logger.info(f"🔍 Search: ✅ Found {len(citations)} citations")
            if search_results:
                logger.info(f"🔍 Search: ✅ Found {len(search_results)} search result sources")

            state["module_results"]["search"] = {
                "success": True,
                "result": search_result,
                "query_used": query_to_search,
                "citations": citations,
                "search_results": search_results,
            }
        else:
            error_message = f"Perplexity API request failed with status code {response.status_code}: {response.text}"
            logger.error(f"🔍 Search: ❌ {error_message}")
            state["module_results"]["search"] = {
                "success": False,
                "error": error_message,
                "status_code": response.status_code,
            }

    except Exception as e:
        error_message = f"Error in search_node: {str(e)}"
        logger.error(f"🔍 Search: ❌ {error_message}", exc_info=True)
        state["module_results"]["search"] = {"success": False, "error": error_message}

    return state
