import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage  # noqa: E402
from fastapi.testclient import TestClient
from app import app
from config import DEFAULT_MODEL, get_available_models

client = TestClient(app)


def test_root_endpoint(client):
    """Test that the root endpoint returns the expected message."""
    response = client.get("/health")  # Updated to use the actual health endpoint
    assert response.status_code == 200
    assert "status" in response.json()


def test_models_endpoint():
    """Test the /models endpoint returns available models."""
    response = client.get("/models")
    assert response.status_code == 200
    
    data = response.json()
    assert "models" in data
    assert "default_model" in data
    
    # Check that models from config are present
    available_models = get_available_models()
    models = data["models"]
    
    for model_id in available_models:
        assert model_id in models
    
    # Check default model is valid
    assert data["default_model"] in models


@patch("nodes.multi_source_analyzer_node.ChatOpenAI")
@patch("nodes.integrator_node.ChatOpenAI")
@patch("nodes.response_renderer_node.ChatOpenAI")
def test_chat_endpoint(mock_renderer_openai, mock_integrator_openai, mock_analyzer_openai, client, test_chat_state):
    """Test the chat endpoint with a mocked LLM response."""
    # Mock the integrator LLM response
    mock_integrator_instance = MagicMock()
    mock_integrator_instance.invoke.return_value.content = "This is a test response"
    mock_integrator_openai.return_value = mock_integrator_instance

    # Mock the renderer LLM response
    mock_renderer_instance = MagicMock()
    mock_renderer_instance.with_structured_output.return_value = mock_renderer_instance
    mock_renderer_instance.invoke.return_value.main_response = "This is a test response"
    mock_renderer_instance.invoke.return_value.follow_up_questions = None
    mock_renderer_openai.return_value = mock_renderer_instance

    # Mock the analyzer LLM to avoid API key requirement  
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.with_structured_output.return_value.invoke.return_value.intent = "chat"
    mock_analyzer_instance.with_structured_output.return_value.invoke.return_value.reason = "test"
    mock_analyzer_instance.with_structured_output.return_value.invoke.return_value.sources = []
    mock_analyzer_openai.return_value = mock_analyzer_instance

    # Convert the test state to the format expected by the API
    api_request = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    # Send the request to the chat endpoint
    response = client.post("/chat", json=api_request)

    # Check the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["response"] == "This is a test response"
    assert response_data["model"] == DEFAULT_MODEL


def test_invalid_request(client):
    """Test that an invalid request returns an error."""
    # Missing required field (messages)
    request_data = {"model": DEFAULT_MODEL, "temperature": 0.7}

    response = client.post("/chat", json=request_data)

    assert response.status_code == 422  # Validation error


@patch("nodes.multi_source_analyzer_node.ChatOpenAI")
@patch("nodes.integrator_node.ChatOpenAI")
@patch("nodes.response_renderer_node.ChatOpenAI")
@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_chat_graph(
    mock_renderer_openai, mock_integrator_openai, mock_analyzer_openai, chat_graph, test_chat_state
):
    """Test the chat node in the graph."""
    # Mock the integrator LLM response
    mock_integrator_instance = MagicMock()
    mock_integrator_instance.invoke.return_value.content = "This is a test response"
    mock_integrator_openai.return_value = mock_integrator_instance

    # Mock the renderer LLM response
    mock_renderer_instance = MagicMock()
    mock_renderer_instance.with_structured_output.return_value = mock_renderer_instance
    mock_renderer_instance.invoke.return_value.main_response = "This is a test response"
    mock_renderer_instance.invoke.return_value.follow_up_questions = None
    mock_renderer_openai.return_value = mock_renderer_instance

    # Mock analyzer LLM
    mock_analyzer_instance = MagicMock() 
    mock_analyzer_instance.with_structured_output.return_value.invoke.return_value.intent = "chat"
    mock_analyzer_instance.with_structured_output.return_value.invoke.return_value.reason = "test"
    mock_analyzer_instance.with_structured_output.return_value.invoke.return_value.sources = []
    mock_analyzer_openai.return_value = mock_analyzer_instance

    # Run the graph using async invoke
    result = await chat_graph.ainvoke(test_chat_state)

    # Check the result
    assert "messages" in result
    assert len(result["messages"]) == 2  # Original message + response
    assert isinstance(result["messages"][1], AIMessage)
    assert result["messages"][1].content == "This is a test response"


if __name__ == "__main__":
    pytest.main()
