"""
Initializer node for setting up user and state.
"""
from langchain_core.messages import trim_messages
from nodes.base import (
    ChatState, 
    logger, 
    config,
    user_manager
)


def initializer_node(state: ChatState) -> ChatState:
    """Handles user and initial state setup."""
    logger.info("🔄 Initializer: Setting up user state")
    
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