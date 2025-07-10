"""
Integrator node that combines all available information to generate a coherent response.
"""
from nodes.base import (
    ChatState, 
    logger,
    SystemMessage,
    ChatOpenAI,
    INTEGRATOR_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)
from utils import get_last_user_message

# Remove the context template imports
# from prompts import SEARCH_CONTEXT_TEMPLATE, ANALYSIS_CONTEXT_TEMPLATE, MEMORY_CONTEXT_TEMPLATE


def integrator_node(state: ChatState) -> ChatState:
    """Core thinking component that integrates all available context and generates a response."""
    logger.info("🧠 Integrator: Processing all contextual information")
    current_time_str = get_current_datetime_str()
    model = state.get("model", config.DEFAULT_MODEL)
    temperature = state.get("temperature", 0.7)
    max_tokens = state.get("max_tokens", 1000)
    
    # Get last user message for logging
    last_message = get_last_user_message(state.get("messages", []))
            
    if last_message:
        display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
        logger.info(f"🧠 Integrator: Processing query: \"{display_msg}\"")
    
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
            search_sources = search_results_data.get("search_results", []) # List of objects

            # Create a mapping from citation index (1-based) to URL
            citation_url_map = {i + 1: url for i, url in enumerate(citations)}

            # Replace [n] with markdown links in the main text
            import re
            def replace_citation(match):
                citation_num = int(match.group(1))
                url = citation_url_map.get(citation_num)
                if url:
                    return f"[{citation_num}]({url})"
                return match.group(0)  # Return original if no URL found

            if isinstance(search_result_text, str):
                search_result_text = re.sub(r'\[(\d+)\]', replace_citation, search_result_text)

            # Create a URL-to-Title map from search_sources to enrich the citations list
            url_to_title_map = {s.get("url"): s.get("title", "Unknown Title") for s in search_sources if s.get("url")}
            
            # Format citations section with markdown links
            citations_section = ""
            if citations:
                citations_list = []
                for i, url in enumerate(citations):
                    title = url_to_title_map.get(url, f"Source [{i+1}]")
                    citations_list.append(f"- [{title}]({url})")
                if citations_list:
                    citations_section = f"CITATIONS:\n" + "\n".join(citations_list)
                    logger.info(f"🧠 Integrator: Including {len(citations_list)} citations")

            # Format sources section (this might be redundant but retained for completeness)
            sources_section = ""
            if search_sources:
                sources_list = []
                for s in search_sources:
                    title = s.get("title", "Unknown Title")
                    url = s.get("url")
                    if url:
                        sources_list.append(f"- [{title}]({url})")
                if sources_list:
                    sources_section = f"SOURCES:\n" + "\n".join(sources_list)
                    logger.info(f"🧠 Integrator: Including {len(sources_list)} source references")
            
            # Directly construct the search context string
            search_context = f"CURRENT INFORMATION FROM WEB SEARCH:\nThe following information was retrieved from a recent web search related to the user's query:\n\n{search_result_text}\n\n{citations_section}\n\n{sources_section}\n\nUse this information to provide accurate, up-to-date responses. When referencing specific facts or claims, cite the relevant sources using markdown hyperlinks."
            context_sections.append(search_context)
            logger.info("🧠 Integrator: Added enhanced search results with hyperlinked citations and sources to system context")
    
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
        current_time=current_time_str,
        memory_context_section=memory_context_section,
        context_section=context_section
    )
    
    # Initialize the model
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=config.OPENAI_API_KEY
    )
    
    # Get the messages and add system message
    messages_for_llm = [SystemMessage(content=system_message_content)]
    messages_for_llm.extend(state.get("messages", []))

    # Log the system prompt for debugging (truncated)
    system_prompt_preview = system_message_content[:200] + "..." if len(system_message_content) > 200 else system_message_content
    logger.info(f"🧠 Integrator: System prompt preview: {system_prompt_preview}")
    
    try:
        logger.debug(f"Sending {len(messages_for_llm)} messages to Integrator")
        # Create a chat model with specified parameters
        response = llm.invoke(messages_for_llm)
        logger.debug(f"Received response from Integrator: {response}")
        
        # Log the response for traceability
        display_response = response.content[:75] + "..." if len(response.content) > 75 else response.content
        logger.info(f"🧠 Integrator: Generated response: \"{display_response}\"")
        
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