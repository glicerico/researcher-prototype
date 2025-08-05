"""
Integrator node that combines all available information to generate a coherent response.
"""

import asyncio
from nodes.base import (
    ChatState,
    logger,
    SystemMessage,
    ChatOpenAI,
    INTEGRATOR_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
)
from utils import get_last_user_message

# Remove the context template imports
# from prompts import SEARCH_CONTEXT_TEMPLATE, ANALYSIS_CONTEXT_TEMPLATE, MEMORY_CONTEXT_TEMPLATE


async def integrator_node(state: ChatState) -> ChatState:
    """Core thinking component that integrates all available context and generates a response."""
    logger.info("🧠 Integrator: Processing all contextual information")
    queue_status(state.get("thread_id"), "Integrating information...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible
    current_time_str = get_current_datetime_str()
    model = state.get("model", config.DEFAULT_MODEL)
    temperature = state.get("temperature", 0.7)
    max_tokens = state.get("max_tokens", 1000)

    # Get last user message for logging
    last_message = get_last_user_message(state.get("messages", []))

    if last_message:
        display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
        logger.info(f'🧠 Integrator: Processing query: "{display_msg}"')

    # Build context section for system prompt
    context_sections = []

    # Add memory context first if available
    memory_context = state.get("memory_context")
    memory_context_section = ""
    if memory_context:
        memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
        logger.info("🧠 Integrator: Including memory context from previous conversations")
    else:
        logger.debug("🧠 Integrator: No memory context available")

    # Add search results to context if available
    search_results_data = state.get("module_results", {}).get("search", {})
    if search_results_data.get("success", False):
        search_result_text = search_results_data.get("result", "")
        if search_result_text:
            citations = search_results_data.get("citations", [])  # List of URL strings
            search_sources = search_results_data.get("search_results", [])  # List of objects

            # --- Data for Renderer ---
            # Pass the raw citation data directly to the renderer.
            state["workflow_context"]["citations"] = citations
            state["workflow_context"]["search_sources"] = search_sources
            logger.info("🧠 Integrator: Passing raw citation data and sources to the renderer.")

            # --- Context for Integrator LLM ---
            # Build a simple, clean context for the integrator's LLM prompt.
            # The search_result_text already has [n] markers. We pass it as-is.
            search_context = f"CURRENT INFORMATION FROM WEB SEARCH:\nThe following text was retrieved from a web search. It contains citation markers like [1], [2], etc.\n\n---\n\n{search_result_text}\n\n---\n\nUse this information to answer the user's query, making sure to preserve the citation markers as they are."
            context_sections.append(search_context)
            logger.info("🧠 Integrator: Added search results with original citation markers to system context")

    # Add analysis results to context if available
    analysis_results = state.get("module_results", {}).get("analyzer", {})
    if analysis_results.get("success", False):
        analysis_result_text = analysis_results.get("result", "")
        if analysis_result_text:
            # Directly construct the analysis context string
            analysis_context = f"ANALYTICAL INSIGHTS:\nThe following analysis was performed related to the user's query:\n\n{analysis_result_text}\n\nIncorporate these insights naturally into your response where relevant."
            context_sections.append(analysis_context)
            logger.info("🧠 Integrator: Added analysis results to system context")

    # Combine all context sections
    context_section = "\n\n".join(context_sections) if context_sections else ""

    # Create enhanced system message with context
    system_message_content = INTEGRATOR_SYSTEM_PROMPT.format(
        current_time=current_time_str, memory_context_section=memory_context_section, context_section=context_section
    )

    # Initialize the model
    llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens, api_key=config.OPENAI_API_KEY)

    # Get the messages and add system message
    messages_for_llm = [SystemMessage(content=system_message_content)]
    messages_for_llm.extend(state.get("messages", []))

    # Log the system prompt for debugging (truncated)
    system_prompt_preview = (
        system_message_content[:200] + "..." if len(system_message_content) > 200 else system_message_content
    )
    logger.info(f"🧠 Integrator: System prompt preview: {system_prompt_preview}")

    try:
        logger.debug(f"Sending {len(messages_for_llm)} messages to Integrator")
        # Create a chat model with specified parameters
        response = llm.invoke(messages_for_llm)
        logger.debug(f"Received response from Integrator: {response}")

        # Log the response for traceability
        display_response = response.content[:75] + "..." if len(response.content) > 75 else response.content
        logger.info(f'🧠 Integrator: Generated response: "{display_response}"')

        # Store the Integrator's response in the workflow context for the renderer
        state["workflow_context"]["integrator_response"] = response.content

        # Also store in module_results for consistency
        state["module_results"]["integrator"] = response.content

    except Exception as e:
        logger.error(f"Error in integrator_node: {str(e)}", exc_info=True)
        # Store the error in workflow context
        state["workflow_context"]["integrator_error"] = str(e)
        state["workflow_context"]["integrator_response"] = f"I encountered an error processing your request: {str(e)}"

    return state
