import os
from typing import Optional
from fastapi import Header

from storage import StorageManager, ProfileManager, ResearchManager, ZepManager
from services.logging_config import get_logger

logger = get_logger(__name__)

# Initialize storage components
storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_data")
storage_manager = StorageManager(storage_dir)
profile_manager = ProfileManager(storage_manager)
research_manager = ResearchManager(storage_manager, profile_manager)

# Initialize Zep manager
zep_manager = ZepManager()
_motivation_config_override = {}

# Default guest user configuration
GUEST_USER_ID = "guest"
GUEST_DISPLAY_NAME = "Guest User"


def ensure_guest_user_exists() -> None:
    """Ensure the default guest user exists, create it if not."""
    if not profile_manager.user_exists(GUEST_USER_ID):
        # Create guest user with specific metadata
        metadata = {
            "display_name": GUEST_DISPLAY_NAME,
            "is_guest": True,
            "created_from": "system_default"
        }
        
        # Create the guest user profile directly
        profile = {
            "user_id": GUEST_USER_ID,
            "created_at": 0,  # Use 0 to indicate it's the system default
            "metadata": metadata,
            "personality": {"style": "helpful", "tone": "friendly", "additional_traits": {}},
        }
        
        # Save the profile using storage manager directly
        profile_path = f"{profile_manager.users_path}/{GUEST_USER_ID}/profile.json"
        if profile_manager.storage.write(profile_path, profile):
            logger.info(f"Created default guest user: {GUEST_USER_ID}")
        else:
            logger.error(f"Failed to create default guest user: {GUEST_USER_ID}")


def generate_display_name_from_user_id(user_id: str) -> str:
    """Generate a display name from a user ID."""
    if not user_id:
        return "User"

    # Handle guest user specially
    if user_id == GUEST_USER_ID:
        return GUEST_DISPLAY_NAME

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
    if user_id and profile_manager.user_exists(user_id):
        return user_id
    return None


def get_or_create_user_id(user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from headers or return the default guest user."""
    if user_id and profile_manager.user_exists(user_id):
        return user_id

    # Ensure guest user exists before returning it
    ensure_guest_user_exists()
    
    # Return guest user instead of creating a new user
    logger.info(f"Using default guest user: {GUEST_USER_ID}")
    return GUEST_USER_ID


# Initialize guest user on startup
ensure_guest_user_exists()
