import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import config as app_config
from services.autonomous_research_engine import AutonomousResearcher
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager


def _mk_topic(name, is_exp=True, depth=1, status='active', enabled=False, last_eval=0, backoff_until=0):
    return {
        "topic_id": f"id-{name}",
        "topic_name": name,
        "description": "desc",
        "is_active_research": True,
        "is_expansion": is_exp,
        "expansion_depth": depth,
        "child_expansion_enabled": enabled,
        "expansion_status": status,
        "last_evaluated_at": last_eval,
        "last_backoff_until": backoff_until,
    }


@pytest.fixture
def pm_rm():
    pm = MagicMock(spec=ProfileManager)
    pm.storage = MagicMock()
    rm = MagicMock(spec=ResearchManager)
    return pm, rm


@pytest.mark.asyncio
async def test_lifecycle_promote_children(monkeypatch, pm_rm):
    pm, rm = pm_rm
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        # Topics
        topics = {"sessions": {"s1": [_mk_topic("T1", enabled=False)]}}
        rm.get_user_topics.return_value = topics
        rm.get_research_findings_for_api.return_value = [
            {"topic_name": "T1", "research_time": time.time(), "quality_score": 0.8, "read": True}
        ]
        # High engagement
        ar.motivation._get_topic_engagement_score = MagicMock(return_value=0.5)

        await ar._update_expansion_lifecycle("u1")

        updated = rm.save_user_topics.call_args[0][1]
        t = updated["sessions"]["s1"][0]
        assert t["child_expansion_enabled"] is True
        assert t["expansion_status"] == "active"


@pytest.mark.asyncio
async def test_lifecycle_pause_on_cold_engagement(monkeypatch, pm_rm):
    pm, rm = pm_rm
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        topics = {"sessions": {"s1": [_mk_topic("Cold", enabled=False, status='active')]}}
        rm.get_user_topics.return_value = topics
        # No interactions in window
        rm.get_research_findings_for_api.return_value = [
            {"topic_name": "Cold", "research_time": time.time() - (15 * 24 * 3600), "quality_score": 0.5, "read": False}
        ]
        ar.motivation._get_topic_engagement_score = MagicMock(return_value=0.0)

        await ar._update_expansion_lifecycle("u1")
        updated = rm.save_user_topics.call_args[0][1]
        t = updated["sessions"]["s1"][0]
        assert t["is_active_research"] is False
        assert t["expansion_status"] == "paused"
        assert t["last_backoff_until"] > time.time()


@pytest.mark.asyncio
async def test_lifecycle_retire_after_ttl(monkeypatch, pm_rm):
    pm, rm = pm_rm
    monkeypatch.setattr(app_config, "EXPANSION_RETIRE_TTL_DAYS", 1, raising=False)
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        old = time.time() - (2 * 24 * 3600)
        topics = {"sessions": {"s1": [_mk_topic("OldPaused", status='paused', last_eval=old)]}}
        rm.get_user_topics.return_value = topics
        rm.get_research_findings_for_api.return_value = []
        ar.motivation._get_topic_engagement_score = MagicMock(return_value=0.0)

        await ar._update_expansion_lifecycle("u1")
        updated = rm.save_user_topics.call_args[0][1]
        t = updated["sessions"]["s1"][0]
        assert t["expansion_status"] == "retired"


@pytest.mark.asyncio
async def test_depth_and_backoff_gate(monkeypatch, pm_rm):
    pm, rm = pm_rm
    monkeypatch.setattr(app_config, "EXPANSION_MAX_DEPTH", 1, raising=False)
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        # Topic with depth at max and disabled children
        topic = _mk_topic("Parent", depth=1, enabled=False)
        rm.get_active_research_topics.return_value = [topic]
        ar.motivation.evaluate_topics = MagicMock(return_value=[topic])
        ar._research_topic_with_langgraph = AsyncMock(return_value={"success": True, "stored": True, "quality_score": 0.7})
        # Ensure expansion service would return, but gating prevents
        ar.topic_expansion_service.generate_candidates = AsyncMock(return_value=[MagicMock(name="Candidate")])
        # Run single-cycle path directly
        res = await ar._conduct_research_cycle()
        # Only root researched; no add_custom_topic calls
        assert rm.add_custom_topic.call_count == 0


@pytest.mark.asyncio
async def test_gating_only_affects_expansions(monkeypatch, pm_rm):
    pm, rm = pm_rm
    with patch("services.autonomous_research_engine.research_graph"):
        ar = AutonomousResearcher(pm, rm)
        root = {"topic_name": "Root", "is_expansion": False}
        rm.get_active_research_topics.return_value = [root]
        ar.motivation.evaluate_topics = MagicMock(return_value=[root])
        ar._research_topic_with_langgraph = AsyncMock(return_value={"success": True, "stored": True, "quality_score": 0.7})
        ar.topic_expansion_service.generate_candidates = AsyncMock(return_value=[])
        # Should still research root without gating interference
        res = await ar._conduct_research_cycle()
        assert res["topics_researched"] >= 1
