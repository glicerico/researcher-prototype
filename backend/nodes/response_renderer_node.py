"""
Response renderer node that formats and enhances the raw response.
"""
from nodes.base import (
    ChatState, 
    logger,
    HumanMessage, 
    AIMessage, 
    SystemMessage,
    ChatOpenAI,
    RESPONSE_RENDERER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)
from llm_models import FormattedResponse
from utils import get_last_user_message
import re

def response_renderer_node(state: ChatState) -> ChatState:
    """Post-processes the LLM output to enforce style, insert follow-up suggestions, and apply user persona settings."""
    logger.info("✨ Renderer: Post-processing final response")
    logger.debug("Response Renderer node processing output")
    current_time_str = get_current_datetime_str()
    
    # Get the raw response from the Integrator
    raw_response = state.get("workflow_context", {}).get("integrator_response", "")
    
    if not raw_response:
        error = state.get("workflow_context", {}).get("integrator_error", "Unknown error")
        logger.error(f"No response from Integrator to render. Error: {error}")
        state["messages"].append(AIMessage(
            content=f"I apologize, but I encountered an error generating a response: {error}"
        ))
        return state
    
    # Retrieve citation data from the workflow context
    citations = state.get("workflow_context", {}).get("citations", [])
    search_sources = state.get("workflow_context", {}).get("search_sources", [])
    
    # Log the raw response
    display_raw = raw_response[:75] + "..." if len(raw_response) > 75 else raw_response
    logger.info(f"✨ Renderer: Processing raw response: \"{display_raw}\"")
    
    # Get personality settings to apply to the response
    personality = state.get("personality") or {}
    style = personality.get("style", "helpful")
    tone = personality.get("tone", "friendly")
    
    # Get the active module that was used to handle the query
    module_used = state.get("current_module", "chat")
    
    # Initialize LLM for response rendering
    renderer_llm = ChatOpenAI(
        model=config.DEFAULT_MODEL,
        temperature=0.3,  # Low temperature for more consistent formatting
        max_tokens=1500,  # Allow for extra tokens for formatting and follow-ups 
        api_key=config.OPENAI_API_KEY
    )
    
    # Create a system prompt for the renderer
    system_message = SystemMessage(content=RESPONSE_RENDERER_SYSTEM_PROMPT.format(
        current_time=current_time_str,
        style=style,
        tone=tone,
        module_used=module_used
    ))
    
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
    renderer_messages.append(HumanMessage(content=f"""
    Below is the raw response to be formatted according to the specified guidelines.
    
    [Raw Response]:
    {raw_response}
    """))
    
    try:
        # Create structured output model
        structured_renderer = renderer_llm.with_structured_output(FormattedResponse)

        # Process the response with the renderer
        llm_response = structured_renderer.invoke(renderer_messages)
        stylized_response = llm_response.main_response
        follow_up_questions = llm_response.follow_up_questions

        # Create the URL map from the raw citations list
        citation_url_map = {i + 1: url for i, url in enumerate(citations)}
        
        # Replace citation markers [n] with markdown hyperlinks
        def replace_citation(match):
            citation_num = int(match.group(1))
            url = citation_url_map.get(citation_num)
            if url:
                # Wrap the citation number in another set of brackets to keep them in the link text
                return f"[[{citation_num}]]({url})"
            return match.group(0) # Return original if no URL found
        
        # Apply the replacement to the stylized response
        final_response = re.sub(r'\[(\d+)\]', replace_citation, stylized_response)
        
        # Format and append the sources section
        if search_sources:
            sources_list = []
            for s in search_sources:
                title = s.get("title", "Unknown Title")
                url = s.get("url")
                if url:
                    sources_list.append(f"- [{title}]({url})")
            
            if sources_list:
                sources_section = "\n\n**Sources:**\n" + "\n".join(sources_list)
                final_response += sources_section
        
        # Add follow-up questions to the workflow context to be used in the API response
        if follow_up_questions:
            state["workflow_context"]["follow_up_questions"] = follow_up_questions

        # Log the formatted response
        display_formatted = final_response[:75] + "..." if len(final_response) > 75 else final_response
        logger.info(f"✨ Renderer: Produced formatted response: \"{display_formatted}\"")
        
        logger.debug(f"Renderer processed response. Original length: {len(raw_response)}, Formatted length: {len(final_response)}")
        
        # Create the final assistant message
        assistant_message = AIMessage(content=final_response)
        
        # Add the rendered response to the messages in state
        state["messages"].append(assistant_message)
            
    except Exception as e:
        logger.error(f"Error in response_renderer_node: {str(e)}", exc_info=True)
        # If rendering fails, use the raw response as a fallback
        state["messages"].append(AIMessage(content=raw_response))
    
    return state 