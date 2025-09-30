"""
Unit tests for per-user autonomous research features.

Tests cover:
- ProfileManager autonomy flag storage
- Per-user scheduler lifecycle
- API endpoints for autonomy control
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import tempfile
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.storage_manager import StorageManager
from storage.profile_manager import ProfileManager
from services.per_user_scheduler import PerUserScheduler


class TestProfileManagerAutonomy:
    """Test autonomy flag storage in ProfileManager."""

    def test_create_user_defaults_autonomy_false(self):
        """New users should have autonomous_enabled=False by default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            user_id = pm.create_user({"test": "metadata"})
            assert user_id
            
            profile = pm.get_user(user_id)
            assert profile.get("autonomous_enabled") is False

    def test_is_autonomous_enabled_default_false(self):
        """is_autonomous_enabled should return False for new users."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            user_id = pm.create_user()
            assert pm.is_autonomous_enabled(user_id) is False

    def test_is_autonomous_enabled_nonexistent_user(self):
        """is_autonomous_enabled should return False for nonexistent users."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            assert pm.is_autonomous_enabled("nonexistent-user") is False

    def test_set_autonomous_enabled_true(self):
        """set_autonomous_enabled should enable autonomy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            user_id = pm.create_user()
            success = pm.set_autonomous_enabled(user_id, True)
            
            assert success is True
            assert pm.is_autonomous_enabled(user_id) is True
            
            profile = pm.get_user(user_id)
            assert profile.get("autonomous_enabled") is True

    def test_set_autonomous_enabled_false(self):
        """set_autonomous_enabled should disable autonomy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            user_id = pm.create_user()
            pm.set_autonomous_enabled(user_id, True)
            success = pm.set_autonomous_enabled(user_id, False)
            
            assert success is True
            assert pm.is_autonomous_enabled(user_id) is False

    def test_set_autonomous_enabled_idempotent(self):
        """Setting the same value multiple times should work."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            user_id = pm.create_user()
            
            pm.set_autonomous_enabled(user_id, True)
            pm.set_autonomous_enabled(user_id, True)
            assert pm.is_autonomous_enabled(user_id) is True
            
            pm.set_autonomous_enabled(user_id, False)
            pm.set_autonomous_enabled(user_id, False)
            assert pm.is_autonomous_enabled(user_id) is False


class TestPerUserScheduler:
    """Test per-user scheduler functionality."""

    @pytest.fixture
    def mock_profile_manager(self):
        """Create a mock ProfileManager."""
        pm = Mock()
        pm.is_autonomous_enabled = Mock(return_value=False)
        return pm

    @pytest.fixture
    def mock_researcher(self):
        """Create a mock AutonomousResearcher."""
        researcher = Mock()
        researcher.trigger_research_for_user = AsyncMock(return_value={
            "success": True,
            "topics_researched": 2,
            "findings_stored": 1
        })
        return researcher

    @pytest.fixture
    def scheduler(self, mock_profile_manager, mock_researcher):
        """Create a PerUserScheduler instance."""
        return PerUserScheduler(mock_profile_manager, mock_researcher)

    def test_scheduler_initialization(self, scheduler, mock_profile_manager, mock_researcher):
        """Scheduler should initialize with correct dependencies."""
        assert scheduler.profile_manager is mock_profile_manager
        assert scheduler.autonomous_researcher is mock_researcher
        assert scheduler._tasks == {}
        assert scheduler._next_run_at == {}

    def test_is_running_no_task(self, scheduler):
        """is_running should return False when no task exists."""
        assert scheduler.is_running("test-user") is False

    def test_next_run_at_no_task(self, scheduler):
        """next_run_at should return None when no task exists."""
        assert scheduler.next_run_at("test-user") is None

    def test_start_for_user_when_disabled(self, scheduler, mock_profile_manager):
        """start_for_user should return False when autonomy is disabled."""
        mock_profile_manager.is_autonomous_enabled.return_value = False
        
        result = scheduler.start_for_user("test-user")
        
        assert result is False
        assert scheduler.is_running("test-user") is False

    @pytest.mark.asyncio
    async def test_start_for_user_when_enabled(self, scheduler, mock_profile_manager):
        """start_for_user should create a task when autonomy is enabled."""
        mock_profile_manager.is_autonomous_enabled.return_value = True
        
        result = scheduler.start_for_user("test-user")
        
        assert result is True
        assert scheduler.is_running("test-user") is True
        
        # Give the async loop time to set next_run_at
        await asyncio.sleep(0.01)
        assert scheduler.next_run_at("test-user") is not None
        
        # Clean up
        await scheduler.stop_for_user("test-user")

    @pytest.mark.asyncio
    async def test_start_for_user_idempotent(self, scheduler, mock_profile_manager):
        """start_for_user should be idempotent (safe to call multiple times)."""
        mock_profile_manager.is_autonomous_enabled.return_value = True
        
        result1 = scheduler.start_for_user("test-user")
        result2 = scheduler.start_for_user("test-user")
        
        assert result1 is True
        assert result2 is True
        assert scheduler.is_running("test-user") is True
        
        # Clean up
        await scheduler.stop_for_user("test-user")

    @pytest.mark.asyncio
    async def test_stop_for_user(self, scheduler, mock_profile_manager):
        """stop_for_user should cancel the task."""
        mock_profile_manager.is_autonomous_enabled.return_value = True
        
        scheduler.start_for_user("test-user")
        assert scheduler.is_running("test-user") is True
        
        await scheduler.stop_for_user("test-user")
        
        assert scheduler.is_running("test-user") is False
        assert scheduler.next_run_at("test-user") is None

    @pytest.mark.asyncio
    async def test_stop_for_user_when_not_running(self, scheduler):
        """stop_for_user should be safe to call when no task exists."""
        await scheduler.stop_for_user("test-user")
        assert scheduler.is_running("test-user") is False

    @pytest.mark.asyncio
    async def test_stop_all(self, scheduler, mock_profile_manager):
        """stop_all should stop all running schedulers."""
        mock_profile_manager.is_autonomous_enabled.return_value = True
        
        scheduler.start_for_user("user-1")
        scheduler.start_for_user("user-2")
        
        assert scheduler.is_running("user-1") is True
        assert scheduler.is_running("user-2") is True
        
        await scheduler.stop_all()
        
        assert scheduler.is_running("user-1") is False
        assert scheduler.is_running("user-2") is False

    @pytest.mark.asyncio
    async def test_scheduler_calls_researcher(self, mock_profile_manager, mock_researcher):
        """Scheduler should call researcher after interval."""
        # Patch the _loop to use a shorter wait time for testing
        async def fast_loop(user_id: str):
            try:
                while mock_profile_manager.is_autonomous_enabled(user_id):
                    scheduler._next_run_at[user_id] = time.time() + 0.05
                    await asyncio.sleep(0.05)
                    
                    if not mock_profile_manager.is_autonomous_enabled(user_id):
                        break
                    
                    try:
                        if scheduler.autonomous_researcher is not None:
                            await scheduler.autonomous_researcher.trigger_research_for_user(user_id)
                    except Exception:
                        pass
            finally:
                scheduler._next_run_at.pop(user_id, None)
                scheduler._tasks.pop(user_id, None)
        
        scheduler = PerUserScheduler(mock_profile_manager, mock_researcher)
        scheduler._loop = fast_loop
        
        # Enable autonomy
        mock_profile_manager.is_autonomous_enabled.return_value = True
        scheduler.start_for_user("test-user")
        
        # Wait for scheduler to run
        await asyncio.sleep(0.1)
        
        # After sleep, turn off autonomy to stop loop
        mock_profile_manager.is_autonomous_enabled.return_value = False
        await asyncio.sleep(0.05)
        
        # Verify researcher was called at least once
        assert mock_researcher.trigger_research_for_user.call_count >= 1
        mock_researcher.trigger_research_for_user.assert_called_with("test-user")
        
        # Clean up
        await scheduler.stop_for_user("test-user")

    @pytest.mark.asyncio
    async def test_scheduler_handles_researcher_errors(self, mock_profile_manager):
        """Scheduler should continue running even if researcher throws errors."""
        failing_researcher = Mock()
        failing_researcher.trigger_research_for_user = AsyncMock(
            side_effect=Exception("Research failed")
        )
        
        scheduler = PerUserScheduler(mock_profile_manager, failing_researcher)
        scheduler._interval_seconds = 0.1
        
        mock_profile_manager.is_autonomous_enabled.return_value = True
        scheduler.start_for_user("test-user")
        
        # Wait for scheduler to attempt run
        await asyncio.sleep(0.25)
        
        # Stop the scheduler
        mock_profile_manager.is_autonomous_enabled.return_value = False
        await asyncio.sleep(0.05)
        
        # Task should still be managed (not crashed)
        await scheduler.stop_for_user("test-user")

    @pytest.mark.asyncio
    async def test_scheduler_stops_when_autonomy_disabled(self, mock_profile_manager, mock_researcher):
        """Scheduler should stop automatically when autonomy is disabled."""
        # Patch the _loop to use a shorter wait time for testing
        async def fast_loop(user_id: str):
            try:
                while mock_profile_manager.is_autonomous_enabled(user_id):
                    scheduler._next_run_at[user_id] = time.time() + 0.05
                    await asyncio.sleep(0.05)
                    
                    if not mock_profile_manager.is_autonomous_enabled(user_id):
                        break
                    
                    try:
                        if scheduler.autonomous_researcher is not None:
                            await scheduler.autonomous_researcher.trigger_research_for_user(user_id)
                    except Exception:
                        pass
            finally:
                scheduler._next_run_at.pop(user_id, None)
                scheduler._tasks.pop(user_id, None)
        
        scheduler = PerUserScheduler(mock_profile_manager, mock_researcher)
        scheduler._loop = fast_loop
        
        # Start with autonomy enabled
        mock_profile_manager.is_autonomous_enabled.return_value = True
        scheduler.start_for_user("test-user")
        
        assert scheduler.is_running("test-user") is True
        
        # Wait for first cycle to start
        await asyncio.sleep(0.02)
        
        # Disable autonomy (simulating user turning it off)
        mock_profile_manager.is_autonomous_enabled.return_value = False
        
        # Wait for loop to check and exit
        await asyncio.sleep(0.1)
        
        # Task should have cleaned itself up
        assert scheduler.is_running("test-user") is False


class TestPerUserSchedulerJitter:
    """Test scheduler jitter and timing."""

    @pytest.mark.asyncio
    async def test_next_run_at_has_jitter(self):
        """next_run_at should include jitter to avoid synchronized runs."""
        pm = Mock()
        pm.is_autonomous_enabled = Mock(return_value=True)
        researcher = Mock()
        
        scheduler = PerUserScheduler(pm, researcher)
        scheduler._interval_seconds = 100
        
        # Start multiple users
        scheduler.start_for_user("user-1")
        scheduler.start_for_user("user-2")
        scheduler.start_for_user("user-3")
        
        # Give async loops time to set next_run_at
        await asyncio.sleep(0.01)
        
        # Get next run times
        next_1 = scheduler.next_run_at("user-1")
        next_2 = scheduler.next_run_at("user-2")
        next_3 = scheduler.next_run_at("user-3")
        
        # All should be set
        assert next_1 is not None
        assert next_2 is not None
        assert next_3 is not None
        
        # Times should be different due to jitter (very high probability)
        assert next_1 != next_2 or next_2 != next_3
        
        # All should be in the future
        now = time.time()
        assert next_1 > now
        assert next_2 > now
        assert next_3 > now
        
        # Clean up
        await scheduler.stop_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

