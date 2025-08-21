"""
Multi-source analyzer node for determining which search sources to use.
"""

import asyncio
from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    SystemMessage,
    ChatOpenAI,
    MultiSourceAnalysis,
    MULTI_SOURCE_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
)
from utils import get_last_user_message


async def multi_source_analyzer_node(state: ChatState) -> ChatState:
    """Analyzes user query and determines which sources to use for information gathering."""
    logger.info("🔍 Multi-Source Analyzer: Analyzing query to determine source strategy")
    queue_status(state.get("thread_id"), "Analyzing information needs...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible

    # Get the last user message
    last_message = get_last_user_message(state.get("messages", []))

    if not last_message:
        # Default to chat if no user message found
        state["intent"] = "chat"
        state["selected_sources"] = []
        state["routing_analysis"] = {"intent": "chat", "reason": "No user message found", "sources": []}
        logger.info("🔍 Multi-Source Analyzer: No user message found, defaulting to chat")
        return state

    # Log the user message for traceability
    display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
    logger.info(f'🔍 Multi-Source Analyzer: Analyzing query: "{display_msg}"')

    # Initialize the model for analysis
    analyzer_llm = ChatOpenAI(
        model=config.ROUTER_MODEL,  # Use same model as router
        temperature=0.0,  # Keep deterministic
        max_tokens=200,  # Slightly longer for source selection
        api_key=config.OPENAI_API_KEY,
    )

    # Create a structured output model
    structured_analyzer = analyzer_llm.with_structured_output(MultiSourceAnalysis)

    try:
        history_messages = state.get("messages", [])

        # Create the system prompt for analysis - include memory context if available
        memory_context = state.get("memory_context")
        memory_context_section = ""
        if memory_context:
            memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
            logger.debug("🔍 Multi-Source Analyzer: Including memory context in analysis")
        else:
            logger.debug("🔍 Multi-Source Analyzer: No memory context available")

        # Create system message with analysis instructions
        system_message = SystemMessage(
            content=MULTI_SOURCE_SYSTEM_PROMPT.format(
                current_time=get_current_datetime_str(), memory_context_section=memory_context_section
            )
        )

        # Build the complete message list for the analyzer
        analyzer_messages = [system_message] + history_messages

        # If no conversation history exists, add the current user message
        if not history_messages and last_message:
            analyzer_messages.append(HumanMessage(content=last_message))

        logger.debug(f"Multi-source analyzer using {len(analyzer_messages)-1} context messages")

        # Invoke the structured analyzer
        analysis_result = structured_analyzer.invoke(analyzer_messages)

        # Extract results
        intent = analysis_result.intent.lower()
        reason = analysis_result.reason
        sources = analysis_result.sources

        # Validate intent
        if intent not in ["chat", "search", "analysis"]:
            intent = "chat"  # Default to chat for invalid intents

        # Validate and filter sources (only applies to search intent)
        if intent == "search":
            valid_sources = ["search", "academic_search", "social_search", "medical_search"]
            sources = [s for s in sources if s in valid_sources]
            
            # For search intent, ensure we have at least one source
            if not sources:
                sources = ["search"]  # Default fallback
                logger.info("🔍 Multi-Source Analyzer: No valid sources selected, defaulting to general search")
        else:
            # For chat and analysis intents, no sources are needed
            sources = []

        # Limit to max 3 sources to control costs
        if len(sources) > 3:
            sources = sources[:3]
            logger.info(f"🔍 Multi-Source Analyzer: Limited to 3 sources: {sources}")

        # Store results in state
        state["intent"] = intent
        state["selected_sources"] = sources
        state["routing_analysis"] = {
            "intent": intent,
            "reason": reason,
            "sources": sources,
            "model_used": config.ROUTER_MODEL,
            "context_messages_used": len(analyzer_messages) - 1,
        }

        logger.info(f"🔍 Multi-Source Analyzer: Intent '{intent}' with sources: {sources}")
        logger.debug(f"Analysis reason: {reason}")

    except Exception as e:
        # Error handling with fallback to chat
        logger.error(f"Error in multi_source_analyzer_node: {str(e)}")
        state["intent"] = "chat"
        state["selected_sources"] = []
        state["routing_analysis"] = {"intent": "chat", "reason": f"Error: {str(e)}", "sources": []}
        logger.info("🔍 Multi-Source Analyzer: Exception occurred, defaulting to chat")

    return state