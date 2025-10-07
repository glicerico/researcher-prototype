import asyncio
from types import SimpleNamespace

import pytest

from storage.zep_manager import ZepManager


class FakeGraph:
    def __init__(self, results):
        self._results = results

    async def search(self, **kwargs):  # query, user_id, scope, reranker, limit
        return self._results


class FakeClient:
    def __init__(self, results):
        self.graph = FakeGraph(results)


@pytest.mark.asyncio
async def test_search_graph_disabled_returns_empty(monkeypatch):
    z = ZepManager()
    z.enabled = False
    z.client = None
    out = await z.search_graph("u1", "q", scope="nodes")
    assert out == []


@pytest.mark.asyncio
async def test_search_graph_normalizes_nodes_and_edges(monkeypatch):
    # Prepare mixed results: node as object, edge as object
    node_obj = SimpleNamespace(name="Tesla", labels=["Company", "EV"], uuid_="n-1", score=0.9)
    edge_obj = SimpleNamespace(
        fact="Elon Musk founded Tesla",
        name="founded",
        source_node_uuid="s-1",
        target_node_uuid="t-1",
        uuid_="e-1",
        score=0.8
    )

    z = ZepManager()
    z.enabled = True
    z.client = FakeClient([('nodes', [node_obj]), ('edges', [edge_obj])])

    nodes = await z.search_graph("u1", "tesla", scope="nodes", limit=5)
    assert len(nodes) == 1
    assert nodes[0]["name"] == "Tesla"
    assert nodes[0]["labels"] == ["Company", "EV"]
    assert nodes[0]["uuid"] == "n-1"
    assert nodes[0]["similarity"] == pytest.approx(0.9)

    edges = await z.search_graph("u1", "tesla", scope="edges", limit=5)
    assert len(edges) == 1
    assert edges[0]["fact"] == "Elon Musk founded Tesla"
    assert edges[0]["name"] == "Elon Musk founded Tesla"
    assert edges[0]["source_node_uuid"] == "s-1"
    assert edges[0]["target_node_uuid"] == "t-1"
    assert edges[0]["uuid"] == "e-1"
    assert edges[0]["similarity"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_search_graph_invalid_scope_returns_empty():
    z = ZepManager()
    z.enabled = True
    z.client = FakeClient([])
    out = await z.search_graph("u1", "q", scope="invalid")
    assert out == []


@pytest.mark.asyncio
async def test_search_graph_timeout_returns_empty(monkeypatch):
    class TimeoutGraph:
        async def search(self, **kwargs):
            raise asyncio.TimeoutError()

    class TimeoutClient:
        def __init__(self):
            self.graph = TimeoutGraph()

    monkeypatch.setattr("config.ZEP_SEARCH_TIMEOUT_SECONDS", 1, raising=False)
    monkeypatch.setattr("config.ZEP_SEARCH_RETRIES", 0, raising=False)
    z = ZepManager()
    z.enabled = True
    z.client = TimeoutClient()
    out = await z.search_graph("u1", "q", scope="nodes")
    assert out == []
