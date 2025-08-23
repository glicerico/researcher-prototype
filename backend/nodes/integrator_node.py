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
        logger.info("🧠 Integrator: ✅ Including memory context from previous conversations")
    else:
        logger.debug("🧠 Integrator: ⚠️ No memory context available")

    # Multi-source processing with cross-referencing
    source_config = {
        "search": {"name": "Web Search", "type": "current_info"},
        "academic_search": {"name": "Academic Papers", "type": "scholarly"},
        "social_search": {"name": "Social Media", "type": "sentiment"},
        "medical_search": {"name": "Medical Research", "type": "clinical"},
        "analyzer": {"name": "Analysis", "type": "analytical"}
    }
    
    all_citations = []
    all_search_sources = []
    successful_sources = []
    failed_sources = []
    
    # Process each potential source
    for source, source_info in source_config.items():
        search_results_data = state.get("module_results", {}).get(source, {})
        
        if search_results_data.get("success", False):
            # Prefer reviewer-filtered raw results if available to avoid LLM regeneration drift
            filtered_items_text = ""
            try:
                raw = search_results_data.get("raw_results", {}) or {}
                all_items = raw.get("results")
                if all_items and search_results_data.get("filtered_by_reviewer"):
                    # Use only the items selected by the reviewer
                    selected_indices = search_results_data.get("selected_indices", [])
                    if selected_indices:
                        # Build a concise list from only the selected items
                        lines = []
                        for display_idx, original_idx in enumerate(selected_indices, 1):
                            if original_idx < len(all_items):
                                item = all_items[original_idx]
                                title = (
                                    item.get("title")
                                    or item.get("story_title")
                                    or item.get("paperTitle")
                                    or "(no title)"
                                )
                                url = (
                                    item.get("url")
                                    or item.get("story_url")
                                    or (item.get("openAccessPdf", {}) or {}).get("url")
                                    or ""
                                )
                                snippet = item.get("text") or item.get("abstract") or ""
                                if snippet and len(snippet) > 220:
                                    snippet = snippet[:220] + "..."
                                parts = [f"{display_idx}. {title}"]
                                if snippet:
                                    parts.append(f" — {snippet}")
                                if url:
                                    parts.append(f"\n   🔗 {url}")
                                lines.append("".join(parts))
                        filtered_items_text = "\n".join(lines)
                        logger.info(f"🧠 Integrator: Using {len(selected_indices)} reviewer-filtered items from {source}")
                    else:
                        # No items selected by reviewer - use empty content
                        filtered_items_text = ""
                        logger.info(f"🧠 Integrator: No relevant items selected by reviewer for {source}")
            except Exception:
                filtered_items_text = ""

            search_result_text = filtered_items_text or search_results_data.get("content", "")
            if search_result_text:
                # Build source-specific context
                source_name = source_info["name"]
                source_type = source_info["type"]
                
                # Create context with source information
                search_context = f"""INFORMATION FROM {source_name.upper()} (Type: {source_type}):
{search_result_text}
"""
                context_sections.append(search_context)
                successful_sources.append({"name": source_name, "type": source_type})
                logger.info(f"🧠 Integrator: ✅ Added {source_name} results to context")
                
                # Collect citations and sources for renderer
                citations = search_results_data.get("citations", [])
                search_sources_data = search_results_data.get("search_sources", [])
                all_citations.extend(citations)
                all_search_sources.extend(search_sources_data)
        else:
            # Track failed sources for graceful degradation reporting
            if source in state.get("selected_sources", []):
                failed_sources.append(source_config[source]["name"])
                logger.warning(f"🧠 Integrator: ⚠️ {source_config[source]['name']} failed or returned no results")
    
    # Add multi-source analysis summary to context
    if len(successful_sources) > 1:
        source_summary = f"""
MULTI-SOURCE ANALYSIS SUMMARY:
Successfully retrieved information from {len(successful_sources)} sources: {', '.join([s['name'] for s in successful_sources])}.
When synthesizing, cross-reference information between sources and highlight areas where sources agree or provide complementary information.
"""
        context_sections.insert(0, source_summary)
        logger.info(f"🧠 Integrator: 📊 Multi-source analysis with {len(successful_sources)} sources")
    elif len(successful_sources) == 1:
        logger.info(f"🧠 Integrator: Single source analysis: {successful_sources[0]['name']}")
    
    # Report any failures (graceful degradation)  
    if failed_sources:
        failure_note = f"\nNOTE: Some sources were unavailable: {', '.join(failed_sources)}. Response is based on available sources only."
        state["workflow_context"]["source_failures"] = failed_sources
        state["workflow_context"]["failure_note"] = failure_note
        logger.info(f"🧠 Integrator: ⚠️ {len(failed_sources)} sources failed, graceful degradation in effect")
    
    # Pass enhanced citation data and source metadata to renderer
    if all_citations or all_search_sources:
        state["workflow_context"]["citations"] = all_citations
        state["workflow_context"]["search_sources"] = all_search_sources
        state["workflow_context"]["successful_sources"] = successful_sources
        logger.info(f"🧠 Integrator: 📚 Passing {len(all_citations)} citations from {len(successful_sources)} sources to renderer")

    # Add analysis results to context if available
    analysis_results = state.get("module_results", {}).get("analyzer", {})
    if analysis_results.get("success", False):
        analysis_result_text = analysis_results.get("result", "")
        if analysis_result_text:
            # Directly construct the analysis context string
            analysis_context = f"ANALYTICAL INSIGHTS:\nThe following analysis was performed related to the user's query:\n\n{analysis_result_text}\n\nIncorporate these insights naturally into your response where relevant."
            context_sections.append(analysis_context)
            logger.info("🧠 Integrator: ✅ Added analysis results to system context")

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
        logger.info(f'🧠 Integrator: ✅ Generated response: "{display_response}"')

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
