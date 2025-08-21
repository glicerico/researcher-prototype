import pytest
from unittest.mock import patch, MagicMock, Mock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nodes.multi_source_analyzer_node import multi_source_analyzer_node
from nodes.integrator_node import integrator_node  
from nodes.response_renderer_node import response_renderer_node
from llm_models import MultiSourceAnalysis, FormattedResponse
from config import DEFAULT_MODEL


@pytest.fixture
def sample_chat_state():
    """Create a sample chat state for testing."""
    return {
        "messages": [HumanMessage(content="Hello, how are you?")],
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "max_tokens": 1000,
        "personality": {"style": "helpful", "tone": "friendly"},
        "current_module": None,
        "module_results": {},
        "workflow_context": {},
        "user_id": "test_user",
        "routing_analysis": None,
        "thread_id": "test_thread",
        "memory_context": None,
    }


@pytest.fixture
def sample_chat_state_with_memory():
    """Create a sample chat state with memory context for testing."""
    return {
        "messages": [HumanMessage(content="Tell me more about that")],
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "max_tokens": 1000,
        "personality": {"style": "helpful", "tone": "friendly"},
        "current_module": None,
        "module_results": {},
        "workflow_context": {},
        "user_id": "test_user",
        "routing_analysis": None,
        "thread_id": "test_thread",
        "memory_context": "Previous conversation about machine learning"
    }


class TestMultiSourceAnalyzerNode:
    """Test multi_source_analyzer_node function."""

    @patch('nodes.multi_source_analyzer_node.ChatOpenAI')
    async def test_multi_source_analyzer_chat_intent(self, mock_openai, sample_chat_state):
        """Test chat intent routing."""
        # Mock the structured output
        mock_llm = Mock()
        mock_structured_analyzer = Mock()
        mock_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured_analyzer
        
        mock_analysis_result = MultiSourceAnalysis(
            intent="chat",
            reason="General conversation",
            sources=[]
        )
        mock_structured_analyzer.invoke.return_value = mock_analysis_result
        
        result = await multi_source_analyzer_node(sample_chat_state)
        
        assert result["intent"] == "chat"
        assert result["selected_sources"] == []
        assert result["routing_analysis"]["intent"] == "chat"
        assert result["routing_analysis"]["reason"] == "General conversation"

    @patch('nodes.multi_source_analyzer_node.ChatOpenAI')
    async def test_multi_source_analyzer_search_intent(self, mock_openai, sample_chat_state):
        """Test search intent routing with sources."""
        mock_llm = Mock()
        mock_structured_analyzer = Mock()
        mock_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured_analyzer
        
        mock_analysis_result = MultiSourceAnalysis(
            intent="search",
            reason="User needs current information",
            sources=["search", "academic_search"]
        )
        mock_structured_analyzer.invoke.return_value = mock_analysis_result
        
        result = await multi_source_analyzer_node(sample_chat_state)
        
        assert result["intent"] == "search"
        assert result["selected_sources"] == ["search", "academic_search"]
        assert result["routing_analysis"]["intent"] == "search"

    @patch('nodes.multi_source_analyzer_node.ChatOpenAI')
    async def test_multi_source_analyzer_analysis_intent(self, mock_openai, sample_chat_state):
        """Test analysis intent routing."""
        mock_llm = Mock()
        mock_structured_analyzer = Mock()
        mock_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured_analyzer
        
        mock_analysis_result = MultiSourceAnalysis(
            intent="analysis",
            reason="Complex analytical task",
            sources=[]
        )
        mock_structured_analyzer.invoke.return_value = mock_analysis_result
        
        result = await multi_source_analyzer_node(sample_chat_state)
        
        assert result["intent"] == "analysis"
        assert result["selected_sources"] == []
        assert result["routing_analysis"]["intent"] == "analysis"

    @patch('nodes.multi_source_analyzer_node.ChatOpenAI')
    async def test_multi_source_analyzer_invalid_intent_fallback(self, mock_openai, sample_chat_state):
        """Test fallback to chat for invalid intents."""
        mock_llm = Mock()
        mock_structured_analyzer = Mock()
        mock_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured_analyzer
        
        mock_analysis_result = MultiSourceAnalysis(
            intent="invalid_intent",
            reason="This should fallback to chat",
            sources=[]
        )
        mock_structured_analyzer.invoke.return_value = mock_analysis_result
        
        result = await multi_source_analyzer_node(sample_chat_state)
        
        assert result["intent"] == "chat"

    @patch('nodes.multi_source_analyzer_node.ChatOpenAI')
    async def test_multi_source_analyzer_exception_handling(self, mock_openai, sample_chat_state):
        """Test exception handling in analyzer."""
        mock_llm = Mock()
        mock_openai.return_value = mock_llm
        mock_llm.with_structured_output.side_effect = Exception("API Error")
        
        result = await multi_source_analyzer_node(sample_chat_state)
        
        assert result["intent"] == "chat"
        assert "Error:" in result["routing_analysis"]["reason"]

    async def test_multi_source_analyzer_no_user_message(self, sample_chat_state):
        """Test analyzer behavior with no user message."""
        sample_chat_state["messages"] = []
        
        result = await multi_source_analyzer_node(sample_chat_state)
        
        assert result["intent"] == "chat"
        assert result["routing_analysis"]["reason"] == "No user message found"


class TestIntegratorNode:
    """Test integrator_node function."""

    @patch('nodes.integrator_node.ChatOpenAI')
    async def test_integrator_node_basic_integration(self, mock_openai, sample_chat_state):
        """Test basic integration functionality."""
        # Mock the LLM response
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "This is a test response from integrator"
        mock_openai.return_value = mock_llm

        # Set up state with some context
        sample_chat_state["workflow_context"] = {"test_context": "test_value"}

        result = await integrator_node(sample_chat_state)

        # Check that integrator response is stored
        assert "integrator_response" in result["workflow_context"]
        assert result["workflow_context"]["integrator_response"] == "This is a test response from integrator"

    @patch('nodes.integrator_node.ChatOpenAI')
    async def test_integrator_node_with_search_results(self, mock_openai, sample_chat_state):
        """Test integrator with search results."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Integrated response with search data"
        mock_openai.return_value = mock_llm

        # Add search results to state
        sample_chat_state["module_results"] = {
            "search": {
                "success": True,
                "result": "Search result content",
                "citations": ["http://example.com"],
                "search_sources": [{"title": "Test Source", "url": "http://example.com"}]
            }
        }

        result = await integrator_node(sample_chat_state)

        assert "integrator_response" in result["workflow_context"]
        assert result["workflow_context"]["integrator_response"] == "Integrated response with search data"


class TestResponseRendererNode:
    """Test response_renderer_node function."""

    @patch('nodes.response_renderer_node.ChatOpenAI')
    async def test_response_renderer_basic_formatting(self, mock_openai, sample_chat_state):
        """Test basic response rendering functionality."""
        # Set up integrator response
        sample_chat_state["workflow_context"] = {
            "integrator_response": "This is a test response that needs formatting",
            "citations": [],
            "search_sources": []
        }

        # Mock the structured output
        mock_llm = MagicMock()
        mock_structured_renderer = MagicMock()
        mock_formatted_response = FormattedResponse(
            main_response="This is a formatted test response",
            follow_up_questions=["Would you like to know more?"],
            sources=[]
        )
        mock_structured_renderer.invoke.return_value = mock_formatted_response
        mock_llm.with_structured_output.return_value = mock_structured_renderer
        mock_openai.return_value = mock_llm

        result = await response_renderer_node(sample_chat_state)

        # Check that a message was added
        assert len(result["messages"]) > 0
        assert result["messages"][-1].content == "This is a formatted test response"

    async def test_response_renderer_no_integrator_response(self, sample_chat_state):
        """Test response renderer behavior with no integrator response."""
        # No integrator response in workflow context
        sample_chat_state["workflow_context"] = {}

        result = await response_renderer_node(sample_chat_state)

        # Should add an error message
        assert len(result["messages"]) > 0
        assert "error" in result["messages"][-1].content.lower()