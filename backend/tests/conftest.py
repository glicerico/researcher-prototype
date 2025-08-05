import os
import sys
import pytest
import asyncio
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, AIMessage
from unittest.mock import Mock, AsyncMock

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_MODEL
from app import app
from graph_builder import create_chat_graph


@pytest.fixture
def client():
    """Fixture for creating a FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def chat_graph():
    """Fixture for creating a chat graph for testing"""
    return create_chat_graph()


@pytest.fixture
def test_message():
    """Fixture for a standard test message"""
    return {"role": "user", "content": "Hello, how are you?"}


@pytest.fixture
def test_chat_state():
    """Fixture for a standard chat state for testing"""
    return {
        "messages": [
            HumanMessage(content="Hello, how are you?")
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000
    }


@pytest.fixture
def sample_chat_state():
    """Sample chat state for testing."""
    return {
        "messages": [],
        "user_id": "test_user",
        "thread_id": "test_thread",
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "max_tokens": 1000,
        "current_module": None,
        "module_results": {},
        "workflow_context": {},
    } 