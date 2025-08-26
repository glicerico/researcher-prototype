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
from utils import get_last_user_message
import re


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
    use_bullet_points = format_prefs.get("use_bullet_points", True)
    include_key_insights = format_prefs.get("include_key_insights", True)
    
    # Extract learned adaptations
    learned_adaptations = personalization_context.get("learned_adaptations", {})
    format_optimizations = learned_adaptations.get("format_optimizations", {})
    prefers_structured = format_optimizations.get("prefers_structured_responses", True)
    optimal_length = format_optimizations.get("optimal_response_length")
    
    # Create a system prompt for the renderer with personalization
    system_message = SystemMessage(
        content=RESPONSE_RENDERER_SYSTEM_PROMPT.format(
            current_time=current_time_str, 
            style=style, 
            tone=tone, 
            module_used=module_used,
            response_length=response_length,
            detail_level=detail_level,
            use_bullet_points=use_bullet_points,
            include_key_insights=include_key_insights,
            prefers_structured=prefers_structured,
            optimal_length=optimal_length or "not specified"
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

        # Create the URL map from unified citations (preferred) or fallback to old citations
        if unified_citations:
            citation_url_map = {i + 1: citation.get("url", "") for i, citation in enumerate(unified_citations)}
        else:
            citation_url_map = {i + 1: url for i, url in enumerate(citations)}

        # Replace citation markers [n] with markdown hyperlinks
        def replace_citation(match):
            citation_num = int(match.group(1))
            url = citation_url_map.get(citation_num)
            if url:
                # Wrap the citation number in another set of brackets to keep them in the link text
                return f"[[{citation_num}]]({url})"
            return match.group(0)  # Return original if no URL found

        # Apply the replacement to the stylized response
        final_response = re.sub(r"\[(\d+)\]", replace_citation, stylized_response)

        # Enhanced sources section with unified citations
        if unified_citations or search_sources or successful_sources:
            sources_section_parts = []
            
            # Add source attribution summary if multiple sources were used
            if len(successful_sources) > 1:
                source_names = [s.get("name", "Unknown") for s in successful_sources]
                attribution = f"\n\n*Information synthesized from {len(successful_sources)} sources: {', '.join(source_names)}*"
                sources_section_parts.append(attribution)
            
            # Add detailed sources list from unified citations (preferred)
            if unified_citations:
                # Group citations by source type
                web_citations = []
                academic_citations = []
                social_citations = []
                medical_citations = []
                
                citation_counter = 1
                
                for citation in unified_citations:
                    title = citation.get("title", "Unknown Title")
                    url = citation.get("url", "")
                    source = citation.get("source", "Unknown")
                    citation_type = citation.get("type", "")
                    
                    if url:
                        # Build rich citation with metadata
                        citation_parts = [f"[{citation_counter}]. [{title}]({url})"]
                        citation_counter += 1
                        
                        # Add source-specific metadata
                        if citation_type == "academic" or citation_type == "scholarly":
                            authors = citation.get("authors", [])
                            year = citation.get("year")
                            venue = citation.get("venue")
                            metadata_parts = []
                            if authors and len(authors) > 0:
                                author_names = [a.get("name", "") for a in authors[:2]]  # First 2 authors
                                if author_names:
                                    metadata_parts.append(f"Authors: {', '.join(author_names)}")
                            if year:
                                metadata_parts.append(f"Year: {year}")
                            if venue:
                                metadata_parts.append(f"Venue: {venue}")
                            if metadata_parts:
                                citation_parts.append(f" — {'; '.join(metadata_parts)}")
                            academic_citations.append("".join(citation_parts))
                        
                        elif citation_type == "clinical":
                            authors = citation.get("authors", [])
                            journal = citation.get("journal")
                            pubdate = citation.get("pubdate")
                            metadata_parts = []
                            if authors and len(authors) > 0:
                                author_names = [a.get("name", "") for a in authors[:2]]
                                if author_names:
                                    metadata_parts.append(f"Authors: {', '.join(author_names)}")
                            if journal:
                                metadata_parts.append(f"Journal: {journal}")
                            if pubdate:
                                metadata_parts.append(f"Published: {pubdate}")
                            if metadata_parts:
                                citation_parts.append(f" — {'; '.join(metadata_parts)}")
                            medical_citations.append("".join(citation_parts))
                        
                        elif citation_type == "sentiment":
                            author = citation.get("author")
                            points = citation.get("points")
                            comments = citation.get("comments")
                            metadata_parts = []
                            if author:
                                metadata_parts.append(f"Author: {author}")
                            if points:
                                metadata_parts.append(f"Points: {points}")
                            if comments:
                                metadata_parts.append(f"Comments: {comments}")
                            if metadata_parts:
                                citation_parts.append(f" — {'; '.join(metadata_parts)}")
                            social_citations.append("".join(citation_parts))
                        
                        elif citation_type == "web":
                            web_citations.append("".join(citation_parts))
                        
                        else:
                            # Default handling for unrecognized citation types
                            logger.warning(f"✨ Renderer: Unknown citation type '{citation_type}' for citation {citation_counter-1}, adding to web citations")
                            web_citations.append("".join(citation_parts))

                # Build sources section with grouped headers
                sources_content_parts = []
                
                if web_citations:
                    sources_content_parts.append("**Web Search:**")
                    sources_content_parts.extend(web_citations)
                
                if academic_citations:
                    if sources_content_parts:
                        sources_content_parts.append("")  # Empty line between sections
                    sources_content_parts.append("**Academic Papers:**")
                    sources_content_parts.extend(academic_citations)
                
                if social_citations:
                    if sources_content_parts:
                        sources_content_parts.append("")
                    sources_content_parts.append("**Social Media:**")
                    sources_content_parts.extend(social_citations)
                
                if medical_citations:
                    if sources_content_parts:
                        sources_content_parts.append("")
                    sources_content_parts.append("**Medical Research:**")
                    sources_content_parts.extend(medical_citations)

                if sources_content_parts:
                    sources_section_parts.append("\n\n**Sources:**\n" + "\n".join(sources_content_parts))
            
            # Fallback to old search_sources format if no unified citations
            elif search_sources:
                sources_list = []
                for i, s in enumerate(search_sources, 1):
                    title = s.get("title", "Unknown Title")
                    url = s.get("url")
                    if url:
                        sources_list.append(f"[{i}]. [{title}]({url})")

                if sources_list:
                    sources_section_parts.append("\n\n**Sources:**\n" + "\n".join(sources_list))
            
            # Add failure notice if any sources failed
            if failure_note:
                sources_section_parts.append(f"\n*{failure_note.strip()}*")
                
            # Only append sources if they exist, so frontend can split them properly
            if sources_section_parts:
                final_response += "".join(sources_section_parts)

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
