import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import config as app_config
from services.topic_expansion_service import TopicExpansionService


def _mk_zep_node(name, sim):
    return {"name": name, "labels": [], "similarity": sim}


def _mk_zep_edge(name, sim):
    return {"fact": name, "similarity": sim}


@pytest.mark.asyncio
async def test_generate_candidates_llm_valid_json(monkeypatch):
    monkeypatch.setattr(app_config, "EXPANSION_LLM_ENABLED", True, raising=False)

    zep = MagicMock()
    zep.search_graph = AsyncMock(side_effect=[
        # initial nodes
        [_mk_zep_node("A", 0.9), _mk_zep_node("B", 0.7)],
        # initial edges
        [_mk_zep_edge("B fact", 0.65)],
    ])

    research = MagicMock()
    research.get_user_topics.return_value = {"sessions": {"s1": [{"topic_name": "Existing"}]}}

    svc = TopicExpansionService(zep, research)

    # Mock ChatOpenAI structured output
    with patch("services.topic_expansion_service.ChatOpenAI") as chat:
        mock_structured = MagicMock()
        chat.return_value.with_structured_output.return_value = mock_structured
        # Accepted: one zep_node (A), one llm proposal (C); one rejected
        class Accepted:
            def __init__(self, name, source, rationale, sim=None, conf=0.8):
                self.name = name
                self.source = source
                self.rationale = rationale
                self.similarity_if_available = sim
                self.confidence = conf

        class Rejected:
            def __init__(self, name, reason):
                self.name = name
                self.reason = reason

        selection = type("Sel", (), {
            "topics": [Accepted("A", "zep_node", "good node", 0.9), Accepted("C", "llm", "novel")],
            "accepted": [Accepted("A", "zep_node", "good node", 0.9), Accepted("C", "llm", "novel")],
            "rejected": [Rejected("D", "too generic")]
        })
        mock_structured.ainvoke = AsyncMock(return_value=selection)

        # LLM-only C validation via Zep (nodes preferred)
        async def validate_query(user_id, q, scope, reranker, limit):
            if q == "C":
                return [_mk_zep_node("C", 0.8)]
            return []
        # Append to side effects for validate_llm_item
        zep.search_graph = AsyncMock(side_effect=[
            # initial nodes
            [_mk_zep_node("A", 0.9), _mk_zep_node("B", 0.7)],
            # initial edges
            [_mk_zep_edge("B fact", 0.65)],
            # validation for C
            awaitable := None
        ])
        zep.search_graph.side_effect = [
            [_mk_zep_node("A", 0.9), _mk_zep_node("B", 0.7)],
            [_mk_zep_edge("B fact", 0.65)],
            [_mk_zep_node("C", 0.8)],
        ]

        out = await svc.generate_candidates("u1", {"topic_name": "Root"})

        names = [c.name for c in out]
        assert names == ["C", "A"]  # Sorted by confidence (desc), then by name
        # C is llm, A has zep source
        assert out[0].source == "llm"
        assert out[1].source in ("zep_node", "zep_edge")
        # Both should have confidence 0.8
        assert out[0].confidence == 0.8
        assert out[1].confidence == 0.8


@pytest.mark.asyncio
async def test_generate_candidates_llm_invalid_json_fallback(monkeypatch):
    monkeypatch.setattr(app_config, "EXPANSION_LLM_ENABLED", True, raising=False)
    zep = MagicMock()
    zep.search_graph = AsyncMock(return_value=[_mk_zep_node("A", 0.9)])
    research = MagicMock()
    research.get_user_topics.return_value = {"sessions": {"s1": []}}
    svc = TopicExpansionService(zep, research)

    with patch("services.topic_expansion_service.ChatOpenAI") as chat:
        chat.return_value.with_structured_output.return_value.ainvoke = AsyncMock(side_effect=Exception("bad json"))
        out = await svc.generate_candidates("u1", {"topic_name": "Root"})
        # Falls back to Zep-only
        assert any(c.source.startswith("zep_") for c in out)


@pytest.mark.asyncio
async def test_generate_candidates_llm_only_validated_by_zep(monkeypatch):
    monkeypatch.setattr(app_config, "EXPANSION_LLM_ENABLED", True, raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_MIN_SIMILARITY", 0.5, raising=False)
    zep = MagicMock()
    # initial searches
    zep.search_graph = AsyncMock(side_effect=[[], [], [_mk_zep_node("LLM1", 0.6)], []])
    research = MagicMock()
    research.get_user_topics.return_value = {"sessions": {"s1": []}}
    svc = TopicExpansionService(zep, research)

    with patch("services.topic_expansion_service.ChatOpenAI") as chat:
        mock_structured = MagicMock()
        chat.return_value.with_structured_output.return_value = mock_structured
        class Accepted:
            def __init__(self, name, source, rationale, sim=None, conf=0.8):
                self.name = name
                self.source = source
                self.rationale = rationale
                self.similarity_if_available = sim
                self.confidence = conf
        selection = type("Sel", (), {
            "topics": [Accepted("LLM1", "llm", "novel", sim=0.6)],
            "accepted": [Accepted("LLM1", "llm", "novel", sim=0.6)],
            "rejected": []
        })
        mock_structured.ainvoke = AsyncMock(return_value=selection)

        out = await svc.generate_candidates("u1", {"topic_name": "Root"})
        # LLM-only suggestion validated by Zep and kept (0.6 >= 0.5)
        assert [c.name for c in out] == ["LLM1"]
        assert out[0].similarity == 0.6


@pytest.mark.asyncio
async def test_generate_candidates_llm_timeout_fallback(monkeypatch):
    monkeypatch.setattr(app_config, "EXPANSION_LLM_ENABLED", True, raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_LLM_TIMEOUT_SECONDS", 1, raising=False)
    zep = MagicMock()
    zep.search_graph = AsyncMock(return_value=[_mk_zep_node("A", 0.9)])
    research = MagicMock()
    research.get_user_topics.return_value = {"sessions": {"s1": []}}
    svc = TopicExpansionService(zep, research)

    with patch("services.topic_expansion_service.ChatOpenAI") as chat:
        # Simulate hang by blocking invoke; our wait_for should timeout
        def blocking_invoke(_):
            import time as _t
            _t.sleep(2)
        chat.return_value.with_structured_output.return_value.ainvoke = AsyncMock(side_effect=blocking_invoke)
        out = await svc.generate_candidates("u1", {"topic_name": "Root"})
        assert any(c.source.startswith("zep_") for c in out)


@pytest.mark.asyncio
async def test_generate_candidates_llm_flag_disabled(monkeypatch):
    # Note: EXPANSION_LLM_ENABLED was removed - LLM is always used for topic expansion
    # This test now verifies that LLM is always called even when Zep returns results
    zep = MagicMock()
    zep.search_graph = AsyncMock(return_value=[_mk_zep_node("A", 0.9)])
    research = MagicMock()
    research.get_user_topics.return_value = {"sessions": {"s1": []}}
    svc = TopicExpansionService(zep, research)

    # Mock the LLM to return a result
    with patch("services.topic_expansion_service.ChatOpenAI") as chat:
        mock_structured = MagicMock()
        chat.return_value.with_structured_output.return_value = mock_structured
        
        class Accepted:
            def __init__(self, name, source, rationale, sim=None, conf=0.8):
                self.name = name
                self.source = source
                self.rationale = rationale
                self.similarity_if_available = sim
                self.confidence = conf
        
        selection = type("Sel", (), {
            "topics": [Accepted("LLM_Topic", "llm", "novel")],
        })
        mock_structured.ainvoke = AsyncMock(return_value=selection)
        
        out = await svc.generate_candidates("u1", {"topic_name": "Root"})
        # Should return LLM result, not just Zep result
        assert any(c.source == "llm" for c in out)


@pytest.mark.asyncio
async def test_dedupe_against_existing_topics(monkeypatch):
    monkeypatch.setattr(app_config, "EXPANSION_LLM_ENABLED", True, raising=False)
    zep = MagicMock()
    zep.search_graph = AsyncMock(return_value=[_mk_zep_node("Duplicate", 0.9)])
    research = MagicMock()
    research.get_user_topics.return_value = {"sessions": {"s1": [{"topic_name": "duplicate"}]}}
    svc = TopicExpansionService(zep, research)

    with patch("services.topic_expansion_service.ChatOpenAI") as chat:
        mock_structured = MagicMock()
        chat.return_value.with_structured_output.return_value = mock_structured
        class Accepted:
            def __init__(self, name, source, rationale, sim=None, conf=0.8):
                self.name = name
                self.source = source
                self.rationale = rationale
                self.similarity_if_available = sim
                self.confidence = conf
        selection = type("Sel", (), {
            "accepted": [Accepted("Duplicate", "zep_node", "dup", 0.9)],
            "rejected": []
        })
        mock_structured.ainvoke = AsyncMock(return_value=selection)

        out = await svc.generate_candidates("u1", {"topic_name": "Root"})
        # Should dedupe against existing topics, resulting in empty list
        assert out == []
