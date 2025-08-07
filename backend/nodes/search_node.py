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


def _build_search_parameters(source_preferences: dict) -> tuple[str, dict, list, str]:
    """Build personalized search parameters based on user preferences."""
    # Default values
    search_mode = "web"
    web_search_options = {"search_context_size": "medium"}
    search_domain_filter = []
    search_recency_filter = None
    
    # Get preference weights
    academic_weight = source_preferences.get("academic_papers", 0.5)
    news_weight = source_preferences.get("news_articles", 0.5)
    expert_weight = source_preferences.get("expert_blogs", 0.5)
    
    # Determine search mode and context size
    if academic_weight > 0.7:
        search_mode = "academic"
        web_search_options["search_context_size"] = "high"
        search_recency_filter = "year"
        logger.info(f"🔍 Search: Using academic search mode (preference: {academic_weight})")
    else:
        logger.info(f"🔍 Search: Using web search mode (academic preference: {academic_weight})")
    
    # Set recency filter for news preference
    if news_weight > 0.7:
        search_recency_filter = "week"
        logger.info(f"🔍 Search: Using week recency filter for news preference")
    
    # Add non-academic domain filters
    domain_mappings = {
        "news_articles": [
            "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
            "bbc.com", "cnn.com", "npr.org", "apnews.com"
        ],
        "expert_blogs": [
            "medium.com", "substack.com", "techcrunch.com",
            "hbr.org", "mckinsey.com", "pwc.com", "deloitte.com"
        ]
    }
    
    for source_type, domains in domain_mappings.items():
        if source_preferences.get(source_type, 0.5) > 0.7:
            search_domain_filter.extend(domains)
            logger.info(f"🔍 Search: Added {source_type} domains")
    
    return search_mode, web_search_options, search_domain_filter, search_recency_filter


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
        # Get personalization context
        user_id = state.get("user_id")
        source_preferences = _get_source_preferences(user_id)
        
        # Build search parameters
        search_mode, web_search_options, search_domain_filter, search_recency_filter = _build_search_parameters(source_preferences)
        
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
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter[:10]  # Limit to 10 domains max
            logger.info(f"🔍 Search: Using domain filter with {len(payload['search_domain_filter'])} domains")
            
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
