"""
Initializer node for setting up user, conversation, and state.
"""
import os
from typing import List, Dict, Any
from nodes.base import (
    ChatState, 
    logger, 
    user_manager,
    conversation_manager
)
from storage.pinecone_manager import PineconeManager
import config

# Initialize the Pinecone manager
pinecone_manager = PineconeManager()

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
    
    # Handle long-term memory management
    if pinecone_manager.is_available():
        handle_long_term_memory(user_id, conversation_id)
    
    return state 

def handle_long_term_memory(user_id: str, conversation_id: str) -> None:
    """
    Manage long-term memory by storing older messages in Pinecone.
    
    Args:
        user_id: The ID of the user
        conversation_id: The ID of the conversation
    """
    # Get STM limit from config
    stm_limit = config.STM_LIMIT
    
    # Get all messages for this conversation
    all_messages = conversation_manager.get_messages(user_id, conversation_id)
    
    # Count total number of messages
    message_count = len(all_messages)
    
    # If we have more messages than the STM limit, move oldest to LTM
    if message_count > stm_limit:
        # Calculate how many messages to move to LTM
        messages_to_move_count = message_count - stm_limit
        
        # Get the messages to move (oldest first)
        messages_to_move = all_messages[:messages_to_move_count]
        
        # Add conversation_id to message metadata for future reference
        for msg in messages_to_move:
            if "metadata" not in msg:
                msg["metadata"] = {}
            msg["metadata"]["conversation_id"] = conversation_id
        
        # Store messages in Pinecone
        success = pinecone_manager.store_messages(user_id, messages_to_move)
        
        if success:
            logger.info(f"Moved {len(messages_to_move)} messages to long-term memory for user {user_id}")
            
            # Create new conversation without the moved messages
            new_conversation = conversation_manager.get_conversation(user_id, conversation_id)
            new_conversation["messages"] = all_messages[messages_to_move_count:]
            
            # Update the conversation with the trimmed message list
            conversation_manager.storage.write(
                conversation_manager._get_conversation_path(user_id, conversation_id),
                new_conversation
            ) 