"""Simple motivation system for the autonomous researcher."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class DriveConfig:
    boredom_rate: float = config.MOTIVATION_BOREDOM_RATE
    curiosity_decay: float = config.MOTIVATION_CURIOSITY_DECAY
    tiredness_decay: float = config.MOTIVATION_TIREDNESS_DECAY
    satisfaction_decay: float = config.MOTIVATION_SATISFACTION_DECAY
    threshold: float = config.MOTIVATION_THRESHOLD
    topic_threshold: float = config.TOPIC_MOTIVATION_THRESHOLD
    engagement_weight: float = config.TOPIC_ENGAGEMENT_WEIGHT
    quality_weight: float = config.TOPIC_QUALITY_WEIGHT
    staleness_scale: float = config.TOPIC_STALENESS_SCALE


class MotivationSystem:
    """Track motivation drives and decide when research should occur."""

    def __init__(self, drives: DriveConfig | None = None, personalization_manager=None) -> None:
        self.drives = drives or DriveConfig()
        self.personalization_manager = personalization_manager
        self.boredom = 0.0
        self.curiosity = 0.0
        self.tiredness = 0.0
        self.satisfaction = 0.0
        self.last_tick = time.time()
        logger.info(f"Motivation system initialized with threshold: {self.drives.threshold}, topic threshold: {self.drives.topic_threshold}")

    def tick(self) -> None:
        """Update drive levels based on time since last tick."""
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now

        old_boredom = self.boredom
        old_curiosity = self.curiosity
        old_tiredness = self.tiredness
        old_satisfaction = self.satisfaction

        self.boredom = min(1.0, self.boredom + dt * self.drives.boredom_rate)
        self.curiosity = max(0.0, self.curiosity - dt * self.drives.curiosity_decay)
        self.tiredness = max(0.0, self.tiredness - dt * self.drives.tiredness_decay)
        self.satisfaction = max(0.0, self.satisfaction - dt * self.drives.satisfaction_decay)
        
        # Log significant changes (> 0.1) or every 5 minutes
        if (abs(self.boredom - old_boredom) > 0.1 or 
            abs(self.curiosity - old_curiosity) > 0.1 or
            abs(self.tiredness - old_tiredness) > 0.1 or
            abs(self.satisfaction - old_satisfaction) > 0.1 or
            dt > 300):  # 5 minutes
            logger.debug(f"Drive update after {dt:.1f}s - Boredom: {self.boredom:.2f} (+{self.boredom-old_boredom:.2f}), "
                        f"Curiosity: {self.curiosity:.2f} ({self.curiosity-old_curiosity:+.2f}), "
                        f"Tiredness: {self.tiredness:.2f} ({self.tiredness-old_tiredness:+.2f}), "
                        f"Satisfaction: {self.satisfaction:.2f} ({self.satisfaction-old_satisfaction:+.2f}), "
                        f"Impetus: {self.impetus():.2f}")

    def on_user_activity(self) -> None:
        """Increase curiosity and reduce boredom when user interacts."""
        old_curiosity = self.curiosity
        old_boredom = self.boredom
        
        self.curiosity = min(1.0, self.curiosity + 0.3)
        self.boredom = max(0.0, self.boredom - 0.1)
        
        logger.info(f"User activity detected - Curiosity: {old_curiosity:.2f} → {self.curiosity:.2f}, "
                   f"Boredom: {old_boredom:.2f} → {self.boredom:.2f}, "
                   f"New impetus: {self.impetus():.2f}")

    def on_research_completed(self, quality_score: float = 0.5) -> None:
        """Update drives after research completes."""
        old_tiredness = self.tiredness
        old_satisfaction = self.satisfaction
        old_curiosity = self.curiosity
        old_boredom = self.boredom
        
        # Tiredness increase scales with quality (good research is less tiring)
        tiredness_increase = 0.4 - (quality_score * 0.2)  # 0.4 for bad, 0.2 for excellent
        self.tiredness = min(1.0, self.tiredness + tiredness_increase)
        
        # Satisfaction scales with quality
        satisfaction_increase = quality_score * 0.8  # Up to 0.8 for excellent research
        self.satisfaction = min(1.0, self.satisfaction + satisfaction_increase)
        
        # Curiosity reduction scales inversely with quality (good research satisfies more)
        curiosity_reduction = 0.1 + (quality_score * 0.3)  # 0.1-0.4 based on quality
        self.curiosity = max(0.0, self.curiosity - curiosity_reduction)
        
        # Boredom reduction is consistent (research always reduces boredom)
        self.boredom = max(0.0, self.boredom - 0.4)
        
        logger.info(f"Research completed (quality: {quality_score:.2f}) - "
                   f"Tiredness: {old_tiredness:.2f} → {self.tiredness:.2f} (+{self.tiredness-old_tiredness:.2f}), "
                   f"Satisfaction: {old_satisfaction:.2f} → {self.satisfaction:.2f} (+{self.satisfaction-old_satisfaction:.2f}), "
                   f"Curiosity: {old_curiosity:.2f} → {self.curiosity:.2f} ({self.curiosity-old_curiosity:+.2f}), "
                   f"Boredom: {old_boredom:.2f} → {self.boredom:.2f} ({self.boredom-old_boredom:+.2f}), "
                   f"New impetus: {self.impetus():.2f}")

    def impetus(self) -> float:
        """Compute the overall desire to research."""
        return self.boredom + self.curiosity + 0.5 * self.satisfaction - self.tiredness

    def should_research(self) -> bool:
        """Return True if motivation threshold reached."""
        current_impetus = self.impetus()
        should_do_research = current_impetus >= self.drives.threshold
        
        if should_do_research:
            logger.info(f"Research triggered! Impetus {current_impetus:.2f} >= threshold {self.drives.threshold:.2f} "
                       f"(Boredom: {self.boredom:.2f}, Curiosity: {self.curiosity:.2f}, "
                       f"Satisfaction: {self.satisfaction:.2f}, Tiredness: {self.tiredness:.2f})")
        
        return should_do_research

    def _get_topic_engagement_score(self, user_id: str, topic_name: str) -> float:
        """
        Extract engagement score focusing heavily on research result interactions.
        
        Primary signal: How many research findings for this topic the user has actually read.
        Secondary signals: General engagement analytics if available.
        """
        if not self.personalization_manager:
            return 0.0
            
        try:
            engagement_score = 0.0
            
            # PRIMARY SIGNAL: Research findings interaction (HEAVILY WEIGHTED)
            research_findings_score = self._get_research_findings_engagement(user_id, topic_name)
            engagement_score += research_findings_score * 2.0  # Heavy weight for actual research interaction
            
            # SECONDARY SIGNAL: General engagement analytics (if available)
            analytics_score = self._get_analytics_engagement(user_id, topic_name)  
            engagement_score += analytics_score * 0.5  # Lower weight for general analytics
            
            # Normalize to 0-1 range but allow research findings to dominate
            return min(engagement_score / 3.0, 1.0)
            
        except Exception as e:
            logger.debug(f"Error getting topic engagement score for {topic_name}: {str(e)}")
            return 0.0
    
    def _get_research_findings_engagement(self, user_id: str, topic_name: str) -> float:
        """
        Calculate engagement based on research findings interactions.
        This is the primary signal for per-topic motivation.
        """
        try:
            # Import here to avoid circular dependencies
            from storage.research_manager import ResearchManager
            research_manager = ResearchManager(
                self.personalization_manager.storage, 
                self.personalization_manager.profile_manager
            )
            
            # Get all findings for this user and topic
            all_findings = research_manager.get_research_findings_for_api(user_id, topic_name, unread_only=False)
            if not all_findings:
                return 0.0
            
            total_findings = len(all_findings)
            read_findings = sum(1 for f in all_findings if f.get('read', False))
            
            # Base engagement: percentage of findings read
            read_percentage = read_findings / total_findings if total_findings > 0 else 0.0
            
            # Bonus for recent reads (findings read in last 7 days get extra weight)
            import time
            recent_threshold = time.time() - (7 * 24 * 3600)  # 7 days ago
            recent_reads = sum(1 for f in all_findings 
                             if f.get('read', False) and 
                             f.get('created_at', 0) > recent_threshold)
            
            recent_bonus = min(recent_reads * 0.2, 0.5)  # Up to 0.5 bonus for recent engagement
            
            # Total findings bonus (more findings = more research value demonstrated)
            volume_bonus = min(total_findings * 0.1, 0.3)  # Up to 0.3 bonus for research volume
            
            total_score = read_percentage + recent_bonus + volume_bonus
            
            logger.debug(f"Research findings engagement for {topic_name}: "
                        f"{read_findings}/{total_findings} read ({read_percentage:.2f}), "
                        f"recent_bonus: {recent_bonus:.2f}, volume_bonus: {volume_bonus:.2f}, "
                        f"total: {total_score:.2f}")
            
            return min(total_score, 2.0)  # Cap at 2.0 to allow for heavy weighting
            
        except Exception as e:
            logger.debug(f"Error calculating research findings engagement for {topic_name}: {str(e)}")
            return 0.0
    
    def _get_analytics_engagement(self, user_id: str, topic_name: str) -> float:
        """
        Get engagement from PersonalizationManager tracking (secondary signal).
        
        This method looks for indirect signals of topic engagement through
        the PersonalizationManager's tracking of user interactions.
        """
        try:
            # Get user profile data which contains engagement analytics
            profile = self.personalization_manager.profile_manager.get_user_profile(user_id)
            if not profile:
                return 0.0
                
            # Extract engagement data from analytics
            analytics = profile.get('analytics', {})
            interaction_signals = analytics.get('interaction_signals', {})
            
            if not interaction_signals:
                return 0.0
            
            # Calculate score from tracked engagement signals
            engagement_score = 0.0
            
            # Source type engagement (if user positively engages with research sources)
            most_engaged_sources = interaction_signals.get('most_engaged_source_types', [])
            if most_engaged_sources:
                # Users with source preferences show research engagement
                engagement_score += min(len(most_engaged_sources) * 0.15, 0.4)
            
            # Follow-up question frequency (shows continued engagement)
            follow_up_freq = interaction_signals.get('follow_up_question_frequency', 0.0)
            engagement_score += follow_up_freq * 0.3
            
            # NOTE: The PersonalizationManager tracks topic expansions, bookmarks, and mark_read 
            # actions via engagement_events, but these are not currently stored in a queryable
            # way by topic. The primary signal remains research findings read status.
            
            # Small baseline for users who have any tracked preferences
            if most_engaged_sources or follow_up_freq > 0:
                engagement_score += 0.2
            
            return min(engagement_score, 1.0)
            
        except Exception as e:
            logger.debug(f"Error getting analytics engagement for {topic_name}: {str(e)}")
            return 0.0

    def _get_topic_success_rate(self, user_id: str, topic_name: str) -> float:
        """Calculate research success rate from user engagement patterns."""
        if not self.personalization_manager:
            return 0.5  # Default neutral success rate
            
        try:
            profile = self.personalization_manager.profile_manager.get_user_profile(user_id)
            if not profile:
                return 0.5
                
            analytics = profile.get('analytics', {})
            
            # High engagement after research indicates successful research
            engagement_score = self._get_topic_engagement_score(user_id, topic_name)
            
            # Use engagement as proxy for success rate
            # Higher engagement = more successful research
            success_rate = 0.3 + (engagement_score * 0.4)  # Range: 0.3-0.7
            
            return success_rate
            
        except Exception as e:
            logger.debug(f"Error getting topic success rate for {topic_name}: {str(e)}")
            return 0.5

    def should_research_topic(self, user_id: str, topic: Dict[str, Any]) -> bool:
        """Check if specific topic should be researched (after global check)."""
        if not self.should_research():  # Global motivation gate
            return False
            
        topic_motivation = self._calculate_topic_motivation(user_id, topic)
        should_research = topic_motivation >= self.drives.topic_threshold
        
        if should_research:
            topic_name = topic.get('topic_name', 'Unknown')
            logger.info(f"Topic research triggered for '{topic_name}' - motivation: {topic_motivation:.2f} >= threshold: {self.drives.topic_threshold:.2f}")
        
        return should_research

    def _calculate_topic_motivation(self, user_id: str, topic: Dict[str, Any]) -> float:
        """Calculate topic-specific motivation score."""
        # Staleness pressure based on time since last research
        last_researched = topic.get('last_researched', 0)
        if last_researched == 0:
            # Never researched - give immediate moderate pressure
            staleness_time = 3600  # Equivalent to 1 hour
        else:
            staleness_time = time.time() - last_researched
            
        staleness_coefficient = topic.get('staleness_coefficient', 1.0)
        staleness_pressure = staleness_time * staleness_coefficient * self.drives.staleness_scale
        
        # Get engagement-based factors
        engagement_score = self._get_topic_engagement_score(user_id, topic.get('topic_name', ''))
        success_rate = self._get_topic_success_rate(user_id, topic.get('topic_name', ''))
        
        # Calculate final motivation score
        topic_motivation = (staleness_pressure + 
                          engagement_score * self.drives.engagement_weight +
                          success_rate * self.drives.quality_weight)
        
        return topic_motivation

    def evaluate_topics(self, user_id: str, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Return engagement-prioritized topics ready for research.
        
        Implements TWO-TIER FILTERING approach:
        1. Tier 1: Global motivation gates whether ANY research occurs
        2. Tier 2: Among topics marked for active research, prioritize by:
           - Research findings interaction (heavily weighted)
           - Staleness pressure (time × LLM-assessed urgency coefficient)
           - Research success rate
        
        Note: Only evaluates topics already marked as 'is_active_research=True' 
        by user, respecting explicit user intent as a strong signal.
        """
        if not self.should_research():  # Global motivation gate
            logger.debug(f"Global motivation check failed - no topics will be researched")
            return []
        
        # Filter: Only evaluate topics user has explicitly activated for research
        active_topics = [t for t in topics if t.get('is_active_research', False)]
        if not active_topics:
            logger.debug(f"No active research topics found for user {user_id}")
            return []
        
        logger.debug(f"Evaluating {len(active_topics)}/{len(topics)} topics marked for active research")
        
        # Score active topics using comprehensive motivation calculation
        scored_topics = []
        for topic in active_topics:
            if self.should_research_topic(user_id, topic):
                score = self._calculate_topic_motivation(user_id, topic)
                scored_topics.append((topic, score))
        
        # Sort by motivation score (highest first)
        sorted_topics = sorted(scored_topics, key=lambda x: x[1], reverse=True)
        
        if sorted_topics:
            topic_names = [topic['topic_name'] for topic, score in sorted_topics[:3]]
            logger.info(f"Motivated topics for user {user_id}: {', '.join(topic_names)}")
        
        return [topic for topic, score in sorted_topics]
