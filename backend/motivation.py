"""Simple motivation system for the autonomous researcher."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import config

logger = logging.getLogger(__name__)


@dataclass
class DriveConfig:
    boredom_rate: float = config.MOTIVATION_BOREDOM_RATE
    curiosity_decay: float = config.MOTIVATION_CURIOSITY_DECAY
    tiredness_decay: float = config.MOTIVATION_TIREDNESS_DECAY
    satisfaction_decay: float = config.MOTIVATION_SATISFACTION_DECAY
    threshold: float = config.MOTIVATION_THRESHOLD


class MotivationSystem:
    """Track motivation drives and decide when research should occur."""

    def __init__(self, drives: DriveConfig | None = None) -> None:
        self.drives = drives or DriveConfig()
        self.boredom = 0.0
        self.curiosity = 0.0
        self.tiredness = 0.0
        self.satisfaction = 0.0
        self.last_tick = time.time()
        logger.info(f"Motivation system initialized with threshold: {self.drives.threshold}")

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
