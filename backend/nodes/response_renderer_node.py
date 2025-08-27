"""
Response renderer node that formats and enhances the raw response.
"""

import asyncio
from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ChatOpenAI,
    RESPONSE_RENDERER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
    personalization_manager,
)
from llm_models import FormattedResponse
from services.citation_processor import citation_processor


async def response_renderer_node(state: ChatState) -> ChatState:
    """Post-processes the LLM output to enforce style, insert follow-up suggestions, and apply user persona settings."""
    logger.info("✨ Renderer: Post-processing final response")
    queue_status(state.get("thread_id"), "Rendering response...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible
    logger.debug("Response Renderer node processing output")
    current_time_str = get_current_datetime_str()

    # Get the raw response from the Integrator
    raw_response = state.get("workflow_context", {}).get("integrator_response", "")

    if not raw_response:
        error = state.get("workflow_context", {}).get("integrator_error", "Unknown error")
        logger.error(f"No response from Integrator to render. Error: {error}")
        state["messages"].append(
            AIMessage(content=f"I apologize, but I encountered an error generating a response: {error}")
        )
        return state

    # Retrieve enhanced citation and source data from the workflow context
    unified_citations = state.get("workflow_context", {}).get("unified_citations", [])
    citations = state.get("workflow_context", {}).get("citations", [])  # Fallback for Perplexity
    search_sources = state.get("workflow_context", {}).get("search_sources", [])
    successful_sources = state.get("workflow_context", {}).get("successful_sources", [])
    source_failures = state.get("workflow_context", {}).get("source_failures", [])
    failure_note = state.get("workflow_context", {}).get("failure_note", "")
    


    # Log the raw response
    display_raw = raw_response[:75] + "..." if len(raw_response) > 75 else raw_response
    logger.info(f'✨ Renderer: Processing raw response: "{display_raw}"')

    # Get personality settings to apply to the response
    personality = state.get("personality") or {}
    style = personality.get("style", "helpful")
    tone = personality.get("tone", "friendly")
    
    # Get personalization context for user preferences
    user_id = state.get("user_id")
    personalization_context = {}
    if user_id:
        try:
            logger.info(f"✨ Renderer: Retrieving personalization context for user {user_id}")
            personalization_context = personalization_manager.get_personalization_context(user_id)
            logger.debug(f"✨ Renderer: ✅ Personalization context retrieved for user {user_id}")
        except Exception as e:
            logger.warning(f"✨ Renderer: ⚠️ Could not retrieve personalization context for user {user_id}: {str(e)}")
    else:
        logger.info("✨ Renderer: No user_id found, using default formatting preferences")

    # Get the active module that was used to handle the query
    module_used = state.get("current_module", "chat")

    # Initialize LLM for response rendering
    renderer_llm = ChatOpenAI(
        model=config.DEFAULT_MODEL,
        temperature=0.3,  # Low temperature for more consistent formatting
        max_tokens=1500,  # Allow for extra tokens for formatting and follow-ups
        api_key=config.OPENAI_API_KEY,
    )

    # Extract format preferences from personalization context
    format_prefs = personalization_context.get("format_preferences", {})
    response_length = format_prefs.get("response_length", "medium")
    detail_level = format_prefs.get("detail_level", "balanced")
    formatting_style = format_prefs.get("formatting_style", "structured")
    include_key_insights = format_prefs.get("include_key_insights", True)
    
    # Create a system prompt for the renderer with personalization
    system_message = SystemMessage(
        content=RESPONSE_RENDERER_SYSTEM_PROMPT.format(
            current_time=current_time_str, 
            style=style, 
            tone=tone, 
            module_used=module_used,
            response_length=response_length,
            detail_level=detail_level,
            formatting_style=formatting_style,
            include_key_insights=include_key_insights
        )
    )

    # Prepare the messages for the renderer LLM
    renderer_messages = [system_message]

    # Get the messages and add them for context
    raw_messages = state.get("messages", [])
    if raw_messages:
        # Add conversation history with proper formatting for the renderer
        for msg in raw_messages:
            if isinstance(msg, HumanMessage):
                renderer_messages.append(HumanMessage(content=f"[User Message]: {msg.content}"))
            elif isinstance(msg, AIMessage):
                renderer_messages.append(AIMessage(content=f"[Assistant Response]: {msg.content}"))

    # Add specific message for the raw response to be formatted
    renderer_messages.append(
        HumanMessage(
            content=f"""
    Below is the raw response to be formatted according to the specified guidelines.
    
    [Raw Response]:
    {raw_response}
    """
        )
    )

    try:
        # Create structured output model
        structured_renderer = renderer_llm.with_structured_output(FormattedResponse)

        # Process the response with the renderer
        llm_response = structured_renderer.invoke(renderer_messages)
        stylized_response = llm_response.main_response
        follow_up_questions = llm_response.follow_up_questions

        # Process citations using external citation processor
        final_response = citation_processor.process_citations(
            text=stylized_response,
            unified_citations=unified_citations,
            fallback_citations=citations,
            search_sources=search_sources,
            successful_sources=successful_sources,
            failure_note=failure_note
        )

        # Add follow-up questions to the workflow context to be used in the API response
        if follow_up_questions:
            state["workflow_context"]["follow_up_questions"] = follow_up_questions

        # Log the formatted response with source info
        display_formatted = final_response[:75] + "..." if len(final_response) > 75 else final_response
        source_info = f" (from {len(successful_sources)} sources)" if successful_sources else ""
        logger.info(f'✨ Renderer: Produced formatted response: "{display_formatted}"{source_info}')

        logger.debug(
            f"Renderer processed response. Original length: {len(raw_response)}, Formatted length: {len(final_response)}"
        )

        # Create the final assistant message
        assistant_message = AIMessage(content=final_response)

        # Add the rendered response to the messages in state
        state["messages"].append(assistant_message)

    except Exception as e:
        logger.error(f"Error in response_renderer_node: {str(e)}", exc_info=True)
        # If rendering fails, use the raw response as a fallback
        state["messages"].append(AIMessage(content=raw_response))

    return state
