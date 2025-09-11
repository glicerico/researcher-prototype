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
        self.is_running = False
        self.research_task = None
        
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
            
        self.check_interval = config.MOTIVATION_CHECK_INTERVAL

        # Configure research parameters from config
        self.max_topics_per_user = config.RESEARCH_MAX_TOPICS_PER_USER
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        self.enabled = config.RESEARCH_ENGINE_ENABLED

        # Topic expansion service (Phase 2 wiring)
        try:
            from dependencies import zep_manager as _zep_manager_singleton  # type: ignore
            self.topic_expansion_service = TopicExpansionService(_zep_manager_singleton, self.research_manager)
        except Exception:
            # Fallback: create a placeholder that returns no candidates
            self.topic_expansion_service = TopicExpansionService(None, self.research_manager)  # type: ignore[arg-type]

        # Concurrency guard for expansions
        self._expansion_semaphore = asyncio.Semaphore(max(1, int(getattr(config, 'EXPANSION_MAX_PARALLEL', 2))))

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
            # Get all users; coerce to list and fall back to guest if empty/invalid
            users_raw = self.profile_manager.list_users()
            try:
                users_list = list(users_raw) if users_raw is not None else []
            except Exception:
                users_list = []
            all_users = users_list or ["guest"]
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

                    # Use engagement-aware motivation system to prioritize topics
                    prioritized_topics = self.motivation.evaluate_topics(user_id, active_topics)
                    
                    if not prioritized_topics:
                        logger.debug(f"🔬 No topics motivated for research for user {user_id}")
                        continue

                    # Limit topics per user (already sorted by priority)
                    topics_to_research = prioritized_topics[: self.max_topics_per_user]
                    logger.info(f"🔬 Selected {len(topics_to_research)} prioritized topics for user {user_id}")

                    for topic in topics_to_research:
                        try:
                            root_name = topic['topic_name']
                            logger.info(f"🔬 Researching topic: {root_name} for user {user_id}")

                            tasks = []

                            async def _run_root() -> Optional[Dict[str, Any]]:
                                return await self._research_topic_with_langgraph(user_id, topic)

                            tasks.append(asyncio.create_task(_run_root()))

                            # Phase 2+: schedule expansions with lifecycle gating
                            created_expansions: List[Dict[str, Any]] = []
                            if getattr(config, 'EXPANSION_ENABLED', False):
                                # Determine gating for child expansion
                                depth = int(topic.get('expansion_depth', 0) or 0)
                                is_expansion = bool(topic.get('is_expansion', False))
                                backoff_until = float(topic.get('last_backoff_until', 0) or 0)
                                now_ts = time.time()

                                allowed_for_children = True
                                # Apply gating only for expansion topics (child generations)
                                if is_expansion:
                                    allowed_for_children = (
                                        bool(topic.get('child_expansion_enabled', False))
                                        and depth < int(getattr(config, 'EXPANSION_MAX_DEPTH', 2))
                                        and backoff_until <= now_ts
                                    )

                                if not allowed_for_children:
                                    logger.info(
                                        f"🔬 Skipping child expansion for '{root_name}' (depth={depth}, enabled={topic.get('child_expansion_enabled', False)}, backoff_until={int(backoff_until)})"
                                    )
                                else:
                                    # Generate candidates
                                    candidates = await self.topic_expansion_service.generate_candidates(user_id, topic)
                                    logger.debug(f"🔬 Expansion candidates for '{root_name}': {len(candidates)}")
                                    if candidates:
                                        k = min(getattr(config, 'EXPLORATION_PER_ROOT_MAX', 2), len(candidates))
                                        selected = candidates[:k]
                                        logger.info(
                                            f"🔬 Choosing {len(selected)}/{len(candidates)} expansions for '{root_name}'"
                                        )
                                        for cand in selected:
                                            desc = f"Auto expansion of {root_name}"
                                            # Compute child depth
                                            child_depth = min(depth + 1, int(getattr(config, 'EXPANSION_MAX_DEPTH', 2)))
                                            extra_meta = {
                                                "is_expansion": True,
                                                "origin": {
                                                    "type": "expansion",
                                                    "parent_topic": root_name,
                                                    "method": cand.source,
                                                    "similarity": cand.similarity,
                                                    "rationale": cand.rationale,
                                                },
                                                "expansion_depth": child_depth,
                                                "child_expansion_enabled": False,
                                                "expansion_status": "active",
                                                "last_evaluated_at": now_ts,
                                            }
                                            res = self.research_manager.add_custom_topic(
                                                user_id=user_id,
                                                topic_name=cand.name,
                                                description=desc,
                                                confidence_score=0.8,
                                                enable_research=True,
                                                extra=extra_meta,
                                            )
                                            if res and res.get('success'):
                                                topic_obj = res.get('topic', {})
                                                created_expansions.append({
                                                    "topic": topic_obj,
                                                    "candidate": cand,
                                                })
                                                sim_txt = (
                                                    f"{cand.similarity:.2f}" if isinstance(cand.similarity, (int, float)) else "n/a"
                                                )
                                                logger.info(
                                                    f"🔬 Scheduled expansion: {cand.name} (source={cand.source}, sim={sim_txt}, depth={child_depth})"
                                                )
                                            else:
                                                logger.debug(
                                                    f"🔬 Skipping expansion '{cand.name}' - duplicate or failed to persist"
                                                )
                                
                                
                            

                            # Launch expansion research tasks (bounded by semaphore)
                            for item in created_expansions:
                                exp_topic = item["topic"]
                                async def _run_expansion(t=exp_topic) -> Optional[Dict[str, Any]]:
                                    async with self._expansion_semaphore:
                                        return await self._research_topic_with_langgraph(user_id, t)
                                tasks.append(asyncio.create_task(_run_expansion()))

                            results = await asyncio.gather(*tasks, return_exceptions=True)

                            for res in results:
                                if isinstance(res, Exception):
                                    logger.error(f"🔬 Error in research task: {res}")
                                    continue
                                total_topics_researched += 1
                                if res and res.get("stored", False):
                                    total_findings_stored += 1
                                if res and res.get("quality_score"):
                                    quality_scores.append(res.get("quality_score"))

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

            # Lifecycle update per user
            try:
                for user_id in self.profile_manager.list_users():
                    await self._update_expansion_lifecycle(user_id)
            except Exception as e:
                logger.error(f"Lifecycle update failed: {str(e)}")

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

    async def _update_expansion_lifecycle(self, user_id: str) -> None:
        """Evaluate and update lifecycle state for expansion topics for a user."""
        try:
            topics_data = self.research_manager.get_user_topics(user_id)
            if not topics_data:
                return
            now_ts = time.time()
            promoted = paused = retired = 0
            changed = False
            window_days = int(getattr(config, 'EXPANSION_ENGAGEMENT_WINDOW_DAYS', 7))
            promote_thr = float(getattr(config, 'EXPANSION_PROMOTE_ENGAGEMENT', 0.35))
            retire_thr = float(getattr(config, 'EXPANSION_RETIRE_ENGAGEMENT', 0.1))
            min_quality = float(getattr(config, 'EXPANSION_MIN_QUALITY', 0.6))
            backoff_days = int(getattr(config, 'EXPANSION_BACKOFF_DAYS', 7))
            retire_ttl_days = int(getattr(config, 'EXPANSION_RETIRE_TTL_DAYS', 30))

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
