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
    SEARCH_RESULTS_TEMPLATE,
    ANALYSIS_RESULTS_TEMPLATE,
    config,
    get_current_datetime_str
)

# Define the template for memory context
MEMORY_CONTEXT_TEMPLATE = """
--- MEMORY CONTEXT ---
The following information is retrieved from long-term memory and might be relevant to the current conversation:

{memory_context_text}

Remember to consider this historical context when responding.
"""

def integrator_node(state: ChatState) -> ChatState:
    """Core thinking component that integrates all available context and generates a response."""
    logger.info("🧠 Integrator: Processing all contextual information")
    current_time_str = get_current_datetime_str()
    model = state.get("model", config.DEFAULT_MODEL)
    temperature = state.get("temperature", 0.7)
    max_tokens = state.get("max_tokens", 1000)
    
    # Get last user message for logging
    last_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_message = msg["content"]
            break
            
    if last_message:
        display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
        logger.info(f"🧠 Integrator: Processing query: \"{display_msg}\"")
        
    # Create system message based on personality if available
    system_message_content = INTEGRATOR_SYSTEM_PROMPT.format(
        current_time=current_time_str
    )
    
    # Initialize the model
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=config.OPENAI_API_KEY
    )
    
    # Convert dict messages to LangChain message objects
    langchain_messages = []
    
    # Add system message first
    langchain_messages.append(SystemMessage(content=system_message_content))
    
    # Process the conversation history
    for msg in state["messages"]:
        role = msg["role"]
        content = msg["content"]
        
        # Skip system messages as we've already added our own
        if role == "system":
            continue
        
        # Trim whitespace from content
        if isinstance(content, str):
            content = content.strip()
        
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
            
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            logger.warning(f"Unknown message role: {role}")
    
    # Add memory context if available
    memory_context = state.get("memory_context", {})
    if memory_context.get("success", False) and memory_context.get("memories"):
        memories = memory_context.get("memories", [])
        if memories:
            # Format the memories
            memory_texts = []
            for memory in memories:
                # Skip if content is empty
                if not memory.get("content"):
                    continue
                    
                # Format the memory
                memory_type = memory.get("metadata", {}).get("memory_type", "unknown")
                memory_role = memory.get("metadata", {}).get("role", "unknown")
                
                if memory_type == "search":
                    query = memory.get("metadata", {}).get("query", "")
                    memory_texts.append(f"Search for '{query}':\n{memory.get('content')}")
                elif memory_type == "analysis":
                    analysis_type = memory.get("metadata", {}).get("analysis_type", "")
                    memory_texts.append(f"Analysis ({analysis_type}):\n{memory.get('content')}")
                else:
                    memory_texts.append(f"{memory_role.capitalize()}: {memory.get('content')}")
            
            # Add memories to the context
            if memory_texts:
                memory_context_text = "\n---\n".join(memory_texts)
                memory_msg = MEMORY_CONTEXT_TEMPLATE.format(
                    memory_context_text=memory_context_text
                )
                langchain_messages.append(AIMessage(content=memory_msg))
                logger.info("🧠 Integrator: Added memory context to prompt")
    
    # Add search/analysis results after the last message, if available
    search_results = state.get("module_results", {}).get("search", {})
    if search_results.get("success", False):
        search_result_text = search_results.get("result", None)
        if search_result_text:
            # Add search results directly to the prompt
            search_msg = SEARCH_RESULTS_TEMPLATE.format(
                search_result_text=search_result_text
            )
            langchain_messages.append(AIMessage(content=search_msg))
            logger.info("🧠 Integrator: Added search results to prompt")
        
    analysis_results = state.get("module_results", {}).get("analyzer", {})
    if analysis_results.get("success", False):
        analysis_result_text = analysis_results.get("result", None)
        if analysis_result_text:
            # Add analysis results directly to the prompt
            analysis_msg = ANALYSIS_RESULTS_TEMPLATE.format(
                analysis_result_text=analysis_result_text
            )
            langchain_messages.append(AIMessage(content=analysis_msg))
            logger.info("🧠 Integrator: Added analytical insights to prompt")
                
    # Log the full prompt being sent to the LLM for debugging
    prompt_log = "\n---\n".join([
        f"ROLE: {msg.type}\nCONTENT: {msg.content}"
        for msg in langchain_messages
    ])
    logger.info(f"🧠 Integrator: Full prompt being sent to LLM:\n{prompt_log}")
    
    # Generate the response
    try:
        response = llm.invoke(langchain_messages)
        response_text = response.content
        
        # Truncate for logging
        display_response = response_text[:75] + "..." if len(response_text) > 75 else response_text
        logger.info(f"🧠 Integrator: Generated response: \"{display_response}\"")
        
        # Add the response to the state
        state["module_results"]["integrator"] = {
            "success": True,
            "response": response_text
        }
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        state["module_results"]["integrator"] = {
            "success": False,
            "error": str(e)
        }
    
    return state 