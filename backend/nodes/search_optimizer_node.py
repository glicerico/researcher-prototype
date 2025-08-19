"""
Search optimizer node for refining user queries into more effective search queries.
"""

import json
from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ChatOpenAI,
    SEARCH_OPTIMIZER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
)
from utils import get_last_user_message
from llm_models import SearchOptimization


def search_prompt_optimizer_node(state: ChatState) -> ChatState:
    """Refines the user's query into an optimized search query using an LLM, considering conversation context."""
    logger.info("🔬 Search Optimizer: Refining user query for search")
    queue_status(state.get("thread_id"), "Optimizing search query...")
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
    display_msg = (
        last_user_message_content[:75] + "..." if len(last_user_message_content) > 75 else last_user_message_content
    )
    logger.info(f'🔬 Search Optimizer: Refining query: "{display_msg}"')

    # Create system message with optimizer instructions
    memory_context = state.get("memory_context")
    memory_context_section = ""
    if memory_context:
        memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
        logger.debug("🔬 Search Optimizer: Including memory context in search optimization")
    else:
        logger.debug("🔬 Search Optimizer: No memory context available")

    # Build user profile section for the prompt
    user_id = state.get("user_id")
    user_profile_section = ""
    try:
        if user_id:
            from nodes.base import personalization_manager  # local import to avoid cycles at module load
            personalization_context = personalization_manager.get_personalization_context(user_id)
            content_prefs = personalization_context.get("content_preferences", {})
            source_types = content_prefs.get("source_types", {})
            research_depth = content_prefs.get("research_depth", "balanced")
            user_profile_section = (
                "USER PROFILE:\n"
                f"- Research depth: {research_depth}\n"
                f"- Source type prefs: {source_types}\n"
            )
        else:
            user_profile_section = "USER PROFILE:\n- Research depth: balanced\n- Source type prefs: {}\n"
    except Exception:
        user_profile_section = "USER PROFILE:\n- Research depth: balanced\n- Source type prefs: {}\n"

    system_message = SystemMessage(
        content=SEARCH_OPTIMIZER_SYSTEM_PROMPT.format(
            current_time=current_time_str,
            memory_context_section=memory_context_section,
            user_profile_section=user_profile_section,
        )
    )

    history_messages = state.get("messages", [])

    # Build the complete message list for the optimizer
    context_messages_for_llm = [system_message] + history_messages

    # Initialize the optimizer LLM with structured output
    optimizer_llm = ChatOpenAI(
        model=config.ROUTER_MODEL, temperature=0.0, max_tokens=150, api_key=config.OPENAI_API_KEY
    ).with_structured_output(SearchOptimization)

    try:
        # Invoke the optimizer to get structured search optimization
        search_optimization = optimizer_llm.invoke(context_messages_for_llm)
        
        refined_query = search_optimization.query
        recency_filter = search_optimization.recency_filter
        search_mode = search_optimization.search_mode
        context_size = search_optimization.context_size
        confidence = search_optimization.confidence or {}

        if not refined_query:
            logger.warning("🔬 Search Optimizer: Empty query in structured response, using original query")
            refined_query = last_user_message_content
            recency_filter = None

        # Log the refined query and recency decision
        display_refined = refined_query[:75] + "..." if len(refined_query) > 75 else refined_query
        logger.info(f'🔬 Search Optimizer: Produced refined query: "{display_refined}"')
        if recency_filter:
            logger.info(f'🔬 Search Optimizer: Determined recency filter: "{recency_filter}"')
        else:
            logger.info('🔬 Search Optimizer: No recency filter needed (timeless content)')

        # Store optimizer decisions in workflow context
        wc = state["workflow_context"]
        wc["refined_search_query"] = refined_query
        wc["search_recency_filter"] = recency_filter
        wc["optimizer_search_mode"] = search_mode
        wc["optimizer_context_size"] = context_size
        wc["optimizer_confidence"] = confidence
        logger.info(
            f"Refined query: {refined_query}, recency: {recency_filter}, mode: {search_mode}, context: {context_size}, conf: {confidence}"
        )

    except Exception as e:
        logger.error(
            f"Error in search_prompt_optimizer_node (with context): {str(e)}. Using original query as fallback."
        )
        wc = state["workflow_context"]
        wc["refined_search_query"] = last_user_message_content
        wc["search_recency_filter"] = None
        wc["optimizer_search_mode"] = None
        wc["optimizer_context_size"] = None
        wc["optimizer_confidence"] = {}

    return state
