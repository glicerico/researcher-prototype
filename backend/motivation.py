"""Simple motivation system for the autonomous researcher."""

from __future__ import annotations

import time
from dataclasses import dataclass

import config


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

    def tick(self) -> None:
        """Update drive levels based on time since last tick."""
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now

        self.boredom = min(1.0, self.boredom + dt * self.drives.boredom_rate)
        self.curiosity = max(0.0, self.curiosity - dt * self.drives.curiosity_decay)
        self.tiredness = max(0.0, self.tiredness - dt * self.drives.tiredness_decay)
        self.satisfaction = max(0.0, self.satisfaction - dt * self.drives.satisfaction_decay)

    def on_user_activity(self) -> None:
        """Increase curiosity and reduce boredom when user interacts."""
        self.curiosity = min(1.0, self.curiosity + 0.3)
        self.boredom = max(0.0, self.boredom - 0.1)

    def on_research_completed(self, quality_score: float = 0.5) -> None:
        """Update drives after research completes."""
        self.tiredness = min(1.0, self.tiredness + 0.3)
        self.satisfaction = min(1.0, self.satisfaction + quality_score)
        self.curiosity = max(0.0, self.curiosity - 0.2)
        self.boredom = max(0.0, self.boredom - 0.4)

    def impetus(self) -> float:
        """Compute the overall desire to research."""
        return self.boredom + self.curiosity + 0.5 * self.satisfaction - self.tiredness

    def should_research(self) -> bool:
        """Return True if motivation threshold reached."""
        return self.impetus() >= self.drives.threshold
