"""
Search node for performing web searches and retrieving information.
"""
from nodes.base import (
    ChatState, 
    logger, 
    HumanMessage,
    PERPLEXITY_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)
from utils import get_last_user_message
import requests


def search_node(state: ChatState) -> ChatState:
    """Performs web search for user queries requiring up-to-date information."""
    logger.info("🔍 Search: Preparing to search for information")
    logger.debug(f"Search node received state: {state}")
    
    # Use the refined query if available, otherwise get the last user message
    refined_query = state.get("workflow_context", {}).get("refined_search_query")
    original_user_query = get_last_user_message(state.get("messages", []))

    query_to_search = refined_query if refined_query else original_user_query

    if not query_to_search:
        state["module_results"]["search"] = {"success": False, "error": "No query found for search (neither refined nor original)."}
        return state
        
    # Log the search query
    display_msg = query_to_search[:75] + "..." if len(query_to_search) > 75 else query_to_search
    logger.info(f"🔍 Search: Searching for: \"{display_msg}\"")
    
    # Check if Perplexity API key is available
    if not config.PERPLEXITY_API_KEY:
        error_message = "Perplexity API key not configured. Please set the PERPLEXITY_API_KEY environment variable."
        logger.error(error_message)
        state["module_results"]["search"] = {"success": False, "error": error_message}
        return state
    
    try:
        # Prepare the search query
        headers = {
            "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Format the search prompt 
        perplexity_system_prompt = PERPLEXITY_SYSTEM_PROMPT.format(
            current_time=get_current_datetime_str()
        )
        perplexity_messages = [
            {"role": "system", "content": perplexity_system_prompt},
            {"role": "user", "content": query_to_search}
        ]
        
        # Prepare the API request
        payload = {
            "model": config.PERPLEXITY_MODEL,
            "messages": perplexity_messages,
            "options": {"stream": False}
        }
        
        logger.debug(f"Sending search request to Perplexity API with query: {query_to_search}")
        
        # Make the API request to Perplexity
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        )
        
        # Process the response
        if response.status_code == 200:
            response_data = response.json()
            search_result = response_data["choices"][0]["message"]["content"]
            
            # Log the search result
            display_result = search_result[:75] + "..." if len(search_result) > 75 else search_result
            logger.info(f"🔍 Search: Result received: \"{display_result}\"")
            
            state["module_results"]["search"] = {
                "success": True,
                "result": search_result,
                "query_used": query_to_search
            }
        else:
            # Handle API error
            error_message = f"Perplexity API request failed with status code {response.status_code}: {response.text}"
            logger.error(error_message)
            state["module_results"]["search"] = {
                "success": False, 
                "error": error_message,
                "status_code": response.status_code
            }
            
    except Exception as e:
        # Handle any exceptions
        error_message = f"Error in search_node: {str(e)}"
        logger.error(error_message, exc_info=True)
        state["module_results"]["search"] = {"success": False, "error": error_message}
    
    return state 