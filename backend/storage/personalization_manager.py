"""
PersonalizationManager for advanced user behavior learning and preference adaptation.
"""

import time
from typing import Dict, Any, List, Optional
from services.logging_config import get_logger
from .storage_manager import StorageManager
from .profile_manager import ProfileManager

logger = get_logger(__name__)


class PersonalizationManager:
    """
    Advanced personalization manager for learning user preferences and adapting behavior.
    """

    def __init__(self, storage_manager: StorageManager, profile_manager: ProfileManager):
        """Initialize the personalization manager."""
        self.storage = storage_manager
        self.profile_manager = profile_manager

    def track_user_engagement(self, user_id: str, interaction_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Track user engagement and learn from interaction patterns.

        Args:
            user_id: The ID of the user
            interaction_type: Type of interaction (research_finding, chat_response, etc.)
            metadata: Interaction metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"👤 PersonalizationManager: Processing engagement for user {user_id}, type: {interaction_type}")
            logger.debug(f"👤 PersonalizationManager: Engagement data for user {user_id}: {metadata}")
            
            # Track basic engagement
            success = self.profile_manager.track_engagement(user_id, interaction_type, metadata)
            
            if success:
                logger.debug(f"👤 PersonalizationManager: ✅ Basic engagement tracking successful for user {user_id}")
                # Perform advanced learning
                self._update_learned_preferences(user_id, interaction_type, metadata)
                logger.info(f"👤 PersonalizationManager: ✅ Completed learning update for user {user_id}")
            else:
                logger.warning(f"PersonalizationManager: Basic engagement tracking failed for user {user_id}")
                
            return success
        except Exception as e:
            logger.error(f"👤 PersonalizationManager: ❌ Error tracking engagement for user {user_id}: {str(e)}", exc_info=True)
            return False

    def _update_learned_preferences(self, user_id: str, interaction_type: str, metadata: Dict[str, Any]) -> None:
        """Update learned preferences based on engagement patterns."""
        try:
            logger.debug(f"👤 PersonalizationManager: Starting preference learning for user {user_id}, type: {interaction_type}")
            
            if interaction_type == "research_finding":
                self._learn_from_research_interaction(user_id, metadata)
                logger.debug(f"👤 PersonalizationManager: ✅ Completed research interaction learning for user {user_id}")
            elif interaction_type == "chat_response":
                self._learn_from_chat_interaction(user_id, metadata)
                logger.debug(f"👤 PersonalizationManager: ✅ Completed chat interaction learning for user {user_id}")
            elif interaction_type == "engagement_event":
                self._learn_from_engagement_event(user_id, metadata)
                logger.debug(f"👤 PersonalizationManager: ✅ Completed engagement event learning for user {user_id}")
            else:
                logger.warning(f"PersonalizationManager: Unknown interaction type for learning: {interaction_type} (user: {user_id})")
        except Exception as e:
            logger.error(f"👤 PersonalizationManager: ❌ Error updating learned preferences for user {user_id}: {str(e)}", exc_info=True)

    def _learn_from_research_interaction(self, user_id: str, metadata: Dict[str, Any]) -> None:
        """Learn preferences from research finding interactions."""
        # Get new engagement metrics
        feedback = metadata.get("feedback")
        link_clicks = metadata.get("link_clicks", 0)
        source_exploration = metadata.get("source_exploration_clicks", 0)
        session_continuation = metadata.get("session_continuation_rate", 0.0)
        source_types = metadata.get("source_types", [])
        content_length = metadata.get("content_length", 0)
        
        # Calculate engagement score using new metrics
        engagement_score = self._calculate_engagement_score(
            feedback=feedback,
            link_clicks=link_clicks, 
            source_exploration=source_exploration,
            session_continuation=session_continuation,
            completion_rate=0.0  # No longer tracking completion rate
        )
        
        if engagement_score > 0.7:  # High engagement threshold
            # Learn source type preferences
            self._adjust_source_preferences(user_id, source_types, 0.05)
            
            # Learn format preferences
            if content_length > 0:
                # Format preferences based on explicit feedback only
                self._adjust_format_preferences(user_id, content_length, engagement_score)
        
        elif engagement_score < 0.3:  # Low engagement
            # Decrease preference for these source types
            self._adjust_source_preferences(user_id, source_types, -0.03)

    def _learn_from_chat_interaction(self, user_id: str, metadata: Dict[str, Any]) -> None:
        """Learn preferences from chat interactions."""
        # Get new engagement metrics for chat
        feedback = metadata.get("feedback")
        link_clicks = metadata.get("link_clicks", 0)
        source_exploration = metadata.get("source_exploration_clicks", 0)
        session_continuation = metadata.get("session_continuation_rate", 0.0)
        response_length = metadata.get("response_length", "medium")
        
        # Calculate engagement score using new metrics
        engagement_score = self._calculate_engagement_score(
            feedback=feedback,
            link_clicks=link_clicks,
            source_exploration=source_exploration,
            session_continuation=session_continuation,
            completion_rate=0.0  # No longer tracking completion rate
        )
        
        # Learn about preferred response detail level
        if engagement_score > 0.7:
            self._adjust_detail_preference(user_id, response_length, True)
        elif engagement_score < 0.4:
            self._adjust_detail_preference(user_id, response_length, False)

    def _learn_from_engagement_event(self, user_id: str, metadata: Dict[str, Any]) -> None:
        """Learn preferences from engagement events (implicit feedback)."""
        event_type = metadata.get("type")
        interaction_type = metadata.get("interactionType")
        
        if event_type == "content_interaction":
            # Handle implicit feedback from content interactions
            if interaction_type == "bookmark":
                # Bookmarking shows strong interest - record analytics
                content_data = metadata.get("data", {})
                finding_id = content_data.get("findingId")
                topic_name = content_data.get("topicName")
                if finding_id:
                    logger.debug(f"👤 PersonalizationManager: Learning from bookmark action for user {user_id}")
                    analytics = self.profile_manager.get_engagement_analytics(user_id)
                    # Increment per-topic bookmark count
                    if topic_name:
                        by_topic = analytics.get("bookmarks_by_topic", {})
                        by_topic[topic_name] = by_topic.get(topic_name, 0) + 1
                        analytics["bookmarks_by_topic"] = by_topic
                    # Maintain recent bookmarked finding ids (max 50)
                    recent = analytics.get("bookmarked_findings", [])
                    recent.append(finding_id)
                    analytics["bookmarked_findings"] = recent[-50:]
                    # Persist analytics
                    self.profile_manager.storage.write(
                        self.profile_manager._get_engagement_analytics_path(user_id),
                        analytics
                    )
                    logger.debug(f"👤 PersonalizationManager: ✅ Updated bookmark analytics for user {user_id}")
            elif interaction_type == "integrate_to_knowledge_graph":
                # Integration indicates very strong utility; record analytics
                content_data = metadata.get("data", {})
                finding_id = content_data.get("findingId")
                topic_name = content_data.get("topicName")
                if finding_id:
                    analytics = self.profile_manager.get_engagement_analytics(user_id)
                    if topic_name:
                        by_topic = analytics.get("integrations_by_topic", {})
                        by_topic[topic_name] = by_topic.get(topic_name, 0) + 1
                        analytics["integrations_by_topic"] = by_topic
                    recent = analytics.get("integrated_findings", [])
                    recent.append(finding_id)
                    analytics["integrated_findings"] = recent[-50:]
                    self.profile_manager.storage.write(
                        self.profile_manager._get_engagement_analytics_path(user_id),
                        analytics
                    )
                    logger.debug(f"👤 PersonalizationManager: ✅ Updated integration analytics for user {user_id}")
                    
            elif interaction_type == "expand":
                # Topic expansion shows interest in that topic area
                content_data = metadata.get("data", {})
                topic_name = content_data.get("topicName")
                if topic_name:
                    logger.debug(f"👤 PersonalizationManager: Learning from topic expansion for user {user_id}: {topic_name}")
                    # Could boost research priority for this topic
                    
            elif interaction_type == "mark_read":
                # Mark as read shows content consumption
                content_data = metadata.get("data", {})
                finding_id = content_data.get("findingId")
                trigger = content_data.get("trigger", "unknown")
                action = content_data.get("action", "unknown")
                topic_name = content_data.get("topicName")
                
                if finding_id:
                    logger.debug(f"👤 PersonalizationManager: Learning from mark-read action for user {user_id} (trigger: {trigger}, action: {action})")
                    
                    # Different learning based on how the article was marked as read
                    if trigger == "topic_expansion" and action == "expansion_read":
                        # User expanded topic card, showing strong interest in the topic
                        # This is implicit positive engagement - treat as moderate positive signal
                        self._learn_from_expansion_read(user_id, topic_name, finding_id, content_data)
                        logger.debug(f"👤 PersonalizationManager: ✅ Processed expansion-based read for user {user_id}")
                    elif trigger == "manual_click" and action == "manual_read":
                        # User explicitly clicked read button - stronger positive signal
                        self._learn_from_manual_read(user_id, finding_id, content_data)
                        logger.debug(f"👤 PersonalizationManager: ✅ Processed manual read for user {user_id}")
                    else:
                        logger.debug(f"👤 PersonalizationManager: Processed generic read action for user {user_id}")
                        # Generic read action
                    
        elif event_type in ["research_activation", "feedback", "source_exploration"]:
            # These are explicit feedback - handle with higher weight
            logger.debug(f"👤 PersonalizationManager: Processing explicit engagement event for user {user_id}: {event_type}")

    def _learn_from_expansion_read(self, user_id: str, topic_name: str, finding_id: str, content_data: Dict[str, Any]) -> None:
        """Learn preferences from expansion-based read actions (moderate positive signal)."""
        try:
            logger.debug(f"👤 PersonalizationManager: Processing expansion-based read for user {user_id} on topic: {topic_name}")
            
            # Expansion-based reading indicates interest in the topic but less deliberate than manual clicking
            # Use moderate positive engagement score (0.6)
            engagement_score = 0.6
            
            # Extract any source types or content characteristics
            # Note: In a real implementation, you'd fetch the finding details to get source types
            # For now, we'll focus on topic-level learning
            
            # Log this as a moderate positive interaction
            self._log_learning_adaptation(
                user_id,
                "expansion_based_read",
                {"topic": topic_name, "finding_id": finding_id, "engagement_score": engagement_score},
                True
            )
            
        except Exception as e:
            logger.error(f"👤 PersonalizationManager: ❌ Error learning from expansion read for user {user_id}: {str(e)}", exc_info=True)

    def _learn_from_manual_read(self, user_id: str, finding_id: str, content_data: Dict[str, Any]) -> None:
        """Learn preferences from manual read button clicks (strong positive signal)."""
        try:
            logger.debug(f"👤 PersonalizationManager: Processing manual read for user {user_id}, finding: {finding_id}")
            
            # Manual read button clicking indicates deliberate positive engagement
            # Use strong positive engagement score (0.8)
            engagement_score = 0.8
            
            # This is a deliberate action showing content was valuable
            # In a real implementation, you'd fetch finding details to learn source preferences
            
            # Log this as a strong positive interaction
            self._log_learning_adaptation(
                user_id,
                "manual_read_action",
                {"finding_id": finding_id, "engagement_score": engagement_score},
                True
            )
            
        except Exception as e:
            logger.error(f"👤 PersonalizationManager: ❌ Error learning from manual read for user {user_id}: {str(e)}", exc_info=True)

    def _adjust_source_preferences(self, user_id: str, source_types: List[str], adjustment: float) -> None:
        """Adjust source type preferences based on engagement."""
        try:
            preferences = self.profile_manager.get_preferences(user_id)
            source_prefs = preferences["content_preferences"]["source_types"]
            
            changes_made = {}
            for source_type in source_types:
                if source_type in source_prefs:
                    old_value = source_prefs[source_type]
                    new_value = max(0.1, min(1.0, old_value + adjustment))
                    source_prefs[source_type] = new_value
                    changes_made[source_type] = {"old": old_value, "new": new_value}
            
            if changes_made:
                logger.info(f"👤 PersonalizationManager: Adjusting source preferences for user {user_id}: {changes_made}")
                self.profile_manager.update_preferences(user_id, {"content_preferences": {"source_types": source_prefs}})
                self._log_learning_adaptation(user_id, "source_preference_adjustment", changes_made, adjustment > 0)
                logger.debug(f"👤 PersonalizationManager: ✅ Source preference adjustment complete for user {user_id}")
            else:
                logger.debug(f"👤 PersonalizationManager: No source preference changes needed for user {user_id}")
                
        except Exception as e:
            logger.error(f"👤 PersonalizationManager: ❌ Error adjusting source preferences for user {user_id}: {str(e)}", exc_info=True)

    def _adjust_format_preferences(self, user_id: str, content_length: int, engagement_score: float) -> None:
        """Adjust format preferences based on content engagement."""
        try:
            if engagement_score > 0.8:  # High engagement from explicit feedback
                # Update formatting style preference based on content structure  
                has_structure = self._analyze_content_structure(content_length)
                if has_structure:
                    # Update user's formatting style preference to structured
                    current_prefs = self.profile_manager.get_user_preferences(user_id) or {}
                    format_prefs = current_prefs.get("format_preferences", {})
                    if format_prefs.get("formatting_style") != "structured":
                        format_prefs["formatting_style"] = "structured"
                        current_prefs["format_preferences"] = format_prefs
                        self.profile_manager.update_preferences(user_id, current_prefs)
                        
                        self._log_learning_adaptation(
                            user_id, 
                            "format_optimization", 
                            {"formatting_style": "structured"},
                            True
                        )
                
        except Exception as e:
            logger.error(f"Error adjusting format preferences for user {user_id}: {str(e)}")

    def _adjust_detail_preference(self, user_id: str, response_length: str, positive_feedback: bool) -> None:
        """Adjust detail level preferences based on chat engagement."""
        try:
            preferences = self.profile_manager.get_preferences(user_id)
            current_detail = preferences["format_preferences"]["detail_level"]
            
            if positive_feedback and response_length in ["long", "detailed"]:
                if current_detail == "concise":
                    new_detail = "balanced"
                elif current_detail == "balanced":
                    new_detail = "comprehensive"
                else:
                    new_detail = current_detail
            elif not positive_feedback and response_length in ["long", "detailed"]:
                if current_detail == "comprehensive":
                    new_detail = "balanced"
                elif current_detail == "balanced":
                    new_detail = "concise"
                else:
                    new_detail = current_detail
            else:
                new_detail = current_detail
            
            if new_detail != current_detail:
                self.profile_manager.update_preferences(
                    user_id, 
                    {"format_preferences": {"detail_level": new_detail}}
                )
                
                self._log_learning_adaptation(
                    user_id,
                    "detail_level_adjustment",
                    {"old": current_detail, "new": new_detail},
                    positive_feedback
                )
                
        except Exception as e:
            logger.error(f"Error adjusting detail preference for user {user_id}: {str(e)}")

    def _analyze_content_structure(self, content_length: int) -> bool:
        """Analyze if content benefits from structured formatting."""
        # Simple heuristic: longer content benefits from structure
        return content_length > 800

    def _log_learning_adaptation(self, user_id: str, adaptation_type: str, changes: Dict[str, Any], positive: bool) -> None:
        """Log automatic learning adaptations."""
        try:
            history = self.profile_manager.get_personalization_history(user_id)
            
            effectiveness_score = 0.8 if positive else 0.3
            
            log_entry = {
                "timestamp": time.time(),
                "adaptation_type": adaptation_type,
                "change_made": f"Automatically adjusted {adaptation_type} based on usage patterns",
                "changes_detail": changes,
                "user_feedback": None,
                "effectiveness_score": effectiveness_score
            }
            
            history["adaptation_log"].append(log_entry)
            
            # Keep only last 50 entries to prevent file bloat
            if len(history["adaptation_log"]) > 50:
                history["adaptation_log"] = history["adaptation_log"][-50:]
            
            self.profile_manager.storage.write(
                self.profile_manager._get_personalization_history_path(user_id),
                history
            )
            
        except Exception as e:
            logger.error(f"Error logging adaptation for user {user_id}: {str(e)}")

    def get_personalization_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get personalization context for request processing.

        Args:
            user_id: The ID of the user

        Returns:
            Personalization context dictionary
        """
        try:
            preferences = self.profile_manager.get_preferences(user_id)
            analytics = self.profile_manager.get_engagement_analytics(user_id)
            
            # Extract key personalization signals
            context = {
                "content_preferences": preferences.get("content_preferences", {}),
                "format_preferences": preferences.get("format_preferences", {}),
                "interaction_preferences": preferences.get("interaction_preferences", {}),
                "learned_adaptations": analytics.get("learned_adaptations", {}),
                "engagement_patterns": {
                    "preferred_sources": analytics["interaction_signals"].get("most_engaged_source_types", []),
                    "follow_up_frequency": analytics["interaction_signals"].get("follow_up_question_frequency", 0.0)
                }
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting personalization context for user {user_id}: {str(e)}")
            return {}

    def override_learned_behavior(self, user_id: str, override_type: str, override_value: Any, disable_learning: bool = False) -> bool:
        """
        Allow user to override learned behaviors.

        Args:
            user_id: The ID of the user
            override_type: Type of behavior to override
            override_value: New value to set
            disable_learning: Whether to disable further learning for this behavior

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"👤 PersonalizationManager: User {user_id} overriding behavior: {override_type} = {override_value}, disable_learning={disable_learning}")
            
            if override_type.startswith("source_preference_"):
                source_type = override_type.replace("source_preference_", "")
                preferences = self.profile_manager.get_preferences(user_id)
                old_value = preferences["content_preferences"]["source_types"].get(source_type, 0.0)
                preferences["content_preferences"]["source_types"][source_type] = override_value
                success = self.profile_manager.update_preferences(user_id, {"content_preferences": {"source_types": preferences["content_preferences"]["source_types"]}})
                logger.debug(f"👤 PersonalizationManager: Source preference override for user {user_id}: {source_type} {old_value} -> {override_value}")
                
            elif override_type == "detail_level":
                success = self.profile_manager.update_preferences(user_id, {"format_preferences": {"detail_level": override_value}})
                logger.debug(f"👤 PersonalizationManager: Detail level override for user {user_id}: {override_value}")
                
            elif override_type == "response_length":
                success = self.profile_manager.update_preferences(user_id, {"format_preferences": {"response_length": override_value}})
                logger.debug(f"👤 PersonalizationManager: Response length override for user {user_id}: {override_value}")
                
            else:
                logger.warning(f"PersonalizationManager: Unknown override type for user {user_id}: {override_type}")
                return False
            
            if success and disable_learning:
                # Mark this preference as user-controlled
                analytics = self.profile_manager.get_engagement_analytics(user_id)
                if "user_overrides" not in analytics:
                    analytics["user_overrides"] = {}
                analytics["user_overrides"][override_type] = {
                    "value": override_value,
                    "learning_disabled": True,
                    "timestamp": time.time()
                }
                self.profile_manager.storage.write(
                    self.profile_manager._get_engagement_analytics_path(user_id),
                    analytics
                )
                logger.info(f"👤 PersonalizationManager: 🚫 Disabled learning for user {user_id}, type: {override_type}")
            
            if success:
                self._log_learning_adaptation(
                    user_id,
                    "user_override",
                    {"type": override_type, "value": override_value, "learning_disabled": disable_learning},
                    True
                )
                logger.info(f"👤 PersonalizationManager: ✅ Successfully processed override for user {user_id}: {override_type}")
            else:
                logger.error(f"👤 PersonalizationManager: ❌ Failed to apply override for user {user_id}: {override_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"👤 PersonalizationManager: ❌ Error overriding behavior for user {user_id}: {str(e)}", exc_info=True)
            return False

    def get_learning_transparency_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get transparency data showing what the system has learned about the user.

        Args:
            user_id: The ID of the user

        Returns:
            Transparency data dictionary
        """
        try:
            preferences = self.profile_manager.get_preferences(user_id)
            analytics = self.profile_manager.get_engagement_analytics(user_id)
            history = self.profile_manager.get_personalization_history(user_id)
            
            transparency_data = {
                "explicit_preferences": preferences,
                "learned_behaviors": {
                    "source_preferences": preferences["content_preferences"]["source_types"],
                    "engagement_patterns": analytics["reading_patterns"],
                    "interaction_signals": analytics["interaction_signals"]
                },
                "adaptation_history": history["adaptation_log"][-10:],  # Last 10 adaptations
                "user_overrides": analytics.get("user_overrides", {}),
                "learning_stats": {
                    "total_adaptations": len(history["adaptation_log"]),
                    "recent_activity": len([entry for entry in history["adaptation_log"] if time.time() - entry["timestamp"] < 604800])  # Last week
                }
            }
            
            return transparency_data
            
        except Exception as e:
            logger.error(f"Error getting transparency data for user {user_id}: {str(e)}")
            return {}

    def _calculate_engagement_score(self, feedback=None, link_clicks=0, source_exploration=0, 
                                   session_continuation=0.0) -> float:
        """
        Calculate engagement score using new metrics (replacing reading time).
        
        Returns:
            Float between 0.0 and 1.0 representing engagement level
        """
        score = 0.0
        
        # Thumbs feedback (30% weight)
        if feedback == "up":
            score += 0.3
        elif feedback == "down":
            score -= 0.1  # Slight negative weight
        
        # Session continuation (25% weight) 
        score += session_continuation * 0.25
        
        # Link clicks (20% weight) - normalized
        normalized_clicks = min(1.0, link_clicks / 3.0)  # 3+ clicks = max score
        score += normalized_clicks * 0.2
        
        # Source exploration (15% weight)
        if source_exploration > 0:
            score += 0.15
        
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
