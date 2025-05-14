import unittest
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


class TestChatbotApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    def test_root_endpoint(self):
        """Test that the root endpoint returns the expected message."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Chatbot API is running"})
        
    def test_models_endpoint(self):
        """Test that the models endpoint returns the supported models."""
        response = self.client.get("/models")
        self.assertEqual(response.status_code, 200)
        self.assertIn("models", response.json())
        models = response.json()["models"]
        self.assertIn("gpt-4o-mini", models)
        
    @patch('nodes.integrator_node.ChatOpenAI')
    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_chat_endpoint(self, mock_renderer_openai, mock_integrator_openai):
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
        
        # Create a test request
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Send the request to the chat endpoint
        response = self.client.post(
            "/chat",
            json=request_data
        )
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["response"], "This is a test response")
        self.assertEqual(response_data["model"], "gpt-4o-mini")
        
    def test_invalid_request(self):
        """Test that an invalid request returns an error."""
        # Missing required field (messages)
        request_data = {
            "model": "gpt-4o-mini",
            "temperature": 0.7
        }
        
        response = self.client.post(
            "/chat",
            json=request_data
        )
        
        self.assertEqual(response.status_code, 422)  # Validation error


class TestChatGraph(unittest.TestCase):
    @patch('nodes.integrator_node.ChatOpenAI')
    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_chat_node(self, mock_renderer_openai, mock_integrator_openai):
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
        
        # Create a test state
        state = {
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Create the graph
        graph = create_chat_graph()
        
        # Run the graph
        result = graph.invoke(state)
        
        # Check the result
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 2)  # Original message + response
        self.assertEqual(result["messages"][1]["role"], "assistant")
        self.assertEqual(result["messages"][1]["content"], "This is a test response")


if __name__ == "__main__":
    unittest.main() 