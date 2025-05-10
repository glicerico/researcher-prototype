"""
User Manager for handling user profiles and preferences.
"""

import uuid
import time
from typing import Dict, Any, List, Optional

# Import the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

from .storage_manager import StorageManager

class UserManager:
    """
    User manager for handling user profiles and preferences.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """Initialize the user manager with a storage manager."""
        self.storage = storage_manager
        self.users_path = "users"
    
    def _get_user_path(self, user_id: str) -> str:
        """Get the path to a user's directory."""
        return f"{self.users_path}/{user_id}"
    
    def _get_profile_path(self, user_id: str) -> str:
        """Get the path to a user's profile file."""
        return f"{self._get_user_path(user_id)}/profile.json"
    
    def create_user(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new user with a unique ID.
        
        Args:
            metadata: Optional metadata for the user
            
        Returns:
            The newly created user ID
        """
        # Generate a unique user ID
        user_id = str(uuid.uuid4())
        
        # Create user profile
        profile = {
            "user_id": user_id,
            "created_at": time.time(),
            "metadata": metadata or {},
            "personality": {
                "style": "helpful",
                "tone": "friendly",
                "additional_traits": {}
            }
        }
        
        # Save the profile
        if self.storage.write(self._get_profile_path(user_id), profile):
            # Create conversations directory
            user_path = self._get_user_path(user_id)
            conversations_path = f"{user_path}/conversations"
            self.storage._get_file_path(conversations_path).mkdir(parents=True, exist_ok=True)
            
            return user_id
        else:
            logger.error(f"Failed to create user {user_id}")
            return ""
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's profile.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The user's profile, or an empty dict if not found
        """
        return self.storage.read(self._get_profile_path(user_id))
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a user's profile.
        
        Args:
            user_id: The ID of the user
            data: The data to update
            
        Returns:
            True if successful, False otherwise
        """
        profile = self.get_user(user_id)
        
        if not profile:
            logger.error(f"User {user_id} not found")
            return False
        
        # Update the profile with new data
        for key, value in data.items():
            if key == "user_id":  # Don't allow changing the user ID
                continue
                
            if isinstance(value, dict) and key in profile and isinstance(profile[key], dict):
                # Merge dictionaries rather than replacing
                profile[key].update(value)
            else:
                profile[key] = value
        
        # Save the updated profile
        return self.storage.write(self._get_profile_path(user_id), profile)
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user and all their data.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            True if successful, False otherwise
        """
        user_path = self._get_user_path(user_id)
        user_dir = self.storage._get_file_path(user_path)
        
        try:
            if user_dir.exists():
                # Remove all files in the user's directory recursively
                import shutil
                shutil.rmtree(user_dir)
                return True
            else:
                logger.warning(f"User directory {user_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False
    
    def list_users(self) -> List[str]:
        """
        List all user IDs.
        
        Returns:
            List of user IDs
        """
        return self.storage.list_directories(self.users_path)
    
    def get_personality(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's personality configuration.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The personality configuration, or default values if not found
        """
        profile = self.get_user(user_id)
        
        if not profile or "personality" not in profile:
            # Return default personality
            return {
                "style": "helpful",
                "tone": "friendly",
                "additional_traits": {}
            }
        
        return profile["personality"]
    
    def update_personality(self, user_id: str, personality: Dict[str, Any]) -> bool:
        """
        Update a user's personality configuration.
        
        Args:
            user_id: The ID of the user
            personality: The personality configuration
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_user(user_id, {"personality": personality})
    
    def user_exists(self, user_id: str) -> bool:
        """
        Check if a user exists.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            True if the user exists, False otherwise
        """
        profile_path = self._get_profile_path(user_id)
        return self.storage._get_file_path(profile_path).exists() 