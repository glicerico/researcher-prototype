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
from research_graph_builder import research_graph
from services.motivation import MotivationSystem


class AutonomousResearcher:
    """
    LangGraph-based autonomous research engine that conducts background research on subscribed topics.
    """

    def __init__(self, profile_manager: ProfileManager, research_manager: ResearchManager, motivation_config_override: dict = None):
        """Initialize the autonomous researcher."""
        self.profile_manager = profile_manager
        self.research_manager = research_manager
        self.research_graph = research_graph
        self.is_running = False
        self.research_task = None
        
        # Create motivation system with config overrides if provided
        if motivation_config_override:
            from services.motivation import DriveConfig
            drives_config = DriveConfig()
            for key, value in motivation_config_override.items():
                if hasattr(drives_config, key):
                    setattr(drives_config, key, value)
            self.motivation = MotivationSystem(drives_config)
        else:
            self.motivation = MotivationSystem()
            
        self.check_interval = config.MOTIVATION_CHECK_INTERVAL

        # Configure research parameters from config
        self.max_topics_per_user = config.RESEARCH_MAX_TOPICS_PER_USER
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        self.enabled = config.RESEARCH_ENGINE_ENABLED

        logger.info(
            f"🔬 LangGraph Autonomous Researcher initialized - Enabled: {self.enabled}"
        )

    async def start(self):
        """Start the autonomous research engine."""
        if not self.enabled:
            logger.info("""🔬 Autonomous Research Engine is disabled in configuration.
                        It can be enabled it in the Research Topics dashboard.""")
            return

        if self.is_running:
            logger.warning("🔬 Autonomous Research Engine is already running")
            return

        self.is_running = True
        logger.info("🔬 Starting LangGraph Autonomous Research Engine...")

        # Reset motivation timer to prevent huge time deltas from accumulated server uptime
        self.motivation.last_tick = time.time()
        logger.info(f"🔬 Reset motivation timer - Current drives: B:{self.motivation.boredom:.2f} C:{self.motivation.curiosity:.2f} T:{self.motivation.tiredness:.2f} S:{self.motivation.satisfaction:.2f}")

        # Start the research loop
        self.research_task = asyncio.create_task(self._research_loop())

    async def stop(self):
        """Stop the autonomous research engine."""
        if not self.is_running:
            return

        logger.info("🔬 Stopping LangGraph Autonomous Research Engine...")
        self.is_running = False

        if self.research_task:
            self.research_task.cancel()
            try:
                await self.research_task
            except asyncio.CancelledError:
                pass

        logger.info("🔬 LangGraph Autonomous Research Engine stopped")

    def enable(self):
        """Enable the research engine."""
        self.enabled = True
        logger.info("🔬 Autonomous Research Engine enabled")

    def disable(self):
        """Disable the research engine."""
        self.enabled = False
        logger.info("🔬 Autonomous Research Engine disabled")

    def toggle_enabled(self):
        """Toggle the enabled state of the research engine."""
        self.enabled = not self.enabled
        logger.info(f"🔬 Autonomous Research Engine {'enabled' if self.enabled else 'disabled'}")
        return self.enabled

    def is_enabled(self) -> bool:
        """Check if the research engine is enabled."""
        return self.enabled

    async def _research_loop(self):
        """Main loop that checks motivation and triggers research."""
        while self.is_running:
            try:
                await asyncio.sleep(self.check_interval)
                self.motivation.tick()

                if not self.is_running:
                    break

                if self.motivation.should_research():
                    logger.info("🔬 Motivation threshold reached - starting research cycle")
                    result = await self._conduct_research_cycle()
                    self.motivation.on_research_completed(result.get("average_quality", 0.0))
                    logger.info("🔬 LangGraph research cycle completed.")

            except asyncio.CancelledError:
                logger.info("🔬 Research loop cancelled")
                break
            except Exception as e:
                logger.error(f"🔬 Error in research loop: {str(e)}", exc_info=True)
                # Sleep for a shorter time on error to retry
                await asyncio.sleep(300)  # 5 minutes

    async def _conduct_research_cycle(self):
        """Conduct a complete research cycle for all users with active topics."""
        try:
            # Get all users
            all_users = self.profile_manager.list_users()
            logger.info(f"🔬 Scanning {len(all_users)} users for active research topics...")

            total_topics_researched = 0
            total_findings_stored = 0
            quality_scores: List[float] = []

            for user_id in all_users:
                try:
                    # Get active research topics for this user
                    active_topics = self.research_manager.get_active_research_topics(user_id)

                    if not active_topics:
                        continue

                    logger.info(f"🔬 User {user_id} has {len(active_topics)} active research topics")

                    # Limit topics per user
                    topics_to_research = active_topics[: self.max_topics_per_user]

                    for topic in topics_to_research:
                        try:
                            logger.info(f"🔬 Researching topic: {topic['topic_name']} for user {user_id}")

                            # Conduct research for this topic using LangGraph
                            research_result = await self._research_topic_with_langgraph(user_id, topic)

                            total_topics_researched += 1

                            if research_result and research_result.get("stored", False):
                                total_findings_stored += 1

                            if research_result and research_result.get("quality_score"):
                                quality_scores.append(research_result.get("quality_score"))

                            # Small delay between topics to avoid overwhelming APIs
                            await asyncio.sleep(1)

                        except Exception as e:
                            logger.error(
                                f"🔬 Error researching topic {topic.get('topic_name')} for user {user_id}: {str(e)}"
                            )
                            continue

                    # Cleanup old findings for this user
                    self.research_manager.cleanup_old_research_findings(user_id, config.RESEARCH_FINDINGS_RETENTION_DAYS)

                except Exception as e:
                    logger.error(f"🔬 Error processing user {user_id}: {str(e)}")
                    continue

            logger.info(
                f"🔬 LangGraph research cycle completed: {total_topics_researched} topics researched, {total_findings_stored} findings stored"
            )

            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            return {
                "topics_researched": total_topics_researched,
                "findings_stored": total_findings_stored,
                "average_quality": avg_quality,
            }

        except Exception as e:
            logger.error(f"🔬 Error in research cycle: {str(e)}", exc_info=True)
            return {
                "topics_researched": 0,
                "findings_stored": 0,
                "average_quality": 0.0,
            }


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
                "max_tokens": 2000,
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
                    await asyncio.sleep(0.5)

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

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the research engine."""
        return {
            "enabled": self.enabled,
            "running": self.is_running,
            "quality_threshold": self.quality_threshold,
            "max_topics_per_user": self.max_topics_per_user,
            "retention_days": config.RESEARCH_FINDINGS_RETENTION_DAYS,
            "engine_type": "LangGraph-based",
            "research_graph_nodes": [
                "research_initializer",
                "research_query_generator",
                "search",
                "research_quality_assessor",
                "research_deduplication",
                "research_storage",
            ],
        }


# Global instance
autonomous_researcher: Optional[AutonomousResearcher] = None


def get_autonomous_researcher() -> Optional[AutonomousResearcher]:
    """Get the global autonomous researcher instance."""
    return autonomous_researcher


def initialize_autonomous_researcher(profile_manager: ProfileManager, research_manager: ResearchManager, motivation_config_override: dict = None) -> AutonomousResearcher:
    """Initialize the global LangGraph autonomous researcher instance."""
    global autonomous_researcher
    autonomous_researcher = AutonomousResearcher(profile_manager, research_manager, motivation_config_override)
    return autonomous_researcher
