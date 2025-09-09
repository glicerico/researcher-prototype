"""
Profile Manager for handling user profiles and preferences.
"""

import uuid
import time
import random
from typing import Dict, Any, List, Optional

# Import the centralized logging configuration
from services.logging_config import get_logger
from .storage_manager import StorageManager

logger = get_logger(__name__)


class ProfileManager:
    """
    Profile manager for handling user profiles and preferences.
    """

    def __init__(self, storage_manager: StorageManager):
        """Initialize the profile manager with a storage manager."""
        self.storage = storage_manager
        self.users_path = "users"

    def _generate_friendly_user_id(self) -> str:
        """
        Generate a friendly, human-readable user ID.
        Format: {adjective}-{noun}-{number}
        Example: happy-cat-42
        """
        adjectives = [
            "happy",
            "clever",
            "bright",
            "swift",
            "calm",
            "bold",
            "wise",
            "kind",
            "cool",
            "smart",
            "quick",
            "brave",
            "gentle",
            "sharp",
            "witty",
            "keen",
            "neat",
            "fresh",
            "warm",
            "clear",
            "pure",
            "fine",
            "good",
            "nice",
        ]

        nouns = [
            "cat",
            "dog",
            "fox",
            "owl",
            "bee",
            "ant",
            "elk",
            "bat",
            "cod",
            "eel",
            "jay",
            "ram",
            "yak",
            "pig",
            "cow",
            "hen",
            "rat",
            "bug",
            "fly",
            "cub",
            "pup",
            "kit",
            "calf",
            "lamb",
            "foal",
            "joey",
            "chick",
            "fawn",
            "kid",
            "colt",
        ]

        # Generate a random number between 10-99
        number = random.randint(10, 99)

        # Pick random adjective and noun
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)

        # Create the friendly ID (removed "user-" prefix)
        friendly_id = f"{adjective}-{noun}-{number}"

        # Check if this ID already exists, if so, try again with a different number
        max_attempts = 10
        attempt = 0
        while self.user_exists(friendly_id) and attempt < max_attempts:
            number = random.randint(10, 99)
            friendly_id = f"{adjective}-{noun}-{number}"
            attempt += 1

        # If we still have a collision after max attempts, fall back to UUID
        if self.user_exists(friendly_id):
            logger.warning(f"Could not generate unique friendly ID after {max_attempts} attempts, falling back to UUID")
            return str(uuid.uuid4())

        return friendly_id

    def _get_user_path(self, user_id: str) -> str:
        """Get the path to a user's directory."""
        return f"{self.users_path}/{user_id}"

    def _get_profile_path(self, user_id: str) -> str:
        """Get the path to a user's profile file."""
        return f"{self._get_user_path(user_id)}/profile.json"

    def _get_preferences_path(self, user_id: str) -> str:
        """Get the path to a user's preferences file."""
        return f"{self._get_user_path(user_id)}/preferences.json"

    def _get_engagement_analytics_path(self, user_id: str) -> str:
        """Get the path to a user's engagement analytics file."""
        return f"{self._get_user_path(user_id)}/engagement_analytics.json"

    def _get_personalization_history_path(self, user_id: str) -> str:
        """Get the path to a user's personalization history file."""
        return f"{self._get_user_path(user_id)}/personalization_history.json"

    def create_user(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new user with a unique ID.

        Args:
            metadata: Optional metadata for the user

        Returns:
            The newly created user ID
        """
        # Generate a friendly user ID
        user_id = self._generate_friendly_user_id()

        # Create user profile
        profile = {
            "user_id": user_id,
            "created_at": time.time(),
            "metadata": metadata or {},
            "personality": {"style": "helpful", "tone": "friendly", "additional_traits": {}},
        }

        # Save the profile
        if self.storage.write(self._get_profile_path(user_id), profile):
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

    def delete_all_users(self) -> bool:
        """Delete all users and their data."""
        users_dir = self.storage._get_file_path(self.users_path)

        try:
            import shutil

            if users_dir.exists():
                shutil.rmtree(users_dir)
            users_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error deleting all users: {str(e)}")
            return False

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
            return {"style": "helpful", "tone": "friendly", "additional_traits": {}}

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
        file_path = self.storage._get_file_path(profile_path)
        return file_path.exists()

    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences."""
        return {
            "content_preferences": {
                "research_depth": "balanced",
                "source_types": {
                    "academic_papers": 0.7,
                    "news_articles": 0.8,
                    "expert_blogs": 0.7,
                    "government_reports": 0.6,
                    "industry_reports": 0.6
                },
                "topic_categories": {}
            },
            "format_preferences": {
                "response_length": "medium",
                "detail_level": "balanced",
                "formatting_style": "structured",
                "include_key_insights": True
            },
            "interaction_preferences": {
                "notification_frequency": "moderate"
            }
        }

    def _get_default_engagement_analytics(self) -> Dict[str, Any]:
        """Get default engagement analytics structure."""
        return {
            "reading_patterns": {
            },
            "interaction_signals": {
                "most_engaged_source_types": [],
                "follow_up_question_frequency": 0.0
            },
            "bookmarks_by_topic": {},
            "bookmarked_findings": [],
            "link_clicks_by_topic": {},
            "recent_link_domains": [],
            "integrations_by_topic": {},
            "integrated_findings": [],
            "learned_adaptations": {
                "tone_adjustments": {}
            }
        }

    def _get_default_personalization_history(self) -> Dict[str, Any]:
        """Get default personalization history structure."""
        return {
            "adaptation_log": [],
            "preference_evolution": {
                "source_type_preferences": [],
                "format_preferences": [],
                "content_preferences": []
            }
        }

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's preferences.

        Args:
            user_id: The ID of the user

        Returns:
            The user's preferences, or default preferences if not found
        """
        try:
            preferences = self.storage.read(self._get_preferences_path(user_id))
            if not preferences:
                logger.info(f"👤 ProfileManager: Creating default preferences for user {user_id}")
                preferences = self._get_default_preferences()
                self.storage.write(self._get_preferences_path(user_id), preferences)
            else:
                logger.debug(f"👤 ProfileManager: Retrieved preferences for user {user_id}")
            return preferences
        except Exception as e:
            logger.error(f"👤 ProfileManager: ❌ Error getting preferences for user {user_id}: {str(e)}")
            return self._get_default_preferences()

    def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update a user's preferences.

        Args:
            user_id: The ID of the user
            preferences: The preferences to update

        Returns:
            True if successful, False otherwise
        """
        try:
            current_preferences = self.get_preferences(user_id)
            changes_made = {}
            
            for category, values in preferences.items():
                old_values = current_preferences.get(category, {})
                if category in current_preferences:
                    if isinstance(values, dict) and isinstance(current_preferences[category], dict):
                        current_preferences[category].update(values)
                        changes_made[category] = {"old": old_values, "new": current_preferences[category]}
                    else:
                        old_value = current_preferences[category]
                        current_preferences[category] = values
                        changes_made[category] = {"old": old_value, "new": values}
                else:
                    current_preferences[category] = values
                    changes_made[category] = {"old": None, "new": values}
            
            success = self.storage.write(self._get_preferences_path(user_id), current_preferences)
            
            if success:
                logger.info(f"👤 ProfileManager: ✅ Updated preferences for user {user_id}. Categories: {list(changes_made.keys())}")
                logger.debug(f"👤 ProfileManager: Preference changes for user {user_id}: {changes_made}")
                self._log_preference_change(user_id, preferences)
            else:
                logger.error(f"👤 ProfileManager: ❌ Failed to write preferences to storage for user {user_id}")
            
            return success
        except Exception as e:
            logger.error(f"👤 ProfileManager: ❌ Error updating preferences for user {user_id}: {str(e)}")
            return False

    def get_engagement_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's engagement analytics.

        Args:
            user_id: The ID of the user

        Returns:
            The user's engagement analytics, or default analytics if not found
        """
        analytics = self.storage.read(self._get_engagement_analytics_path(user_id))
        if not analytics:
            analytics = self._get_default_engagement_analytics()
            self.storage.write(self._get_engagement_analytics_path(user_id), analytics)
        return analytics

    def track_engagement(self, user_id: str, interaction_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Track user engagement for learning preferences.

        Args:
            user_id: The ID of the user
            interaction_type: Type of interaction (research_finding, chat_response, etc.)
            metadata: Interaction metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            analytics = self.get_engagement_analytics(user_id)
            
            logger.info(f"👤 ProfileManager: Tracking engagement for user {user_id}: {interaction_type}")
            logger.debug(f"Engagement metadata for user {user_id}: {metadata}")
            
            if interaction_type == "research_finding":
                self._process_research_engagement(analytics, metadata)
                logger.debug(f"👤 ProfileManager: Processed research engagement for user {user_id}: source_types={metadata.get('source_types', [])}")
            elif interaction_type == "chat_response":
                self._process_chat_engagement(analytics, metadata)
                logger.debug(f"👤 ProfileManager: Processed chat engagement for user {user_id}: follow_up={metadata.get('has_follow_up', False)}")
            else:
                logger.warning(f"Unknown interaction type for user {user_id}: {interaction_type}")
            
            success = self.storage.write(self._get_engagement_analytics_path(user_id), analytics)
            
            if success:
                logger.debug(f"👤 ProfileManager: ✅ Successfully saved engagement analytics for user {user_id}")
            else:
                logger.error(f"👤 ProfileManager: ❌ Failed to save engagement analytics for user {user_id}")
                
            return success
        except Exception as e:
            logger.error(f"👤 ProfileManager: ❌ Error tracking engagement for user {user_id}: {str(e)}", exc_info=True)
            return False

    def _process_research_engagement(self, analytics: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        """Process research finding engagement data."""
        source_types = metadata.get("source_types", [])
        
        if source_types:
            for source_type in source_types:
                if source_type not in analytics["interaction_signals"]["most_engaged_source_types"]:
                    # Use explicit feedback
                    feedback = metadata.get("feedback")
                    if feedback == "up":
                        analytics["interaction_signals"]["most_engaged_source_types"].append(source_type)

    def _process_chat_engagement(self, analytics: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        """Process chat response engagement data."""
        follow_up = metadata.get("has_follow_up", False)
        
        
        if follow_up:
            current_freq = analytics["interaction_signals"]["follow_up_question_frequency"]
            analytics["interaction_signals"]["follow_up_question_frequency"] = min(1.0, current_freq + 0.1)

    def _categorize_response_length(self, content_length: int) -> str:
        """Categorize response length based on character count."""
        if content_length < 500:
            return "short_responses"
        elif content_length < 1500:
            return "medium_responses"
        else:
            return "long_responses"

    def get_personalization_history(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's personalization history.

        Args:
            user_id: The ID of the user

        Returns:
            The user's personalization history
        """
        history = self.storage.read(self._get_personalization_history_path(user_id))
        if not history:
            history = self._get_default_personalization_history()
            self.storage.write(self._get_personalization_history_path(user_id), history)
        return history

    def _log_preference_change(self, user_id: str, preferences_changed: Dict[str, Any]) -> None:
        """Log preference changes to personalization history."""
        try:
            history = self.get_personalization_history(user_id)
            
            log_entry = {
                "timestamp": time.time(),
                "adaptation_type": "manual_preference_update",
                "change_made": f"User manually updated preferences: {list(preferences_changed.keys())}",
                "user_feedback": "explicit",
                "effectiveness_score": None
            }
            
            history["adaptation_log"].append(log_entry)
            
            for category in preferences_changed.keys():
                evolution_entry = {
                    "timestamp": time.time(),
                    "category": category,
                    "change_type": "manual_update"
                }
                
                if category == "content_preferences":
                    history["preference_evolution"]["content_preferences"].append(evolution_entry)
                elif category == "format_preferences":
                    history["preference_evolution"]["format_preferences"].append(evolution_entry)
            
            self.storage.write(self._get_personalization_history_path(user_id), history)
        except Exception as e:
            logger.error(f"👤 ProfileManager: ❌ Error logging preference change for user {user_id}: {str(e)}")

    def migrate_user_personalization_files(self, user_id: str) -> bool:
        """
        Migrate existing user to have personalization files.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"👤 ProfileManager: Starting personalization file migration for user {user_id}")
            
            # Initialize all personalization files
            preferences = self.get_preferences(user_id)
            analytics = self.get_engagement_analytics(user_id)
            history = self.get_personalization_history(user_id)
            
            logger.info(f"👤 ProfileManager: ✅ Successfully migrated personalization files for user {user_id}")
            logger.debug(f"Migration summary for user {user_id}: preferences_categories={list(preferences.keys())}, analytics_ready={bool(analytics)}, history_ready={bool(history)}")
            
            return True
        except Exception as e:
            logger.error(f"Error migrating personalization files for user {user_id}: {str(e)}", exc_info=True)
            return False
