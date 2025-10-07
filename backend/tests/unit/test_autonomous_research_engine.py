import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch, call

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.autonomous_research_engine import AutonomousResearcher, initialize_autonomous_researcher, get_autonomous_researcher
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager


@pytest.fixture
def mock_profile_manager():
    """Create a mock ProfileManager for testing."""
    manager = MagicMock(spec=ProfileManager)
    manager.list_users.return_value = ["user1", "user2"]
    manager.storage = MagicMock()  # Add mock storage for PersonalizationManager initialization
    return manager


@pytest.fixture
def mock_research_manager():
    """Create a mock ResearchManager for testing."""
    manager = MagicMock(spec=ResearchManager)
    manager.get_active_research_topics.return_value = []
    manager.cleanup_old_research_findings.return_value = True
    return manager


@pytest.fixture
def mock_research_graph():
    """Create a mock research graph for testing."""
    graph = AsyncMock()
    graph.ainvoke.return_value = {
        "module_results": {
            "research_storage": {
                "success": True,
                "stored": True,
                "quality_score": 0.8,
                "finding_id": "test_finding_123",
                "insights_count": 3
            }
        }
    }
    return graph


@pytest.fixture
def autonomous_researcher(mock_profile_manager, mock_research_manager):
    """Create an AutonomousResearcher with mocked dependencies."""
    with patch('services.autonomous_research_engine.research_graph') as mock_graph, \
         patch('services.autonomous_research_engine.TopicExpansionService') as mock_expansion:
        
        mock_graph.ainvoke = AsyncMock(return_value={
            "module_results": {
                "research_storage": {
                    "success": True,
                    "stored": True,
                    "quality_score": 0.8,
                    "finding_id": "test_finding_123",
                    "insights_count": 3
                }
            }
        })
        
        # Mock topic expansion service to return no candidates
        mock_expansion_instance = AsyncMock()
        mock_expansion_instance.generate_candidates.return_value = []
        mock_expansion.return_value = mock_expansion_instance
        
        researcher = AutonomousResearcher(mock_profile_manager, mock_research_manager)
        researcher.research_graph = mock_graph
        researcher.topic_expansion_service = mock_expansion_instance
        return researcher


@pytest.fixture
def sample_topics():
    """Sample topic data for testing."""
    return [
        {
            "topic_name": "AI Research",
            "description": "Latest developments in artificial intelligence",
            "is_active_research": True,
            "research_count": 5,
            "last_researched": time.time() - 7200  # 2 hours ago
        },
        {
            "topic_name": "Climate Change",
            "description": "Environmental impact and solutions",
            "is_active_research": True,
            "research_count": 3,
            "last_researched": None  # Never researched
        }
    ]


@pytest.fixture
def motivation_config_override():
    """Sample motivation configuration override."""
    return {
        "boredom_rate": 0.8,
        "curiosity_decay": 0.6,
        "tiredness_decay": 0.3
    }


class TestAutonomousResearcherInitialization:
    """Test AutonomousResearcher initialization and configuration."""

    def test_init_default_config(self, mock_profile_manager, mock_research_manager):
        """Test initialization with default configuration."""
        with patch('services.autonomous_research_engine.research_graph') as mock_graph:
            researcher = AutonomousResearcher(mock_profile_manager, mock_research_manager)
            
            assert researcher.profile_manager == mock_profile_manager
            assert researcher.research_manager == mock_research_manager
            assert researcher.research_graph == mock_graph
            assert researcher.is_running is False
            assert researcher.research_task is None
            assert researcher.motivation is not None
            assert researcher.enabled is False  # From config - default is disabled

    def test_init_with_motivation_override(self, mock_profile_manager, mock_research_manager, motivation_config_override):
        """Test initialization with motivation configuration override."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = AutonomousResearcher(
                mock_profile_manager, 
                mock_research_manager, 
                motivation_config_override
            )
            
            assert researcher.motivation is not None
            # Verify motivation system was created with overrides
            assert researcher.motivation.drives.boredom_rate == 0.8
            assert researcher.motivation.drives.curiosity_decay == 0.6
            assert researcher.motivation.drives.tiredness_decay == 0.3

    def test_enable_disable_functionality(self, autonomous_researcher):
        """Test enable/disable functionality."""
        # Test enable
        autonomous_researcher.enable()
        assert autonomous_researcher.is_enabled() is True
        
        # Test disable
        autonomous_researcher.disable()
        assert autonomous_researcher.is_enabled() is False
        
        # Test toggle
        result = autonomous_researcher.toggle_enabled()
        assert result is True
        assert autonomous_researcher.is_enabled() is True
        
        result = autonomous_researcher.toggle_enabled()
        assert result is False
        assert autonomous_researcher.is_enabled() is False

    def test_get_status(self, autonomous_researcher):
        """Test status reporting."""
        status = autonomous_researcher.get_status()
        
        expected_keys = [
            "enabled", "running", "quality_threshold",
            "max_topics_per_user", "retention_days", "engine_type", "research_graph_nodes"
        ]
        
        for key in expected_keys:
            assert key in status
        
        assert status["engine_type"] == "LangGraph-based"
        assert isinstance(status["research_graph_nodes"], list)
        assert len(status["research_graph_nodes"]) > 0


class TestResearchCycleLogic:
    """Test research cycle and topic research logic."""


    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_success(self, autonomous_researcher, sample_topics):
        """Test successful topic research with LangGraph."""
        topic = sample_topics[0]
        
        result = await autonomous_researcher._research_topic_with_langgraph("user1", topic)
        
        assert result is not None
        assert result["success"] is True
        assert result["stored"] is True
        assert result["quality_score"] == 0.8
        assert result["finding_id"] == "test_finding_123"
        assert result["insights_count"] == 3

    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_not_stored(self, autonomous_researcher, sample_topics):
        """Test topic research where finding is not stored."""
        # Mock research graph to return not stored result
        autonomous_researcher.research_graph.ainvoke.return_value = {
            "module_results": {
                "research_storage": {
                    "success": True,
                    "stored": False,
                    "quality_score": 0.3,
                    "reason": "Quality too low"
                }
            }
        }
        
        topic = sample_topics[0]
        result = await autonomous_researcher._research_topic_with_langgraph("user1", topic)
        
        assert result is not None
        assert result["success"] is True
        assert result["stored"] is False
        assert result["reason"] == "Quality too low"
        assert result["quality_score"] == 0.3

    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_failure(self, autonomous_researcher, sample_topics):
        """Test topic research failure handling."""
        # Mock research graph to return failure
        autonomous_researcher.research_graph.ainvoke.return_value = {
            "module_results": {
                "research_storage": {
                    "success": False,
                    "stored": False,
                    "error": "Network error"
                }
            }
        }
        
        topic = sample_topics[0]
        result = await autonomous_researcher._research_topic_with_langgraph("user1", topic)
        
        assert result is not None
        assert result["success"] is False
        assert result["stored"] is False
        assert result["error"] == "Network error"

    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_exception(self, autonomous_researcher, sample_topics):
        """Test topic research with exception handling."""
        # Mock research graph to raise exception
        autonomous_researcher.research_graph.ainvoke.side_effect = Exception("Graph execution failed")
        
        topic = sample_topics[0]
        result = await autonomous_researcher._research_topic_with_langgraph("user1", topic)
        
        assert result is not None
        assert result["success"] is False
        assert result["stored"] is False
        assert "Graph execution failed" in result["error"]


class TestAutonomousResearchLoop:
    """Test the autonomous research loop and lifecycle."""

    @pytest.mark.asyncio
    async def test_start_when_disabled(self, autonomous_researcher):
        """Test starting when research engine is disabled."""
        autonomous_researcher.disable()
        
        await autonomous_researcher.start()
        
        assert autonomous_researcher.is_running is False
        assert autonomous_researcher.research_task is None

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, autonomous_researcher):
        """Test starting when already running."""
        autonomous_researcher.is_running = True
        
        await autonomous_researcher.start()
        
        # Should still be running, no new task created
        assert autonomous_researcher.is_running is True

    @pytest.mark.asyncio
    async def test_start_and_stop_lifecycle(self, autonomous_researcher):
        """Test complete start/stop lifecycle."""
        # Enable the researcher first
        autonomous_researcher.enable()
        
        # Mock motivation to prevent actual research
        autonomous_researcher.motivation.should_research = MagicMock(return_value=False)
        autonomous_researcher.check_interval = 0.1  # Fast for testing
        
        # Start the engine
        await autonomous_researcher.start()
        
        assert autonomous_researcher.is_running is True
        assert autonomous_researcher.research_task is not None
        
        # Let it run briefly
        await asyncio.sleep(0.15)
        
        # Stop the engine
        await autonomous_researcher.stop()
        
        assert autonomous_researcher.is_running is False

    @pytest.mark.asyncio
    async def test_research_loop_motivation_trigger(self, autonomous_researcher, sample_topics):
        """Test research loop triggering research when motivated."""
        # Enable the researcher first
        autonomous_researcher.enable()
        
        # Setup mocks
        autonomous_researcher.motivation.should_research = MagicMock(return_value=True)
        autonomous_researcher.motivation.on_research_completed = MagicMock()
        autonomous_researcher.research_manager.get_active_research_topics.return_value = sample_topics
        autonomous_researcher.check_interval = 0.1
        
        # Mock the research cycle to return quickly
        autonomous_researcher._conduct_research_cycle = AsyncMock(return_value={"topics_researched": 1, "average_quality": 0.7})
        
        # Start and let it run one cycle
        await autonomous_researcher.start()
        await asyncio.sleep(0.15)  # Let motivation trigger
        await autonomous_researcher.stop()
        
        # Verify research was triggered
        autonomous_researcher._conduct_research_cycle.assert_called_once()
        autonomous_researcher.motivation.on_research_completed.assert_called_once_with(0.7)

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, autonomous_researcher):
        """Test stopping when not running."""
        assert autonomous_researcher.is_running is False
        
        # Should complete without error
        await autonomous_researcher.stop()
        
        assert autonomous_researcher.is_running is False


class TestManualResearchTrigger:
    """Test manual research triggering functionality."""

    @pytest.mark.asyncio
    async def test_trigger_research_no_active_topics(self, autonomous_researcher):
        """Test manual research trigger with no active topics."""
        autonomous_researcher.research_manager.get_active_research_topics.return_value = []
        
        result = await autonomous_researcher.trigger_research_for_user("user1")
        
        assert result["success"] is True
        assert result["message"] == "No active research topics found"
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0

    @pytest.mark.asyncio
    async def test_trigger_research_success(self, autonomous_researcher, sample_topics):
        """Test successful manual research trigger."""
        autonomous_researcher.research_manager.get_active_research_topics.return_value = sample_topics
        
        result = await autonomous_researcher.trigger_research_for_user("user1")
        
        assert result["success"] is True
        assert result["topics_researched"] == 2
        assert result["findings_stored"] == 2  # Both topics should store findings
        assert result["total_active_topics"] == 2
        assert len(result["research_details"]) == 2
        
        # Check research details
        detail = result["research_details"][0]
        assert detail["topic_name"] == "AI Research"
        assert detail["success"] is True
        assert detail["stored"] is True
        assert detail["quality_score"] == 0.8

    @pytest.mark.asyncio
    async def test_trigger_research_with_failures(self, autonomous_researcher, sample_topics):
        """Test manual research trigger with some failures."""
        autonomous_researcher.research_manager.get_active_research_topics.return_value = sample_topics
        
        # Mock one success, one failure
        call_count = 0
        async def mock_research_topic(user_id, topic):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"success": True, "stored": True, "quality_score": 0.8}
            else:
                return {"success": False, "stored": False, "error": "API error"}
        
        autonomous_researcher._research_topic_with_langgraph = mock_research_topic
        
        result = await autonomous_researcher.trigger_research_for_user("user1")
        
        assert result["success"] is True
        assert result["topics_researched"] == 2
        assert result["findings_stored"] == 1  # Only one succeeded
        assert len(result["research_details"]) == 2
        
        # Check mixed results
        success_detail = next(d for d in result["research_details"] if d["success"])
        failure_detail = next(d for d in result["research_details"] if not d["success"])
        
        assert success_detail["stored"] is True
        assert failure_detail["error"] == "API error"

    @pytest.mark.asyncio
    async def test_trigger_research_exception_handling(self, autonomous_researcher):
        """Test manual research trigger exception handling."""
        autonomous_researcher.research_manager.get_active_research_topics.side_effect = Exception("Database error")
        
        result = await autonomous_researcher.trigger_research_for_user("user1")
        
        assert result["success"] is False
        assert "Database error" in result["error"]
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0


class TestResearchCycleIntegration:
    """Test the complete research cycle integration."""

    @pytest.mark.asyncio
    async def test_conduct_research_cycle_no_users(self, autonomous_researcher):
        """Test research cycle with no users."""
        autonomous_researcher.profile_manager.list_users.return_value = []
        
        result = await autonomous_researcher._conduct_research_cycle()
        
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0
        assert result["average_quality"] == 0.0

    @pytest.mark.asyncio
    async def test_conduct_research_cycle_no_active_topics(self, autonomous_researcher):
        """Test research cycle with users but no active topics."""
        autonomous_researcher.profile_manager.list_users.return_value = ["user1", "user2"]
        autonomous_researcher.research_manager.get_active_research_topics.return_value = []
        
        result = await autonomous_researcher._conduct_research_cycle()
        
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0
        assert result["average_quality"] == 0.0

    @pytest.mark.asyncio
    async def test_conduct_research_cycle_success(self, autonomous_researcher, sample_topics):
        """Test successful research cycle."""
        autonomous_researcher.profile_manager.list_users.return_value = ["user1"]
        autonomous_researcher.research_manager.get_active_research_topics.return_value = sample_topics
        
        # Mock motivation system to return all topics as motivated
        with patch.object(autonomous_researcher.motivation, 'evaluate_topics', return_value=sample_topics):
            result = await autonomous_researcher._conduct_research_cycle()
        
        assert result["topics_researched"] == 2
        assert result["findings_stored"] == 2
        assert result["average_quality"] == 0.8
        
        # Verify cleanup was called
        autonomous_researcher.research_manager.cleanup_old_research_findings.assert_called()



class TestGlobalFunctions:
    """Test global initialization and accessor functions."""

    def test_initialize_autonomous_researcher(self, mock_profile_manager, mock_research_manager):
        """Test global initialization function."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = initialize_autonomous_researcher(mock_profile_manager, mock_research_manager)
            
            assert isinstance(researcher, AutonomousResearcher)
            assert researcher.profile_manager == mock_profile_manager
            assert researcher.research_manager == mock_research_manager

    def test_get_autonomous_researcher(self, mock_profile_manager, mock_research_manager):
        """Test global accessor function."""
        with patch('services.autonomous_research_engine.research_graph'):
            # Initialize first
            researcher = initialize_autonomous_researcher(mock_profile_manager, mock_research_manager)
            
            # Get should return the same instance
            retrieved = get_autonomous_researcher()
            assert retrieved is researcher

    def test_initialize_with_motivation_override(self, mock_profile_manager, mock_research_manager, motivation_config_override):
        """Test initialization with motivation configuration override."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = initialize_autonomous_researcher(
                mock_profile_manager, 
                mock_research_manager, 
                motivation_config_override
            )
            
            assert researcher.motivation.drives.boredom_rate == 0.8
            assert researcher.motivation.drives.curiosity_decay == 0.6


class TestErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_research_loop_exception_handling(self, autonomous_researcher):
        """Test research loop handles exceptions gracefully."""
        # Mock motivation to throw exception
        autonomous_researcher.motivation.tick = MagicMock(side_effect=Exception("Motivation error"))
        autonomous_researcher.check_interval = 0.1
        
        # Start and let it run briefly - should not crash
        await autonomous_researcher.start()
        await asyncio.sleep(0.15)
        await autonomous_researcher.stop()
        
        # Should have stopped gracefully
        assert autonomous_researcher.is_running is False

    @pytest.mark.asyncio
    async def test_research_cycle_user_exception_handling(self, autonomous_researcher, sample_topics):
        """Test research cycle handles per-user exceptions."""
        autonomous_researcher.profile_manager.list_users.return_value = ["user1", "user2"]
        
        # Mock to throw exception for user1, succeed for user2
        def mock_get_active_topics(user_id):
            if user_id == "user1":
                raise Exception("User error")
            return sample_topics
        
        autonomous_researcher.research_manager.get_active_research_topics.side_effect = mock_get_active_topics
        
        # Mock motivation system to return topics as motivated for user2
        with patch.object(autonomous_researcher.motivation, 'evaluate_topics', return_value=sample_topics):
            result = await autonomous_researcher._conduct_research_cycle()
        
        # Should complete with results from user2 only
        assert result["topics_researched"] == 2  # Only user2's topics
        assert result["findings_stored"] == 2