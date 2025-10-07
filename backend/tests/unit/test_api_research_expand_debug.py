import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app
from api.research import router
import config as app_config


@pytest.fixture
def client():
    test_app = app
    test_app.include_router(router, prefix="/api")
    return TestClient(test_app)


def test_expand_debug_zep_disabled_returns_structured(client, monkeypatch):
    monkeypatch.setattr(app_config, "ZEP_ENABLED", False, raising=False)
    body = {"root_topic": {"topic_name": "AI"}}
    resp = client.post("/api/research/debug/expand/u1", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "Zep disabled"


def test_expand_debug_returns_candidates_and_persists_when_requested(client, monkeypatch):
    # Enable Zep flag
    monkeypatch.setattr(app_config, "ZEP_ENABLED", True, raising=False)

    # Patch dependencies in the API module
    with patch("api.research.zep_manager") as zm, patch("api.research.research_manager") as rm, patch(
        "api.research.TopicExpansionService"
    ) as svc_cls:
        zm.is_enabled.return_value = True

        svc = MagicMock()
        svc.generate_candidates = AsyncMock(
            return_value=[
                # Mimic dataclass-like objects with attributes
                type("C", (), {"name": "Topic A", "source": "zep_node", "similarity": 0.9, "rationale": "related KG node"})(),
                type("C", (), {"name": "Topic B", "source": "zep_edge", "similarity": 0.7, "rationale": "related KG fact"})(),
            ]
        )
        svc_cls.return_value = svc

        # Mock persistence
        rm.add_custom_topic.side_effect = [
            {"success": True, "topic": {"topic_id": "t1", "topic_name": "Topic A"}},
            {"success": False, "error": "A topic named 'Topic B' already exists", "topic": None},
        ]

        body = {
            "root_topic": {"topic_name": "Root", "description": "desc"},
            "create_topics": True,
            "enable_research": True,
            "limit": 2,
        }
        resp = client.post("/api/research/debug/expand/u1", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["root_topic"] == "Root"
        assert len(data["candidates"]) == 2
        assert {c["name"] for c in data["candidates"]} == {"Topic A", "Topic B"}
        # Ensure annotation fields present
        for c in data["candidates"]:
            assert "source" in c and "rationale" in c
        # Created one, skipped one duplicate
        assert data["created_topics"] == [{"topic_id": "t1", "name": "Topic A"}]
        assert data["skipped_duplicates"] == ["Topic B"]
        assert data["limit"] == 2
        assert "metrics" in data


def test_expand_debug_invalid_root_topic_returns_error(client, monkeypatch):
    monkeypatch.setattr(app_config, "ZEP_ENABLED", True, raising=False)
    with patch("api.research.zep_manager") as zm, patch("api.research.research_manager") as rm:
        zm.is_enabled.return_value = True
        body = {"root_topic": {"topic_name": "   "}}
        resp = client.post("/api/research/debug/expand/u1", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Invalid root_topic.topic_name" in data["error"]
