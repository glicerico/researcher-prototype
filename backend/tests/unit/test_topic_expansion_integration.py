import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import config as app_config
from services.autonomous_research_engine import AutonomousResearcher
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager


@pytest.fixture
def mock_pm_rm():
    pm = MagicMock(spec=ProfileManager)
    pm.list_users.return_value = ["user1"]
    pm.storage = MagicMock()
    rm = MagicMock(spec=ResearchManager)
    rm.get_active_research_topics.return_value = [
        {"topic_name": "Root Topic", "description": "desc", "is_active_research": True}
    ]
    rm.cleanup_old_research_findings.return_value = True
    return pm, rm


def _make_candidate(name, sim, source="zep_node"):
    return SimpleNamespace(name=name, similarity=sim, source=source, rationale="r", description=None, confidence=0.8)


@pytest.mark.asyncio
async def test_expansion_budget_enforced(monkeypatch, mock_pm_rm):
    pm, rm = mock_pm_rm
    # Configure expansion limits
    monkeypatch.setattr(app_config, "EXPLORATION_PER_ROOT_MAX", 1, raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_MAX_PARALLEL", 2, raising=False)

    with patch("services.autonomous_research_engine.research_graph") as mock_graph:
        ar = AutonomousResearcher(pm, rm)
        # Always motivated
        ar.motivation.evaluate_topics = MagicMock(return_value=rm.get_active_research_topics.return_value)
        ar.motivation.should_research = MagicMock(return_value=True)
        ar.check_interval = 0  # single pass

        # Mock research results
        ar._research_topic_with_langgraph = AsyncMock(return_value={"success": True, "stored": True, "quality_score": 0.9})

        # Mock expansion service
        ar.topic_expansion_service = MagicMock()
        ar.topic_expansion_service.generate_candidates = AsyncMock(
            return_value=[
                _make_candidate("A", 0.9),
                _make_candidate("B", 0.5),
                _make_candidate("C", None),
            ]
        )

        # Mock check_active_topics_limit to allow topic activation
        rm.check_active_topics_limit.return_value = {"allowed": True}
        
        # Persist only first (budget=1)
        rm.add_custom_topic.return_value = {"success": True, "topic": {"topic_name": "A", "description": "Auto", "is_active_research": True}}

        result = await ar._conduct_research_cycle()

        # Root + 1 expansion
        assert result["topics_researched"] == 2
        assert result["findings_stored"] == 2
        # Only one expansion persisted due to budget
        rm.add_custom_topic.assert_called_once()
        args, kwargs = rm.add_custom_topic.call_args
        assert kwargs["topic_name"] == "A"


@pytest.mark.asyncio
async def test_expansion_no_candidates(monkeypatch, mock_pm_rm):
    pm, rm = mock_pm_rm
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        ar.motivation.evaluate_topics = MagicMock(return_value=rm.get_active_research_topics.return_value)
        ar.motivation.should_research = MagicMock(return_value=True)
        ar.check_interval = 0
        ar._research_topic_with_langgraph = AsyncMock(return_value={"success": True, "stored": True, "quality_score": 0.8})
        ar.topic_expansion_service = MagicMock()
        ar.topic_expansion_service.generate_candidates = AsyncMock(return_value=[])

        result = await ar._conduct_research_cycle()
        assert result["topics_researched"] == 1  # root only
        rm.add_custom_topic.assert_not_called()


@pytest.mark.asyncio
async def test_expansion_concurrency_guard(monkeypatch, mock_pm_rm):
    pm, rm = mock_pm_rm
    monkeypatch.setattr(app_config, "EXPLORATION_PER_ROOT_MAX", 2, raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_MAX_PARALLEL", 1, raising=False)
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        ar.motivation.evaluate_topics = MagicMock(return_value=rm.get_active_research_topics.return_value)
        ar.motivation.should_research = MagicMock(return_value=True)
        ar.check_interval = 0

        # Simulate longer research tasks to exercise semaphore (lightweight)
        async def slow_research(user_id, topic):
            await asyncio.sleep(0.01)
            return {"success": True, "stored": True, "quality_score": 0.7}

        ar._research_topic_with_langgraph = AsyncMock(side_effect=slow_research)
        ar.topic_expansion_service = MagicMock()
        ar.topic_expansion_service.generate_candidates = AsyncMock(
            return_value=[_make_candidate("A", 0.9), _make_candidate("B", 0.8)]
        )
        
        # Mock check_active_topics_limit to allow topic activation
        rm.check_active_topics_limit.return_value = {"allowed": True}
        
        rm.add_custom_topic.side_effect = [
            {"success": True, "topic": {"topic_name": "A", "description": "Auto", "is_active_research": True}},
            {"success": True, "topic": {"topic_name": "B", "description": "Auto", "is_active_research": True}},
        ]

        result = await ar._conduct_research_cycle()
        # Root + 2 expansions
        assert result["topics_researched"] == 3
        assert rm.add_custom_topic.call_count == 2
