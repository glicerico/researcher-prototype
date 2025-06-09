"""
User Manager for handling user profiles and preferences.
"""

import uuid
import time
import random
import threading
from typing import Dict, Any, List, Optional

# Import the centralized logging configuration
from logging_config import get_logger
from .storage_manager import StorageManager

logger = get_logger(__name__)

class UserManager:
    """
    User manager for handling user profiles and preferences.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """Initialize the user manager with a storage manager."""
        self.storage = storage_manager
        self.users_path = "users"
        # Add threading locks for safe concurrent operations
        self._user_locks = {}
        self._locks_lock = threading.Lock()
    
    def _get_user_lock(self, user_id: str) -> threading.Lock:
        """Get or create a lock for a specific user."""
        with self._locks_lotok:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = threading.Lock()
            return self._user_locks[user_id]
    
    def _generate_friendly_user_id(self) -> str:
        """
        Generate a friendly, human-readable user ID.
        Format: {adjective}-{noun}-{number}
        Example: happy-cat-42
        """
        adjectives = [
            "happy", "clever", "bright", "swift", "calm", "bold", "wise", "kind",
            "cool", "smart", "quick", "brave", "gentle", "sharp", "witty", "keen",
            "neat", "fresh", "warm", "clear", "pure", "fine", "good", "nice"
        ]
        
        nouns = [
            "cat", "dog", "fox", "owl", "bee", "ant", "elk", "bat", "cod", "eel",
            "jay", "ram", "yak", "pig", "cow", "hen", "rat", "bug", "fly", "cub",
            "pup", "kit", "calf", "lamb", "foal", "joey", "chick", "fawn", "kid", "colt"
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
            "personality": {
                "style": "helpful",
                "tone": "friendly",
                "additional_traits": {}
            }
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
        file_path = self.storage._get_file_path(profile_path)
        return file_path.exists()
    
    def store_topic_suggestions(self, user_id: str, session_id: str, topics: List[Dict[str, Any]], conversation_context: str = "") -> bool:
        """
        Store topic suggestions for a user session.
        
        Args:
            user_id: The ID of the user
            session_id: The session ID
            topics: List of topic dictionaries with name, description, confidence_score
            conversation_context: Brief context from the conversation
            
        Returns:
            True if successful, False otherwise
        """
        if not topics:
            return True  # Nothing to store
        
        # Use user-specific lock for thread safety
        with self._get_user_lock(user_id):
            try:
                # Ensure migration from profile.json if needed
                self.migrate_topics_from_profile(user_id)
                
                # Load current topics data
                topics_data = self.get_user_topics(user_id)
                
                # Prepare session topics with unique IDs
                current_time = time.time()
                session_topics = []
                
                for topic in topics:
                    topic_entry = {
                        "topic_id": str(uuid.uuid4()),  # Add unique topic ID
                        "topic_name": topic.get("name"),
                        "description": topic.get("description"),
                        "confidence_score": topic.get("confidence_score"),
                        "suggested_at": current_time,
                        "conversation_context": conversation_context,
                        "is_active_research": False,  # Default to inactive
                        "research_count": 0
                    }
                    session_topics.append(topic_entry)
            
                # Get existing topics for this session
                existing_topics = topics_data.get("sessions", {}).get(session_id, [])
                
                # Merge new topics with existing ones
                # Check for duplicates based on topic name to avoid exact duplicates
                existing_topic_names = {topic.get("topic_name", "").lower() for topic in existing_topics}
                
                merged_topics = existing_topics.copy()  # Start with existing topics
                for new_topic in session_topics:
                    new_topic_name = new_topic.get("topic_name", "").lower()
                    # Only add if we don't already have a topic with the same name
                    if new_topic_name not in existing_topic_names:
                        merged_topics.append(new_topic)
                        existing_topic_names.add(new_topic_name)  # Track it to avoid duplicates within new topics too
                
                # Store merged topics for this session
                topics_data["sessions"][session_id] = merged_topics
                
                # Update metadata
                topics_data["metadata"]["total_topics"] = sum(
                    len(topics) for topics in topics_data["sessions"].values()
                )
                
                # Save updated topics
                return self.save_user_topics(user_id, topics_data)
                
            except Exception as e:
                logger.error(f"Error storing topic suggestions for user {user_id}: {str(e)}")
                return False
    
    def get_topic_suggestions(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Get topic suggestions for a user session.
        
        Args:
            user_id: The ID of the user
            session_id: The session ID
            
        Returns:
            List of topic suggestion dictionaries
        """
        try:
            # Ensure migration from profile.json if needed
            self.migrate_topics_from_profile(user_id)
            
            # Load topics data
            topics_data = self.get_user_topics(user_id)
            return topics_data.get("sessions", {}).get(session_id, [])
            
        except Exception as e:
            logger.error(f"Error getting topic suggestions for user {user_id}, session {session_id}: {str(e)}")
            return []
    
    def get_all_topic_suggestions(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all topic suggestions for a user across all sessions.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dictionary mapping session_id to list of topic suggestions
        """
        try:
            # Ensure migration from profile.json if needed
            self.migrate_topics_from_profile(user_id)
            
            # Load topics data
            topics_data = self.get_user_topics(user_id)
            return topics_data.get("sessions", {})
            
        except Exception as e:
            logger.error(f"Error getting all topic suggestions for user {user_id}: {str(e)}")
            return {}

    # =================== NEW THREE-FILE STORAGE STRUCTURE ===================
    
    def _get_topics_path(self, user_id: str) -> str:
        """Get the path to a user's topics file."""
        return f"{self._get_user_path(user_id)}/topics.json"
    
    def _get_research_findings_path(self, user_id: str) -> str:
        """Get the path to a user's research findings file."""
        return f"{self._get_user_path(user_id)}/research_findings.json"
    
    # =================== TOPIC MANAGEMENT METHODS ===================
    
    def get_user_topics(self, user_id: str) -> Dict[str, Any]:
        """
        Get all topics for a user from the topics.json file.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dictionary containing topic data, or empty structure if not found
        """
        topics_data = self.storage.read(self._get_topics_path(user_id))
        if not topics_data:
            return {
                "sessions": {},
                "metadata": {
                    "total_topics": 0,
                    "active_research_topics": 0,
                    "last_cleanup": time.time()
                }
            }
        return topics_data
    
    def save_user_topics(self, user_id: str, topics_data: Dict[str, Any]) -> bool:
        """
        Save topics data to the topics.json file.
        
        Args:
            user_id: The ID of the user
            topics_data: The topics data to save
            
        Returns:
            True if successful, False otherwise
        """
        return self.storage.write(self._get_topics_path(user_id), topics_data)
    
    def get_active_research_topics(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active research topics for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of active research topic dictionaries
        """
        topics_data = self.get_user_topics(user_id)
        active_topics = []
        
        for session_id, session_topics in topics_data.get("sessions", {}).items():
            for topic in session_topics:
                if topic.get("is_active_research", False):
                    # Add session info for context
                    topic_copy = topic.copy()
                    topic_copy["session_id"] = session_id
                    active_topics.append(topic_copy)
        
        return active_topics
    
    def update_topic_last_researched(self, user_id: str, topic_name: str, research_time: Optional[float] = None) -> bool:
        """
        Update the last researched timestamp for a topic.
        
        Args:
            user_id: The ID of the user
            topic_name: Name of the topic
            research_time: Research timestamp (current time if None)
            
        Returns:
            True if successful, False otherwise
        """
        if research_time is None:
            research_time = time.time()
        
        topics_data = self.get_user_topics(user_id)
        updated = False
        
        # Find and update the topic across all sessions
        for session_id, session_topics in topics_data.get("sessions", {}).items():
            for topic in session_topics:
                if topic.get("topic_name") == topic_name and topic.get("is_active_research", False):
                    topic["last_researched"] = research_time
                    topic["research_count"] = topic.get("research_count", 0) + 1
                    updated = True
        
        if updated:
            return self.save_user_topics(user_id, topics_data)
        
        logger.warning(f"Topic '{topic_name}' not found for user {user_id}")
        return False
    
    def update_topic_research_status_by_id(self, user_id: str, topic_id: str, enable: bool) -> Dict[str, Any]:
        """
        Safely update research status for a topic by its unique ID instead of index.
        
        Args:
            user_id: The ID of the user
            topic_id: The unique topic ID
            enable: True to enable research, False to disable
            
        Returns:
            Dictionary with success status and updated topic info
        """
        with self._get_user_lock(user_id):
            try:
                # Ensure migration from profile.json if needed
                self.migrate_topics_from_profile(user_id)
                
                # Load topics data
                topics_data = self.get_user_topics(user_id)
                
                # Find the topic by ID
                updated_topic = None
                session_id = None
                
                for sid, session_topics in topics_data.get("sessions", {}).items():
                    for topic in session_topics:
                        if topic.get("topic_id") == topic_id:
                            # Update research status
                            topic["is_active_research"] = enable
                            current_time = time.time()
                            
                            if enable:
                                topic["research_enabled_at"] = current_time
                                if "research_disabled_at" in topic:
                                    del topic["research_disabled_at"]
                            else:
                                topic["research_disabled_at"] = current_time
                                if "research_enabled_at" in topic:
                                    del topic["research_enabled_at"]
                            
                            updated_topic = topic.copy()
                            updated_topic["session_id"] = sid
                            session_id = sid
                            break
                    
                    if updated_topic:
                        break
                
                if not updated_topic:
                    return {
                        "success": False,
                        "error": f"Topic with ID {topic_id} not found",
                        "updated_topic": None
                    }
                
                # Update metadata
                topics_data["metadata"]["active_research_topics"] = sum(
                    1 for session_topics in topics_data["sessions"].values()
                    for topic in session_topics
                    if topic.get("is_active_research", False)
                )
                
                # Save updated topics
                success = self.save_user_topics(user_id, topics_data)
                
                if success:
                    action = "enabled" if enable else "disabled"
                    logger.info(f"Research {action} for topic '{updated_topic['topic_name']}' (ID: {topic_id}) for user {user_id}")
                    return {
                        "success": True,
                        "updated_topic": updated_topic
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to save after updating research status",
                        "updated_topic": None
                    }
                
            except Exception as e:
                logger.error(f"Error updating research status for topic ID {topic_id}, user {user_id}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "updated_topic": None
                }
    
    # =================== RESEARCH FINDINGS METHODS ===================
    
    def get_research_findings(self, user_id: str, topic_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get research findings for a user, optionally filtered by topic.
        
        Args:
            user_id: The ID of the user
            topic_name: Optional topic name to filter by
            
        Returns:
            Dictionary mapping topic names to lists of findings
        """
        findings_data = self.storage.read(self._get_research_findings_path(user_id))
        if not findings_data:
            return {}
        
        # Remove metadata if present (it's not a topic)
        findings = {k: v for k, v in findings_data.items() if k != "metadata"}
        
        if topic_name:
            return {topic_name: findings.get(topic_name, [])}
        
        return findings
    
    def store_research_finding(self, user_id: str, topic_name: str, finding: Dict[str, Any]) -> bool:
        """
        Store a research finding for a specific topic.
        
        Args:
            user_id: The ID of the user
            topic_name: Name of the topic
            finding: The finding data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing findings
            findings_data = self.storage.read(self._get_research_findings_path(user_id))
            if not findings_data:
                findings_data = {"metadata": {"last_cleanup": time.time(), "total_findings": 0, "topics_count": 0}}
            
            # Initialize topic if not exists
            if topic_name not in findings_data:
                findings_data[topic_name] = []
                findings_data["metadata"]["topics_count"] = findings_data["metadata"].get("topics_count", 0) + 1
            
            # Add unique ID and read status
            finding["finding_id"] = f"{user_id}_{topic_name.replace(' ', '_')}_{int(finding.get('research_time', time.time()))}"
            finding["read"] = False
            
            # Store the finding
            findings_data[topic_name].append(finding)
            findings_data["metadata"]["total_findings"] = findings_data["metadata"].get("total_findings", 0) + 1
            
            # Save back to storage
            success = self.storage.write(self._get_research_findings_path(user_id), findings_data)
            
            if success:
                logger.info(f"Stored research finding for topic '{topic_name}' for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing research finding for user {user_id}, topic '{topic_name}': {str(e)}")
            return False
    
    def mark_finding_as_read(self, user_id: str, finding_id: str) -> bool:
        """
        Mark a research finding as read.
        
        Args:
            user_id: The ID of the user
            finding_id: The ID of the finding
            
        Returns:
            True if successful, False otherwise
        """
        try:
            findings_data = self.storage.read(self._get_research_findings_path(user_id))
            if not findings_data:
                return False
            
            # Find and update the finding
            for topic_name, findings in findings_data.items():
                if topic_name == "metadata":
                    continue
                
                for finding in findings:
                    if finding.get("finding_id") == finding_id:
                        finding["read"] = True
                        return self.storage.write(self._get_research_findings_path(user_id), findings_data)
            
            logger.warning(f"Finding {finding_id} not found for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error marking finding as read for user {user_id}: {str(e)}")
            return False
    
    def cleanup_old_research_findings(self, user_id: str, retention_days: int) -> bool:
        """
        Clean up old research findings based on retention policy.
        
        Args:
            user_id: The ID of the user
            retention_days: Number of days to retain findings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            findings_data = self.storage.read(self._get_research_findings_path(user_id))
            if not findings_data:
                return True  # Nothing to clean up
            
            cutoff_time = time.time() - (retention_days * 24 * 3600)
            cleaned_topics = []
            total_removed = 0
            
            # Clean up each topic
            for topic_name, findings in list(findings_data.items()):
                if topic_name == "metadata":
                    continue
                
                # Filter out old findings
                original_count = len(findings)
                findings_data[topic_name] = [
                    f for f in findings 
                    if f.get("research_time", 0) > cutoff_time
                ]
                
                removed_count = original_count - len(findings_data[topic_name])
                total_removed += removed_count
                
                if removed_count > 0:
                    cleaned_topics.append(f"{topic_name}: {removed_count}")
                
                # Remove empty topics
                if not findings_data[topic_name]:
                    del findings_data[topic_name]
                    if "metadata" in findings_data:
                        findings_data["metadata"]["topics_count"] = max(0, findings_data["metadata"].get("topics_count", 1) - 1)
            
            # Update metadata
            if "metadata" in findings_data:
                findings_data["metadata"]["last_cleanup"] = time.time()
                findings_data["metadata"]["total_findings"] = findings_data["metadata"].get("total_findings", 0) - total_removed
            
            if total_removed > 0:
                logger.info(f"Cleaned up {total_removed} old research findings for user {user_id}: {', '.join(cleaned_topics)}")
                return self.storage.write(self._get_research_findings_path(user_id), findings_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up research findings for user {user_id}: {str(e)}")
            return False
    
    def get_research_findings_for_api(self, user_id: str, topic_name: Optional[str] = None, unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get research findings formatted for API responses.
        
        Args:
            user_id: The ID of the user
            topic_name: Optional topic name to filter by
            unread_only: If True, only return unread findings
            
        Returns:
            List of finding dictionaries with topic information
        """
        findings_data = self.get_research_findings(user_id, topic_name)
        api_findings = []
        
        for topic, findings in findings_data.items():
            for finding in findings:
                if unread_only and finding.get("read", False):
                    continue
                
                # Add topic name to the finding for API response
                api_finding = finding.copy()
                api_finding["topic_name"] = topic
                api_findings.append(api_finding)
        
        # Sort by research time (newest first)
        api_findings.sort(key=lambda x: x.get("research_time", 0), reverse=True)
        
        return api_findings
    
    # =================== MIGRATION HELPERS ===================
    
    def migrate_topics_from_profile(self, user_id: str) -> bool:
        """
        Migrate topic suggestions from profile.json to topics.json (one-time migration).
        
        Args:
            user_id: The ID of the user
            
        Returns:
            True if successful or no migration needed
        """
        try:
            # Check if topics.json already exists
            topics_path = self._get_topics_path(user_id)
            if self.storage.read(topics_path):
                return True  # Already migrated
            
            # Get topics from profile
            profile = self.get_user(user_id)
            if not profile or "topic_suggestions" not in profile:
                return True  # No topics to migrate
            
            # Create new topics structure
            topics_data = {
                "sessions": profile["topic_suggestions"],
                "metadata": {
                    "total_topics": sum(len(topics) for topics in profile["topic_suggestions"].values()),
                    "active_research_topics": 0,
                    "last_cleanup": time.time(),
                    "migrated_from_profile": True,
                    "migration_time": time.time()
                }
            }
            
            # Count active research topics
            for session_topics in profile["topic_suggestions"].values():
                for topic in session_topics:
                    if topic.get("is_active_research", False):
                        topics_data["metadata"]["active_research_topics"] += 1
            
            # Save topics file
            success = self.save_user_topics(user_id, topics_data)
            
            if success:
                logger.info(f"Migrated {topics_data['metadata']['total_topics']} topics from profile to topics.json for user {user_id}")
                
                # Optionally remove topics from profile (uncomment if desired)
                # del profile["topic_suggestions"]
                # self.storage.write(self._get_profile_path(user_id), profile)
            
            return success
            
        except Exception as e:
            logger.error(f"Error migrating topics for user {user_id}: {str(e)}")
            return False
    
    # =================== SAFE DELETION METHODS ===================
    
    def delete_topic_by_id(self, user_id: str, topic_id: str) -> Dict[str, Any]:
        """
        Safely delete a topic by its unique ID instead of index.
        
        Args:
            user_id: The ID of the user
            topic_id: The unique topic ID
            
        Returns:
            Dictionary with success status and deleted topic info
        """
        with self._get_user_lock(user_id):
            try:
                # Ensure migration from profile.json if needed
                self.migrate_topics_from_profile(user_id)
                
                # Load topics data
                topics_data = self.get_user_topics(user_id)
                
                # Find and remove the topic
                deleted_topic = None
                session_to_update = None
                
                for session_id, session_topics in topics_data.get("sessions", {}).items():
                    for i, topic in enumerate(session_topics):
                        if topic.get("topic_id") == topic_id:
                            deleted_topic = session_topics.pop(i)
                            session_to_update = session_id
                            break
                    
                    if deleted_topic:
                        break
                
                if not deleted_topic:
                    return {
                        "success": False,
                        "error": f"Topic with ID {topic_id} not found",
                        "deleted_topic": None
                    }
                
                # Update or remove session if empty
                if session_topics:
                    topics_data["sessions"][session_to_update] = session_topics
                else:
                    del topics_data["sessions"][session_to_update]
                
                # Update metadata
                topics_data["metadata"]["total_topics"] = sum(
                    len(topics) for topics in topics_data["sessions"].values()
                )
                topics_data["metadata"]["active_research_topics"] = sum(
                    1 for session_topics in topics_data["sessions"].values()
                    for topic in session_topics
                    if topic.get("is_active_research", False)
                )
                
                # Save updated topics
                success = self.save_user_topics(user_id, topics_data)
                
                if success:
                    return {
                        "success": True,
                        "deleted_topic": {
                            "topic_id": deleted_topic.get("topic_id"),
                            "topic_name": deleted_topic.get("topic_name"),
                            "description": deleted_topic.get("description"),
                            "session_id": session_to_update
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to save after deletion",
                        "deleted_topic": None
                    }
                
            except Exception as e:
                logger.error(f"Error deleting topic by ID {topic_id} for user {user_id}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "deleted_topic": None
                }
    
    def delete_session_safe(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Safely delete an entire session with all its topics.
        
        Args:
            user_id: The ID of the user
            session_id: The session ID
            
        Returns:
            Dictionary with success status and deletion info
        """
        with self._get_user_lock(user_id):
            try:
                # Ensure migration from profile.json if needed
                self.migrate_topics_from_profile(user_id)
                
                # Load topics data
                topics_data = self.get_user_topics(user_id)
                
                # Check if session exists
                if session_id not in topics_data.get("sessions", {}):
                    return {
                        "success": True,  # Already doesn't exist
                        "message": f"Session {session_id} not found (already deleted)",
                        "topics_deleted": 0
                    }
                
                # Get topic count before deletion
                topic_count = len(topics_data["sessions"][session_id])
                
                # Remove session
                del topics_data["sessions"][session_id]
                
                # Update metadata
                topics_data["metadata"]["total_topics"] = sum(
                    len(topics) for topics in topics_data["sessions"].values()
                )
                topics_data["metadata"]["active_research_topics"] = sum(
                    1 for session_topics in topics_data["sessions"].values()
                    for topic in session_topics
                    if topic.get("is_active_research", False)
                )
                
                # Save updated topics
                success = self.save_user_topics(user_id, topics_data)
                
                if success:
                    return {
                        "success": True,
                        "message": f"Deleted session {session_id} with {topic_count} topics",
                        "session_id": session_id,
                        "topics_deleted": topic_count
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to save after session deletion",
                        "topics_deleted": 0
                    }
                
            except Exception as e:
                logger.error(f"Error deleting session {session_id} for user {user_id}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "topics_deleted": 0
                } 