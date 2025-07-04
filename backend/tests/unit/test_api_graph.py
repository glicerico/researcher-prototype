import pytest
from fastapi.testclient import TestClient

from fastapi import FastAPI
from api.graph import router
from dependencies import get_existing_user_id, zep_manager

app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    def get_test_user_id():
        return "test_user"

    app.dependency_overrides[get_existing_user_id] = get_test_user_id
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_graph(monkeypatch):
    async def fake_graph(user_id: str, limit: int = 100):
        return {"nodes": [{"uuid": "n1", "name": "User"}], "edges": []}

    monkeypatch.setattr(zep_manager, "get_knowledge_graph", fake_graph)


def test_get_knowledge_graph(client):
    res = client.get("/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data and "edges" in data
