"""
Autonomous Research Engine using LangGraph for conducting background research on user-subscribed topics.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import logging
from services.logging_config import get_logger

logger = get_logger(__name__)

# Import configuration and existing components
import config
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager
from services.personalization_manager import PersonalizationManager
from research_graph_builder import research_graph
from services.motivation import MotivationSystem
from services.topic_expansion_service import TopicExpansionService


class AutonomousResearcher:
    """
    LangGraph-based autonomous research engine that conducts background research on subscribed topics.
    """

    def __init__(self, profile_manager: ProfileManager, research_manager: ResearchManager, motivation_config_override: dict = None, personalization_manager: PersonalizationManager = None):
        """Initialize the autonomous researcher."""
        self.profile_manager = profile_manager
        self.research_manager = research_manager
        self.research_graph = research_graph
        
        # Use provided PersonalizationManager or create one using the same storage as profile_manager
        if personalization_manager:
            self.personalization_manager = personalization_manager
        else:
            # Extract storage manager from profile_manager to avoid duplication
            self.personalization_manager = PersonalizationManager(profile_manager.storage, profile_manager)
        
        # Create motivation system with config overrides if provided
        if motivation_config_override:
            from services.motivation import DriveConfig
            drives_config = DriveConfig()
            for key, value in motivation_config_override.items():
                if hasattr(drives_config, key):
                    setattr(drives_config, key, value)
            self.motivation = MotivationSystem(drives_config, self.personalization_manager)
        else:
            self.motivation = MotivationSystem(personalization_manager=self.personalization_manager)

        # Configure research parameters from config
        self.max_topics_per_user = config.RESEARCH_MAX_TOPICS_PER_USER
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        self.enabled = True

        # Initialize topic expansion service
        try:
            from dependencies import zep_manager as _zep_manager_singleton  # type: ignore
            self.topic_expansion_service = TopicExpansionService(_zep_manager_singleton, self.research_manager)
        except Exception:
            # Fallback: create a placeholder that returns no candidates
            self.topic_expansion_service = TopicExpansionService(None, self.research_manager)  # type: ignore[arg-type]

        # Concurrency guard for expansions
        self._expansion_semaphore = asyncio.Semaphore(max(1, config.EXPANSION_MAX_PARALLEL))

    def get_recent_average_quality(self, user_id: str, topic_name: str, window_days: int) -> float:
        """Compute recent average quality over window for a topic."""
        try:
            now = time.time()
            window_start = now - (window_days * 24 * 3600)
            findings = self.research_manager.get_research_findings_for_api(user_id, topic_name, unread_only=False)
            scores = [f.get("quality_score") for f in findings if f.get("research_time", 0) >= window_start and isinstance(f.get("quality_score"), (int, float))]
            if not scores:
                return 0.0
            return sum(scores) / len(scores)
        except Exception:
            return 0.0

        logger.info(
            f"🔬 LangGraph Autonomous Researcher initialized - Enabled: {self.enabled}"
        )

    async def _research_topic_with_langgraph(self, user_id: str, topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Conduct research on a specific topic using the LangGraph research workflow.

        Args:
            user_id: ID of the user
            topic: Topic dictionary with research details

        Returns:
            Research result summary if successful, None otherwise
        """
        try:
            topic_name = topic["topic_name"]
            topic_description = topic.get("description", "")
            last_researched = topic.get("last_researched")

            logger.info(f"🔬 Starting LangGraph research workflow for topic: {topic_name}")

            # Create initial state for the research graph
            research_state = {
                "messages": [],  # Will be populated by research_initializer_node
                "model": config.RESEARCH_MODEL,
                "temperature": 0.3,
                "max_tokens": config.RESEARCH_MAX_TOKENS,
                "personality": {"style": "research", "tone": "analytical"},
                "current_module": None,
                "module_results": {},
                "workflow_context": {
                    "research_context": {
                        "topic_name": topic_name,
                        "topic_description": topic_description,
                        "user_id": user_id,
                        "last_researched": last_researched,
                        "model": config.RESEARCH_MODEL,
                    }
                },
                "user_id": user_id,
                "routing_analysis": None,
                "thread_id": None,  # Will be generated by research_initializer_node
                "memory_context": None,
            }

            # Run the research workflow through LangGraph
            logger.debug(f"🔬 Invoking research graph for topic: {topic_name}")
            research_result = await self.research_graph.ainvoke(research_state)
            try:
                # Best-effort: capture thread id if created by initializer node
                thread_id = research_result.get("thread_id") or research_result.get("module_results", {}).get("research_initializer", {}).get("thread_id")
                if thread_id:
                    logger.debug(f"🔬 Research workflow thread_id: {thread_id}")
            except Exception:
                pass

            # Extract results from the workflow
            storage_results = research_result.get("module_results", {}).get("research_storage", {})

            if storage_results.get("success", False):
                stored = storage_results.get("stored", False)
                quality_score = storage_results.get("quality_score", 0.0)

                if stored:
                    logger.info(
                        f"🔬 LangGraph research completed successfully for {topic_name} - Finding stored (quality: {quality_score:.2f})"
                    )
                    return {
                        "success": True,
                        "stored": True,
                        "quality_score": quality_score,
                        "finding_id": storage_results.get("finding_id"),
                        "insights_count": storage_results.get("insights_count", 0),
                    }
                else:
                    reason = storage_results.get("reason", "Unknown reason")
                    logger.info(f"🔬 LangGraph research completed for {topic_name} - Finding not stored: {reason}")
                    return {"success": True, "stored": False, "reason": reason, "quality_score": quality_score}
            else:
                error = storage_results.get("error", "Unknown error in storage")
                logger.error(f"🔬 LangGraph research failed for {topic_name}: {error}")
                return {"success": False, "error": error, "stored": False}

        except Exception as e:
            logger.error(
                f"🔬 Error in LangGraph research workflow for topic {topic.get('topic_name', 'unknown')}: {str(e)}",
                exc_info=True,
            )
            return {"success": False, "error": str(e), "stored": False}

    async def _update_expansion_lifecycle(self, user_id: str) -> None:
        """Evaluate and update lifecycle state for expansion topics for a user."""
        try:
            topics_data = self.research_manager.get_user_topics(user_id)
            if not topics_data:
                return
            now_ts = time.time()
            promoted = paused = retired = 0
            changed = False
            window_days = config.EXPANSION_ENGAGEMENT_WINDOW_DAYS
            promote_thr = config.EXPANSION_PROMOTE_ENGAGEMENT
            retire_thr = config.EXPANSION_RETIRE_ENGAGEMENT
            min_quality = config.EXPANSION_MIN_QUALITY
            backoff_days = config.EXPANSION_BACKOFF_DAYS
            retire_ttl_days = config.EXPANSION_RETIRE_TTL_DAYS

            for sid, session_topics in topics_data.get('sessions', {}).items():
                for topic in session_topics:
                    if not topic.get('is_expansion', False):
                        continue
                    name = topic.get('topic_name')
                    depth = int(topic.get('expansion_depth', 0) or 0)
                    engagement = 0.0
                    try:
                        engagement = self.motivation._get_topic_engagement_score(user_id, name)
                    except Exception:
                        engagement = 0.0
                    avg_quality = self.get_recent_average_quality(user_id, name, window_days)

                    status = topic.get('expansion_status', 'active')
                    last_eval = float(topic.get('last_evaluated_at', 0) or 0)
                    backoff_until = float(topic.get('last_backoff_until', 0) or 0)

                    decision_debug = f"topic='{name}' depth={depth} engagement={engagement:.2f} avg_q={avg_quality:.2f} status={status}"

                    # Promote to allow children
                    if engagement >= promote_thr and avg_quality >= min_quality:
                        if not topic.get('child_expansion_enabled', False) or status != 'active':
                            topic['child_expansion_enabled'] = True
                            topic['expansion_status'] = 'active'
                            changed = True
                            promoted += 1
                            logger.debug(f"Lifecycle promote: {decision_debug}")
                        topic['last_evaluated_at'] = now_ts
                        continue

                    # Assess interactions in window via findings read/bookmark/integration
                    findings = self.research_manager.get_research_findings_for_api(user_id, name, unread_only=False)
                    window_start = now_ts - window_days * 24 * 3600
                    any_interaction = any(
                        (f.get('read', False) or f.get('bookmarked', False) or f.get('integrated', False)) and f.get('research_time', 0) >= window_start
                        for f in findings
                    )

                    # Retire after TTL if still cold (check before pausing again)
                    if status == 'paused' and last_eval and (now_ts - last_eval) >= retire_ttl_days * 24 * 3600:
                        if engagement < retire_thr and not any_interaction:
                            topic['expansion_status'] = 'retired'
                            topic['last_evaluated_at'] = now_ts
                            changed = True
                            retired += 1
                            logger.debug(f"Lifecycle retire: {decision_debug}")
                            continue

                    # Pause on cold engagement and no interactions in window
                    if engagement < retire_thr and not any_interaction:
                        topic['is_active_research'] = False
                        topic['child_expansion_enabled'] = False
                        topic['expansion_status'] = 'paused'
                        topic['last_backoff_until'] = now_ts + backoff_days * 24 * 3600
                        topic['last_evaluated_at'] = now_ts
                        changed = True
                        paused += 1
                        logger.debug(f"Lifecycle pause: {decision_debug}")
                        continue

                    # No action
                    topic['last_evaluated_at'] = now_ts

            if changed:
                self.research_manager.save_user_topics(user_id, topics_data)
            logger.info(f"Lifecycle update for {user_id}: promoted={promoted}, paused={paused}, retired={retired}")

        except Exception as e:
            logger.error(f"Error updating expansion lifecycle for user {user_id}: {str(e)}")

    def _should_allow_expansion(self, user_id: str) -> bool:
        """Check if user has capacity for more expansion topics based on breadth control limits."""
        try:
            topics_data = self.research_manager.get_user_topics(user_id)
            if not topics_data:
                return True
                
            expansion_count = 0
            unreviewed_count = 0
            
            for sid, session_topics in topics_data.get('sessions', {}).items():
                for topic in session_topics:
                    if topic.get('is_expansion', False):
                        expansion_count += 1
                        
                        # Check if topic has been "reviewed" (engaged with)
                        try:
                            topic_name = topic.get('topic_name', '')
                            engagement = self.motivation._get_topic_engagement_score(user_id, topic_name)
                            if engagement < config.EXPANSION_REVIEW_ENGAGEMENT_THRESHOLD:
                                unreviewed_count += 1
                        except Exception as e:
                            # If engagement calculation fails, assume unreviewed
                            logger.debug(f"Failed to get engagement for {topic.get('topic_name')}: {e}")
                            unreviewed_count += 1
            
            # Check breadth control limits
            if expansion_count >= config.EXPANSION_MAX_TOTAL_TOPICS_PER_USER:
                logger.info(f"🔬 Expansion blocked: {expansion_count} topics >= limit {config.EXPANSION_MAX_TOTAL_TOPICS_PER_USER}")
                return False
                
            if unreviewed_count >= config.EXPANSION_MAX_UNREVIEWED_TOPICS:
                logger.info(f"🔬 Expansion blocked: {unreviewed_count} unreviewed topics >= limit {config.EXPANSION_MAX_UNREVIEWED_TOPICS}")
                return False
            
            logger.debug(f"🔬 Breadth control check passed: {expansion_count}/{config.EXPANSION_MAX_TOTAL_TOPICS_PER_USER} total, {unreviewed_count}/{config.EXPANSION_MAX_UNREVIEWED_TOPICS} unreviewed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking expansion breadth control for user {user_id}: {str(e)}")
            # Err on the side of caution - block expansion if check fails
            return False

    async def trigger_research_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Manually trigger research for a specific user using LangGraph (for testing/API).

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with research results summary
        """
        try:
            logger.info(f"🔬 Manual LangGraph research trigger for user: {user_id}")

            # Get active research topics for this user
            active_topics = self.research_manager.get_active_research_topics(user_id)

            if not active_topics:
                return {
                    "success": True,
                    "message": "No active research topics found",
                    "topics_researched": 0,
                    "findings_stored": 0,
                }

            # Limit topics
            topics_to_research = active_topics[: self.max_topics_per_user]
            topics_researched = 0
            findings_stored = 0
            research_details = []

            for topic in topics_to_research:
                try:
                    logger.info(f"🔬 Manual LangGraph research for topic: {topic['topic_name']}")

                    # Force research using LangGraph regardless of last research time
                    research_result = await self._research_topic_with_langgraph(user_id, topic)

                    topics_researched += 1

                    if research_result and research_result.get("stored", False):
                        findings_stored += 1

                    research_details.append(
                        {
                            "topic_name": topic["topic_name"],
                            "success": research_result.get("success", False) if research_result else False,
                            "stored": research_result.get("stored", False) if research_result else False,
                            "quality_score": research_result.get("quality_score", 0.0) if research_result else 0.0,
                            "reason": research_result.get("reason") if research_result else None,
                            "error": research_result.get("error") if research_result else None,
                        }
                    )

                    # Small delay between topics
                    await asyncio.sleep(config.RESEARCH_MANUAL_DELAY)

                except Exception as e:
                    logger.error(f"🔬 Error in manual LangGraph research for topic {topic.get('topic_name')}: {str(e)}")
                    research_details.append(
                        {
                            "topic_name": topic.get("topic_name", "Unknown"),
                            "success": False,
                            "stored": False,
                            "error": str(e),
                        }
                    )
                    continue

            # Cleanup old findings
            self.research_manager.cleanup_old_research_findings(user_id, config.RESEARCH_FINDINGS_RETENTION_DAYS)

            return {
                "success": True,
                "message": f"Manual LangGraph research completed for {topics_researched} topics",
                "topics_researched": topics_researched,
                "findings_stored": findings_stored,
                "total_active_topics": len(active_topics),
                "research_details": research_details,
            }

        except Exception as e:
            logger.error(f"🔬 Error in manual LangGraph research trigger: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e), "topics_researched": 0, "findings_stored": 0}
