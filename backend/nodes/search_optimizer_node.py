"""
Search optimizer node for refining user queries into more effective search queries.
"""
from nodes.base import (
    ChatState, 
    logger, 
    HumanMessage, 
    AIMessage, 
    SystemMessage,
    ChatOpenAI, 
    SearchQuery,
    SEARCH_OPTIMIZER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)
from utils import get_last_user_message


def search_prompt_optimizer_node(state: ChatState) -> ChatState:
    """Refines the user's query into an optimized search query using an LLM, considering conversation context."""
    logger.info("🔬 Search Optimizer: Refining user query for search")
    current_time_str = get_current_datetime_str()
    
    # Gather recent conversation history for context (e.g., last 5 messages)
    raw_messages = state.get("messages", [])
    
    # Get the actual last user message to be refined
    last_user_message_content = get_last_user_message(raw_messages)
    
    if not last_user_message_content:
        logger.warning("No user message found in search_prompt_optimizer_node. Cannot refine.")
        state["workflow_context"]["refined_search_query"] = ""
        return state

    # Log the user message being refined
    display_msg = last_user_message_content[:75] + "..." if len(last_user_message_content) > 75 else last_user_message_content
    logger.info(f"🔬 Search Optimizer: Refining query: \"{display_msg}\"")
    
    # Create system message with optimizer instructions
    memory_context = state.get("memory_context")
    memory_context_section = ""
    if memory_context:
        memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
        logger.debug("🔬 Search Optimizer: Including memory context in search optimization")
    else:
        logger.debug("🔬 Search Optimizer: No memory context available")
    
    system_message = SystemMessage(content=SEARCH_OPTIMIZER_SYSTEM_PROMPT.format(
        current_time=current_time_str,
        memory_context_section=memory_context_section
    ))
    
    history_messages = state.get("messages", [])
    
    # Build the complete message list for the optimizer
    context_messages_for_llm = [system_message] + history_messages
    
    # Initialize the optimizer LLM
    optimizer_llm = ChatOpenAI(
        model=config.ROUTER_MODEL, 
        temperature=0.0,
        max_tokens=100,
        api_key=config.OPENAI_API_KEY
    )
    
    # Create structured output model
    structured_optimizer = optimizer_llm.with_structured_output(SearchQuery)
    
    try:
        # Invoke the structured optimizer
        search_result = structured_optimizer.invoke(context_messages_for_llm)
        
        # Extract the refined query from the structured result
        refined_query = search_result.query
        search_type = search_result.search_type
        
        # Log the refined query
        display_refined = refined_query[:75] + "..." if len(refined_query) > 75 else refined_query
        logger.info(f"🔬 Search Optimizer: Produced refined query: \"{display_refined}\" (type: {search_type})")
        
        # Store both the refined query and search type in the workflow context
        state["workflow_context"]["refined_search_query"] = refined_query
        state["workflow_context"]["search_type"] = search_type
        logger.info(f"Refined search query with context: {refined_query}")
        
    except Exception as e:
        logger.error(f"Error in search_prompt_optimizer_node (with context): {str(e)}. Using original query as fallback.")
        state["workflow_context"]["refined_search_query"] = last_user_message_content
        state["workflow_context"]["search_type"] = "unknown"
        
    return state 