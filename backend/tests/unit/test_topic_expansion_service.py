import pytest
from unittest.mock import AsyncMock, MagicMock

import config as app_config
from services.topic_expansion_service import TopicExpansionService


@pytest.mark.asyncio
async def test_generate_candidates_filters_sorts_and_dedup(monkeypatch):
    # Arrange config thresholds
    monkeypatch.setattr(app_config, "ZEP_SEARCH_LIMIT", 10, raising=False)
    monkeypatch.setattr(app_config, "ZEP_SEARCH_RERANKER", "cross_encoder", raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_MIN_SIMILARITY", 0.5, raising=False)

    # Mock ZepManager
    zep = MagicMock()
    # Nodes and edges with varying similarity and duplicates
    zep.search_graph = AsyncMock(side_effect=[
        # nodes
        [
            {"name": "Quantum Computing", "labels": ["Tech"], "similarity": 0.9},
            {"labels": ["AI"], "similarity": 0.7},  # uses first label
            {"name": "Duplicate Topic", "similarity": 0.6},
            {"name": "Low Similarity", "similarity": 0.3},  # should be filtered out
        ],
        # edges
        [
            {"fact": "Quantum supremacy achieved", "similarity": 0.85},
            {"name": "AI ethics", "similarity": 0.65},
            {"fact": "Duplicate Topic", "similarity": 0.75},  # duplicate by name
        ],
    ])

    # Mock ResearchManager with existing topics including a duplicate
    research = MagicMock()
    research.get_user_topics.return_value = {
        "sessions": {
            "s1": [
                {"topic_name": "duplicate topic"},  # case-insensitive duplicate
                {"topic_name": "Existing Topic"},
            ]
        }
    }

    svc = TopicExpansionService(zep, research)

    root = {"topic_name": "Quantum", "description": "state of the art"}
    out = await svc.generate_candidates("user1", root)

    # Filtered out "Low Similarity" (< 0.5)
    names = [c.name for c in out]
    assert "Low Similarity" not in names

    # Dedup removed Duplicate Topic (existing) and kept unique
    assert "Duplicate Topic" not in names

    # Sorting: by similarity desc; nodes preferred over edges for ties
    # Expect first item to be the top similarity (Quantum Computing 0.9)
    assert out[0].name == "Quantum Computing"
    assert out[0].source == "zep_node"

    # Items without similarity go last (none in our set after filtering)
    assert all(c.similarity is None or c.similarity >= 0.5 for c in out)

