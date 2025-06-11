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
    FormattedResponse,
    RESPONSE_RENDERER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)


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
    
    # Create structured output model
    structured_renderer = renderer_llm.with_structured_output(FormattedResponse)
    
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
        # Process the response with the structured renderer
        formatted_result = structured_renderer.invoke(renderer_messages)
        
        # Extract the formatted response and any follow-up questions
        formatted_response = formatted_result.main_response
        sources = formatted_result.sources
        follow_up_questions = formatted_result.follow_up_questions
        
        # If there are sources, append them to the formatted response
        if sources and len(sources) > 0:
            formatted_response += "\n\n**Sources:**\n"
            for source in sources:
                formatted_response += f"- {source}\n"
        
        # If there are follow-up questions, append them to the formatted response
        if follow_up_questions and len(follow_up_questions) > 0:
            formatted_response += "\n\n"
            for i, question in enumerate(follow_up_questions, 1):
                formatted_response += f"{i}. {question}\n"
        
        # Log the formatted response
        display_formatted = formatted_response[:75] + "..." if len(formatted_response) > 75 else formatted_response
        logger.info(f"✨ Renderer: Produced formatted response: \"{display_formatted}\"")
        
        logger.debug(f"Renderer processed response. Original length: {len(raw_response)}, Formatted length: {len(formatted_response)}")
        
        # Create the final assistant message
        assistant_message = AIMessage(content=formatted_response)
        
        # Add the rendered response to the messages in state
        state["messages"].append(assistant_message)
            
    except Exception as e:
        logger.error(f"Error in response_renderer_node: {str(e)}", exc_info=True)
        # If rendering fails, use the raw response as a fallback
        state["messages"].append(AIMessage(content=raw_response))
    
    return state 