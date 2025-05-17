"""
Memory node for retrieving context from long-term memory.
"""
from nodes.base import (
    ChatState, 
    logger,
    memory_manager,
    config
)

def memory_retrieval_node(state: ChatState) -> ChatState:
    """Retrieves relevant memories based on the user's message."""
    logger.info("🧠 Memory: Retrieving relevant memories")
    
    # Skip if memory manager is not configured
    if not memory_manager:
        logger.warning("Memory manager not configured, skipping memory retrieval")
        state["memory_context"] = {"success": False, "error": "Memory manager not configured"}
        return state
    
    user_id = state.get("user_id")
    conversation_id = state.get("conversation_id")
    
    if not user_id or not conversation_id:
        logger.warning("User ID or conversation ID not found in state, skipping memory retrieval")
        state["memory_context"] = {"success": False, "error": "User ID or conversation ID not found"}
        return state
    
    # Get the last user message as the query
    last_user_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break
    
    if not last_user_message:
        logger.warning("No user message found, skipping memory retrieval")
        state["memory_context"] = {"success": False, "error": "No user message found"}
        return state
    
    # Log the query being used for memory retrieval
    display_msg = last_user_message[:75] + "..." if len(last_user_message) > 75 else last_user_message
    logger.info(f"🧠 Memory: Retrieving memories for query: \"{display_msg}\"")
    
    try:
        # Retrieve relevant memories
        memories = memory_manager.get_relevant_memories(
            query=last_user_message,
            user_id=user_id,
            top_k=3,  # Retrieve top 3 relevant memories from LTM
            include_stm=True  # Include short-term memory
        )
        
        # Log the number of memories retrieved
        logger.info(f"🧠 Memory: Retrieved {len(memories)} relevant memories")
        
        # Add retrieved memories to state
        state["memory_context"] = {
            "success": True,
            "memories": memories
        }
        
    except Exception as e:
        logger.error(f"Error retrieving memories: {str(e)}")
        state["memory_context"] = {"success": False, "error": str(e)}
    
    return state

def memory_storage_node(state: ChatState) -> ChatState:
    """Stores messages and results in memory."""
    logger.info("💾 Memory: Storing new information")
    
    # Skip if memory manager is not configured
    if not memory_manager:
        logger.warning("Memory manager not configured, skipping memory storage")
        return state
    
    user_id = state.get("user_id")
    conversation_id = state.get("conversation_id")
    
    if not user_id or not conversation_id:
        logger.warning("User ID or conversation ID not found in state, skipping memory storage")
        return state
    
    # Get the last user message from the messages array (read only)
    last_user_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break
    
    # Get the assistant response from the integrator result
    integrator_result = state.get("module_results", {}).get("integrator", {})
    assistant_response = None
    if integrator_result.get("success", False):
        assistant_response = integrator_result.get("response", "")
    
    # Store user message if found
    if last_user_message:
        try:
            memory_manager.add_to_memory(
                user_id=user_id,
                conversation_id=conversation_id,
                content=last_user_message,
                role="user",
                memory_type="message"
            )
            logger.info("💾 Memory: Stored user message")
        except Exception as e:
            logger.error(f"Error storing user message: {str(e)}")
    
    # Store assistant message if available
    if assistant_response:
        try:
            memory_manager.add_to_memory(
                user_id=user_id,
                conversation_id=conversation_id,
                content=assistant_response,
                role="assistant",
                memory_type="message"
            )
            logger.info("💾 Memory: Stored assistant response")
        except Exception as e:
            logger.error(f"Error storing assistant response: {str(e)}")
    
    # Store search results if available
    search_results = state.get("module_results", {}).get("search", {})
    if search_results.get("success", False):
        search_result_text = search_results.get("result", None)
        search_query = search_results.get("query_used", "")
        
        if search_result_text:
            try:
                memory_manager.add_search_result(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query=search_query,
                    result=search_result_text
                )
                logger.info("💾 Memory: Stored search result")
            except Exception as e:
                logger.error(f"Error storing search result: {str(e)}")
    
    # Store analysis results if available
    analysis_results = state.get("module_results", {}).get("analyzer", {})
    if analysis_results.get("success", False):
        analysis_result_text = analysis_results.get("result", None)
        
        if analysis_result_text:
            try:
                memory_manager.add_analysis_result(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    analysis_type="general",
                    result=analysis_result_text
                )
                logger.info("💾 Memory: Stored analysis result")
            except Exception as e:
                logger.error(f"Error storing analysis result: {str(e)}")
    
    return state 