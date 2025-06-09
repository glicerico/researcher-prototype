import os
from typing import Optional
from fastapi import Header

from storage import StorageManager, UserManager, ZepManager
from logging_config import get_logger

logger = get_logger(__name__)

# Initialize storage components
storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_data")
storage_manager = StorageManager(storage_dir)
user_manager = UserManager(storage_manager)

# Initialize Zep manager
zep_manager = ZepManager()
_motivation_config_override = {}


def generate_display_name_from_user_id(user_id: str) -> str:
    """Generate a display name from a user ID."""
    if not user_id:
        return "User"

    # Check if it's a friendly ID format (adjective-noun-number) - new format
    if len(user_id.split("-")) == 3 and not user_id.startswith("user-"):
        parts = user_id.split("-")
        adjective = parts[0]
        noun = parts[1]
        number = parts[2]

        # Capitalize first letters and create a nice display name
        capitalized_adjective = adjective.capitalize()
        capitalized_noun = noun.capitalize()

        return f"{capitalized_adjective} {capitalized_noun} {number}"

    # Fallback for UUID format - use last 6 characters
    if len(user_id) >= 6:
        return f"User {user_id[-6:]}"

    # Ultimate fallback
    return f"User {user_id}"


def get_existing_user_id(user_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user ID from headers if it exists and is valid."""
    if user_id and user_manager.user_exists(user_id):
        return user_id
    return None


def get_or_create_user_id(user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from headers or create a new user."""
    if user_id and user_manager.user_exists(user_id):
        return user_id

    # Create a new user
    new_user_id = user_manager.create_user()
    logger.info(f"Created new user: {new_user_id}")
    return new_user_id
