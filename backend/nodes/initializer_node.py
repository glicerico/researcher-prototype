"""
Initializer node for setting up user and state.
"""
import uuid
from langchain_core.messages import trim_messages
from nodes.base import (
    ChatState, 
    logger, 
    config,
    user_manager,
    zep_manager
)


async def initializer_node(state: ChatState) -> ChatState:
    """Handles user and initial state setup, including session management and memory context retrieval."""
    logger.info("🔄 Initializer: Setting up user state and session")
    
    # Initialize state objects if they don't exist
    state["workflow_context"] = state.get("workflow_context", {})
    state["module_results"] = state.get("module_results", {})
    state["personality"] = state.get("personality", {"style": "helpful", "tone": "friendly"})
    
    # Handle user management - create or get user
    user_id = state.get("user_id")
    if not user_id or not user_manager.user_exists(user_id):
        # Create a new user if needed
        user_id = user_manager.create_user({
            "created_from": "chat_graph",
            "initial_personality": state.get("personality", {})
        })
        state["user_id"] = user_id
        logger.info(f"Created new user: {user_id}")
    else:
        # Update personality from stored preferences if not explicitly provided
        if not state.get("personality"):
            state["personality"] = user_manager.get_personality(user_id)
    
    # Handle session ID generation or retrieval
    session_id = state.get("session_id", None)
    if not session_id:
        # Generate a new session ID for this conversation thread
        session_id = f"{user_id}-{str(uuid.uuid4())[:8]}"
        state["session_id"] = session_id
        logger.info(f"🔄 Initializer: Generated new session ID: {session_id}")
    else:
        logger.info(f"🔄 Initializer: Using provided session ID: {session_id}")
    
    # Retrieve memory context from Zep if available
    memory_context = None
    if zep_manager.is_enabled():
        try:
            logger.info(f"🧠 Initializer: Retrieving memory context for session {session_id}")
            memory_context = await zep_manager.get_memory_context(session_id)
            
            if memory_context:
                logger.info(f"🧠 Initializer: Retrieved memory context from ZEP.")
                # Store in workflow context for debugging/inspection
                state["workflow_context"]["memory_context_retrieved"] = True
            else:
                logger.info("🧠 Initializer: No memory context found for this session")
                state["workflow_context"]["memory_context_retrieved"] = False
                
        except Exception as e:
            logger.error(f"🧠 Initializer: Error retrieving memory context: {str(e)}")
            state["workflow_context"]["memory_context_error"] = str(e)
    else:
        logger.info("🧠 Initializer: Zep is not enabled, skipping memory context retrieval")
    
    # Store memory context in state (will be None if not available)
    state["memory_context"] = memory_context
    
    # Trim messages to keep only the most recent ones within the configured limit
    messages = state.get("messages", [])
    if messages and len(messages) > config.MAX_MESSAGES_IN_STATE:
        logger.info(f"🔄 Initializer: Trimming messages from {len(messages)} to {config.MAX_MESSAGES_IN_STATE}")
        
        # Use trim_messages to properly trim while maintaining valid chat history
        trimmed_messages = trim_messages(
            messages,
            max_tokens=config.MAX_MESSAGES_IN_STATE,
            strategy="last",  # Keep the most recent messages
            token_counter=len,  # Use message count instead of token count
            include_system=True,  # Keep system messages if present
            start_on="human",  # Ensure valid chat history starts with human message
            allow_partial=False  # Don't allow partial messages
        )
        
        state["messages"] = trimmed_messages
        logger.info(f"🔄 Initializer: Kept {len(state['messages'])} most recent messages")
    else:
        logger.info(f"🔄 Initializer: Processing {len(messages)} messages (within limit)")
    
    return state 