import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_get_user_graph():
    response = client.get("/zep/graph")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "nodes" in data
    assert "edges" in data
