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


async def search_node(state: ChatState) -> ChatState:
    """Performs web search for user queries requiring up-to-date information."""
    logger.info("🔍 Search: Preparing to search for information")
    queue_status(state.get("thread_id"), "Searching the web...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible
    logger.debug(f"Search node received state: {state}")

    # Use the refined query if available, otherwise get the last user message
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

    # Check if Perplexity API key is available
    if not config.PERPLEXITY_API_KEY:
        error_message = "Perplexity API key not configured. Please set the PERPLEXITY_API_KEY environment variable."
        logger.error(f"🔍 Search: ❌ {error_message}")
        state["module_results"]["search"] = {"success": False, "error": error_message}
        return state

    try:
        # Get personalization context for source preferences
        user_id = state.get("user_id")
        source_preferences = {}
        
        if user_id:
            try:
                logger.info(f"🔍 Search: Retrieving personalization context for user {user_id}")
                personalization_context = personalization_manager.get_personalization_context(user_id)
                content_prefs = personalization_context.get("content_preferences", {})
                source_preferences = content_prefs.get("source_types", {})
                logger.debug(f"🔍 Search: Retrieved source preferences for user {user_id}: {source_preferences}")
                    
            except Exception as e:
                logger.warning(f"🔍 Search: ⚠️ Could not retrieve personalization context for user {user_id}: {str(e)}")

        # Prepare the search query
        headers = {"Authorization": f"Bearer {config.PERPLEXITY_API_KEY}", "Content-Type": "application/json"}

        # Format the search prompt
        perplexity_system_prompt = PERPLEXITY_SYSTEM_PROMPT.format(current_time=get_current_datetime_str())
        perplexity_messages = [
            {"role": "system", "content": perplexity_system_prompt},
            {"role": "user", "content": query_to_search},
        ]

        # Build personalized web search options
        web_search_options = {"search_context_size": "medium"}  # Default context size
        
        # Determine search mode based on source preferences
        search_mode = "web"  # Default mode
        academic_weight = source_preferences.get("academic_papers", 0.5)
        if academic_weight > 0.7:
            search_mode = "academic"
            web_search_options["search_context_size"] = "high"  # More context for academic users
            logger.info(f"🔍 Search: Using academic search mode for user {user_id} (academic preference: {academic_weight})")
        else:
            logger.info(f"🔍 Search: Using web search mode for user {user_id} (academic preference: {academic_weight})")
        
        # Set recency filter based on news preference
        news_weight = source_preferences.get("news_articles", 0.5)
        search_recency_filter = None
        if news_weight > 0.7:
            search_recency_filter = "week"  # Recent news for news-preferring users
            logger.info(f"🔍 Search: Using week recency filter for news-preferring user {user_id}")
        elif academic_weight > 0.7:
            search_recency_filter = "year"  # Broader timeframe for academic content
            logger.info(f"🔍 Search: Using year recency filter for academic user {user_id}")
            
        # Build search domain filter based on source preferences
        search_domain_filter = []
        
        # Add academic domains if user prefers academic sources
        if source_preferences.get("academic_papers", 0.5) > 0.7:
            academic_domains = [
                "arxiv.org", "scholar.google.com", "pubmed.ncbi.nlm.nih.gov", 
                "ieee.org", "acm.org", "nature.com", "science.org",
                "springer.com", "wiley.com", "sciencedirect.com"
            ]
            search_domain_filter.extend(academic_domains)
            logger.info(f"🔍 Search: Added academic domains for user {user_id}")
            
        # Add news domains if user prefers news sources  
        if source_preferences.get("news_articles", 0.5) > 0.7:
            news_domains = [
                "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
                "bbc.com", "cnn.com", "npr.org", "apnews.com"
            ]
            search_domain_filter.extend(news_domains)
            logger.info(f"🔍 Search: Added news domains for user {user_id}")
            
        # Add expert blog domains if user prefers expert commentary
        if source_preferences.get("expert_blogs", 0.5) > 0.7:
            expert_domains = [
                "medium.com", "substack.com", "techcrunch.com",
                "hbr.org", "mckinsey.com", "pwc.com", "deloitte.com"
            ]
            search_domain_filter.extend(expert_domains)
            logger.info(f"🔍 Search: Added expert domains for user {user_id}")

        # Prepare the API request with personalized parameters
        payload = {
            "model": config.PERPLEXITY_MODEL, 
            "messages": perplexity_messages, 
            "stream": False,
            "search_mode": search_mode,
            "web_search_options": web_search_options
        }
        
        # Add optional parameters based on personalization
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter[:10]  # Limit to 10 domains max
            logger.info(f"🔍 Search: Using domain filter with {len(payload['search_domain_filter'])} domains")
            
        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter
            
        # Add reasoning effort for deep research model
        if config.PERPLEXITY_MODEL == "sonar-deep-research":
            # Use higher reasoning effort for academic users
            reasoning_effort = "high" if academic_weight > 0.7 else "medium"
            payload["reasoning_effort"] = reasoning_effort
            logger.info(f"🔍 Search: Using {reasoning_effort} reasoning effort for deep research")

        logger.debug(f"Sending search request to Perplexity API with query: {query_to_search}")

        # Make the API request to Perplexity
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)

        # Process the response
        if response.status_code == 200:
            response_data = response.json()
            search_result = response_data["choices"][0]["message"]["content"]

            # Extract additional useful information from the response
            citations = response_data.get("citations", [])
            search_results = response_data.get("search_results", [])

            # Log the search result
            display_result = search_result[:75] + "..." if len(search_result) > 75 else search_result
            logger.info(f'🔍 Search: ✅ Result received: "{display_result}"')

            # Log additional context information
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
            # Handle API error
            error_message = f"Perplexity API request failed with status code {response.status_code}: {response.text}"
            logger.error(f"🔍 Search: ❌ {error_message}")
            state["module_results"]["search"] = {
                "success": False,
                "error": error_message,
                "status_code": response.status_code,
            }

    except Exception as e:
        # Handle any exceptions
        error_message = f"Error in search_node: {str(e)}"
        logger.error(f"🔍 Search: ❌ {error_message}", exc_info=True)
        state["module_results"]["search"] = {"success": False, "error": error_message}

    return state
