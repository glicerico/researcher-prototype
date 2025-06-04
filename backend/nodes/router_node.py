"""
Router node for analyzing and classifying user messages.
"""
from nodes.base import (
    ChatState, 
    logger, 
    HumanMessage, 
    AIMessage, 
    SystemMessage,
    ChatOpenAI, 
    RoutingAnalysis,
    ROUTER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str
)

# Import the memory context template
from prompts import MEMORY_CONTEXT_TEMPLATE


def router_node(state: ChatState) -> ChatState:
    """Uses a lightweight LLM to analyze the user's message and determine routing."""
    logger.info("🔀 Router: Analyzing message to determine processing path")
    
    # Get the last user message
    last_message = None
    logger.debug(f"🔀 Router: Length of messages in router: {len(state["messages"])}")
    for msg in reversed(state['messages']):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
            
    if not last_message:
        state["current_module"] = "chat"  # Default to chat module if no user message found
        state["routing_analysis"] = {"decision": "chat", "reason": "No user message found"}
        logger.info("🔀 Router: No user message found, defaulting to chat module")
        return state
    
    # Log the user message for traceability (truncate if too long)
    display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
    logger.info(f"🔀 Router: Processing user message: \"{display_msg}\"")
    
    # Initialize the GPT-3.5-Turbo model for routing
    router_llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.0,  # Keep deterministic
        max_tokens=150,   # Short response is sufficient
        api_key=config.OPENAI_API_KEY
    )
    
    # Create a structured output model
    structured_router = router_llm.with_structured_output(RoutingAnalysis)
    
    try:
        history_messages = state.get("messages", [])
        
        # Create the system prompt for routing - include memory context if available
        memory_context = state.get("memory_context")
        memory_context_section = ""
        if memory_context:
            memory_context_section = MEMORY_CONTEXT_TEMPLATE.format(memory_context=memory_context)
            logger.debug("🔀 Router: Including memory context in routing decision")
        else:
            logger.debug("🔀 Router: No memory context available")
        
        # Create system message with routing instructions
        system_message = SystemMessage(content=ROUTER_SYSTEM_PROMPT.format(
            current_time=get_current_datetime_str(),
            memory_context_section=memory_context_section
        ))
        
        # Build the complete message list for the router
        router_messages = [system_message] + history_messages
        
        # If no conversation history exists, add the current user message
        if not history_messages and last_message:
            router_messages.append(HumanMessage(content=last_message))
        
        logger.debug(f"Router using {len(router_messages)-1} context messages")
        
        # Invoke the structured router
        routing_result = structured_router.invoke(router_messages)
        
        # routing_result is now a validated Pydantic RoutingAnalysis object
        module = routing_result.decision.lower()
        reason = routing_result.reason
        complexity = routing_result.complexity
        
        # Validate module name
        if module not in ["chat", "search", "analyzer"]:
            module = "chat"  # Default to chat for unrecognized modules
        
        # Set the routing decision
        state["current_module"] = module
        state["routing_analysis"] = {
            "decision": module,
            "reason": reason,
            "complexity": complexity,
            "model_used": config.ROUTER_MODEL,
            "context_messages_used": len(router_messages) - 1  # Excluding system message
        }
        
        logger.info(f"🔀 Router: Selected module '{module}' (complexity: {complexity}) for message: \"{display_msg}\"")
        logger.debug(f"Routing reason: {reason}")
        
    except Exception as e:
        # Single exception handling for all error cases
        logger.error(f"Error in router_node: {str(e)}")
        state["current_module"] = "chat"  # Default fallback
        state["routing_analysis"] = {"decision": "chat", "reason": f"Error: {str(e)}"}
        logger.info("🔀 Router: Exception occurred, defaulting to chat module")
        
    return state 