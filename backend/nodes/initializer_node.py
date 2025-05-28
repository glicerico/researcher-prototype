"""
Initializer node for setting up user, conversation, and state.
"""
from nodes.base import (
    ChatState, 
    logger, 
    config,
    user_manager,
    conversation_manager,
    convert_state_messages_to_langchain
)


def initializer_node(state: ChatState) -> ChatState:
    """Handles user, conversation, and initial state setup."""
    logger.info("🔄 Initializer: Setting up user and conversation state")
    
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
            
    # Handle conversation management
    conversation_id = state.get("conversation_id")
    if not conversation_id or not conversation_manager.get_conversation(user_id, conversation_id):
        # Create a new conversation
        conversation_id = conversation_manager.create_conversation(user_id, {
            "name": f"Conversation {conversation_manager.list_conversations(user_id).__len__() + 1}",
            "model": state.get("model", config.DEFAULT_MODEL)
        })
        state["conversation_id"] = conversation_id
        logger.info(f"Created new conversation: {conversation_id}")
    
    # Store the input messages in the conversation
    conversation_manager.add_messages(user_id, conversation_id, state["messages"])
    
    # Convert messages to LangChain format once for the entire workflow
    state["langchain_messages"] = convert_state_messages_to_langchain(
        state["messages"], include_system=False
    )
    logger.info(f"🔄 Initializer: Converted {len(state.get('langchain_messages', []))} messages to LangChain format")
    
    return state 