"""
Conversation Manager for handling conversation history.
"""

import time
import logging
import uuid
from typing import Dict, Any, List, Optional

from .storage_manager import StorageManager
from .user_manager import UserManager

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Conversation manager for handling conversation history.
    """
    
    def __init__(self, storage_manager: StorageManager, user_manager: UserManager):
        """Initialize the conversation manager with storage and user managers."""
        self.storage = storage_manager
        self.user_manager = user_manager
    
    def _get_conversations_path(self, user_id: str) -> str:
        """Get the path to a user's conversations directory."""
        return f"{self.user_manager._get_user_path(user_id)}/conversations"
    
    def _get_conversation_path(self, user_id: str, conversation_id: str) -> str:
        """Get the path to a specific conversation file."""
        return f"{self._get_conversations_path(user_id)}/{conversation_id}.json"
    
    def create_conversation(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new conversation for a user.
        
        Args:
            user_id: The ID of the user
            metadata: Optional metadata for the conversation
            
        Returns:
            The newly created conversation ID
        """
        # Check if user exists
        if not self.user_manager.user_exists(user_id):
            logger.error(f"User {user_id} not found")
            return ""
        
        # Generate a unique conversation ID
        conversation_id = str(uuid.uuid4())
        
        # Create conversation data
        conversation = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "created_at": time.time(),
            "updated_at": time.time(),
            "metadata": metadata or {},
            "messages": []
        }
        
        # Save the conversation
        if self.storage.write(self._get_conversation_path(user_id, conversation_id), conversation):
            return conversation_id
        else:
            logger.error(f"Failed to create conversation {conversation_id} for user {user_id}")
            return ""
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Dict[str, Any]:
        """
        Get a conversation.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            
        Returns:
            The conversation data, or an empty dict if not found
        """
        return self.storage.read(self._get_conversation_path(user_id, conversation_id))
    
    def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all conversations for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of conversation summaries (without messages)
        """
        # Check if user exists
        if not self.user_manager.user_exists(user_id):
            logger.error(f"User {user_id} not found")
            return []
        
        # Get the list of conversation files
        conversations_path = self._get_conversations_path(user_id)
        conversation_files = self.storage.list_files(conversations_path)
        
        # Load basic info from each conversation
        conversations = []
        for file_name in conversation_files:
            if not file_name.endswith('.json'):
                continue
                
            conversation_id = file_name[:-5]  # Remove .json extension
            conversation = self.storage.read(self._get_conversation_path(user_id, conversation_id))
            
            # Create a summary without the actual messages
            if conversation:
                summary = {
                    "conversation_id": conversation.get("conversation_id", ""),
                    "created_at": conversation.get("created_at", 0),
                    "updated_at": conversation.get("updated_at", 0),
                    "metadata": conversation.get("metadata", {}),
                    "message_count": len(conversation.get("messages", []))
                }
                conversations.append(summary)
        
        # Sort conversations by updated_at (newest first)
        conversations.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        
        return conversations
    
    def add_message(self, user_id: str, conversation_id: str, role: str, content: str,
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            role: The role of the message sender (user, assistant, system)
            content: The content of the message
            metadata: Optional metadata for the message
            
        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation(user_id, conversation_id)
        
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found for user {user_id}")
            return False
        
        # Create the message
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Add the message to the conversation
        if "messages" not in conversation:
            conversation["messages"] = []
            
        conversation["messages"].append(message)
        
        # Update the conversation's updated_at timestamp
        conversation["updated_at"] = time.time()
        
        # Save the updated conversation
        return self.storage.write(self._get_conversation_path(user_id, conversation_id), conversation)
    
    def get_messages(self, user_id: str, conversation_id: str, 
                    start: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            start: The index to start from (0-based)
            limit: The maximum number of messages to return
            
        Returns:
            List of messages
        """
        conversation = self.get_conversation(user_id, conversation_id)
        
        if not conversation or "messages" not in conversation:
            return []
        
        messages = conversation["messages"]
        
        # Apply pagination
        if limit is not None:
            messages = messages[start:start + limit]
        else:
            messages = messages[start:]
            
        return messages
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            
        Returns:
            True if successful, False otherwise
        """
        conversation_path = self._get_conversation_path(user_id, conversation_id)
        return self.storage.delete(conversation_path)
    
    def update_conversation_metadata(self, user_id: str, conversation_id: str, 
                                   metadata: Dict[str, Any]) -> bool:
        """
        Update a conversation's metadata.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            metadata: The new metadata
            
        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation(user_id, conversation_id)
        
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found for user {user_id}")
            return False
        
        # Update the metadata
        if "metadata" not in conversation:
            conversation["metadata"] = {}
            
        conversation["metadata"].update(metadata)
        
        # Save the updated conversation
        return self.storage.write(self._get_conversation_path(user_id, conversation_id), conversation)
    
    def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent conversations for a user.
        
        Args:
            user_id: The ID of the user
            limit: The maximum number of conversations to return
            
        Returns:
            List of conversation summaries
        """
        conversations = self.list_conversations(user_id)
        return conversations[:limit]
    
    def get_conversation_by_name(self, user_id: str, name: str) -> Dict[str, Any]:
        """
        Find a conversation by its name in metadata.
        
        Args:
            user_id: The ID of the user
            name: The name of the conversation
            
        Returns:
            The conversation data if found, or empty dict otherwise
        """
        conversations = self.list_conversations(user_id)
        
        for conversation in conversations:
            metadata = conversation.get("metadata", {})
            if metadata.get("name") == name:
                return self.get_conversation(user_id, conversation["conversation_id"])
        
        return {} 