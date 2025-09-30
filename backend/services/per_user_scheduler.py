import asyncio
import time
import random
from typing import Dict, Optional

from services.logging_config import get_logger
import config


logger = get_logger(__name__)


class PerUserScheduler:
    """
    Simple per-user scheduler that periodically triggers background research for a user.
    """

    def __init__(self, profile_manager, autonomous_researcher):
        self.profile_manager = profile_manager
        self.autonomous_researcher = autonomous_researcher
        self._tasks: Dict[str, asyncio.Task] = {}
        self._next_run_at: Dict[str, float] = {}
        self._interval_seconds = int(getattr(config, "AUTONOMY_INTERVAL_SECONDS", 1800))

    def is_running(self, user_id: str) -> bool:
        task = self._tasks.get(user_id)
        return bool(task and not task.done())

    def next_run_at(self, user_id: str) -> Optional[float]:
        return self._next_run_at.get(user_id)

    async def _loop(self, user_id: str):
        try:
            while self.profile_manager.is_autonomous_enabled(user_id):
                jitter = random.uniform(0.0, 0.15 * self._interval_seconds)
                wait_s = max(5.0, self._interval_seconds + jitter)
                self._next_run_at[user_id] = time.time() + wait_s
                await asyncio.sleep(wait_s)

                if not self.profile_manager.is_autonomous_enabled(user_id):
                    break

                try:
                    if self.autonomous_researcher is not None:
                        await self.autonomous_researcher.trigger_research_for_user(user_id)
                except Exception as e:
                    logger.error(f"Per-user research error for {user_id}: {str(e)}", exc_info=True)
                    await asyncio.sleep(1.0)
        finally:
            self._next_run_at.pop(user_id, None)
            self._tasks.pop(user_id, None)

    def start_for_user(self, user_id: str) -> bool:
        if not self.profile_manager.is_autonomous_enabled(user_id):
            return False
        if self.is_running(user_id):
            return True
        self._tasks[user_id] = asyncio.create_task(self._loop(user_id))
        logger.info(f"Started per-user scheduler for {user_id}")
        return True

    async def stop_for_user(self, user_id: str) -> None:
        task = self._tasks.get(user_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.pop(user_id, None)
        self._next_run_at.pop(user_id, None)
        logger.info(f"Stopped per-user scheduler for {user_id}")

    async def stop_all(self) -> None:
        users = list(self._tasks.keys())
        for uid in users:
            await self.stop_for_user(uid)


