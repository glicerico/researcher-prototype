import pytest
from unittest.mock import patch, MagicMock
import json
import os
import sys
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import Message, ChatRequest, ChatResponse
from graph_builder import create_chat_graph
from nodes.base import ChatState


def test_root_endpoint(client):
    """Test that the root endpoint returns the expected message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Chatbot API is running"}
    
def test_models_endpoint(client):
    """Test that the models endpoint returns the supported models."""
    response = client.get("/models")
    assert response.status_code == 200
    assert "models" in response.json()
    models = response.json()["models"]
    assert "gpt-4o-mini" in models
    
@patch('nodes.integrator_node.ChatOpenAI')
@patch('nodes.response_renderer_node.ChatOpenAI')
def test_chat_endpoint(mock_renderer_openai, mock_integrator_openai, client, test_chat_state):
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
    
    # Send the request to the chat endpoint
    response = client.post(
        "/chat",
        json=test_chat_state
    )
    
    # Check the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["response"] == "This is a test response"
    assert response_data["model"] == "gpt-4o-mini"
    
def test_invalid_request(client):
    """Test that an invalid request returns an error."""
    # Missing required field (messages)
    request_data = {
        "model": "gpt-4o-mini",
        "temperature": 0.7
    }
    
    response = client.post(
        "/chat",
        json=request_data
    )
    
    assert response.status_code == 422  # Validation error


@patch('nodes.integrator_node.ChatOpenAI')
@patch('nodes.response_renderer_node.ChatOpenAI')
def test_chat_graph(mock_renderer_openai, mock_integrator_openai, chat_graph, test_chat_state):
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
    
    # Run the graph
    result = chat_graph.invoke(test_chat_state)
    
    # Check the result
    assert "messages" in result
    assert len(result["messages"]) == 2  # Original message + response
    assert result["messages"][1]["role"] == "assistant"
    assert result["messages"][1]["content"] == "This is a test response"


if __name__ == "__main__":
    pytest.main() 