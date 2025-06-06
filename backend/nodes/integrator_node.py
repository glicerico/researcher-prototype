"""
Integrator node that combines all available information to generate a coherent response.
"""
from nodes.base import (
    ChatState, 
    logger,
    HumanMessage, 
    AIMessage, 
    SystemMessage,
    ChatOpenAI,
    INTEGRATOR_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)
from utils import get_last_user_message

# Import the context templates
from prompts import SEARCH_CONTEXT_TEMPLATE, ANALYSIS_CONTEXT_TEMPLATE, MEMORY_CONTEXT_TEMPLATE


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
        memory_context_section = MEMORY_CONTEXT_TEMPLATE.format(memory_context=memory_context)
        logger.info("🧠 Integrator: Including memory context from previous conversations")
    else:
        logger.debug("🧠 Integrator: No memory context available")
    
    # Add search results to context if available
    search_results = state.get("module_results", {}).get("search", {})
    if search_results.get("success", False):
        search_result_text = search_results.get("result", "")
        if search_result_text:
            search_context = SEARCH_CONTEXT_TEMPLATE.format(
                search_result_text=search_result_text
            )
            context_sections.append(search_context)
            logger.info("🧠 Integrator: Added search results to system context")
    
    # Add analysis results to context if available
    analysis_results = state.get("module_results", {}).get("analyzer", {})
    if analysis_results.get("success", False):
        analysis_result_text = analysis_results.get("result", "")
        if analysis_result_text:
            analysis_context = ANALYSIS_CONTEXT_TEMPLATE.format(
                analysis_result_text=analysis_result_text
            )
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