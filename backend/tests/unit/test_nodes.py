import pytest
from unittest.mock import patch, MagicMock, Mock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nodes.router_node import router_node
from nodes.integrator_node import integrator_node  
from nodes.response_renderer_node import response_renderer_node
from llm_models import RoutingAnalysis, FormattedResponse


@pytest.fixture
def sample_chat_state():
    """Create a sample chat state for testing."""
    return {
        "messages": [HumanMessage(content="Hello, how are you?")],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000,
        "personality": None,
        "current_module": None,
        "module_results": {},
        "workflow_context": {},
        "user_id": "test_user",
        "routing_analysis": None,
        "session_id": "test_session",
        "memory_context": None
    }


@pytest.fixture
def sample_chat_state_with_memory():
    """Create a sample chat state with memory context."""
    return {
        "messages": [HumanMessage(content="Tell me about AI")],
        "model": "gpt-4o-mini", 
        "temperature": 0.7,
        "max_tokens": 1000,
        "personality": None,
        "current_module": None,
        "module_results": {},
        "workflow_context": {},
        "user_id": "test_user",
        "routing_analysis": None,
        "session_id": "test_session",
        "memory_context": "Previous conversation about machine learning"
    }


class TestRouterNode:
    """Test router_node function."""

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_basic_routing(self, mock_openai, sample_chat_state):
        """Test basic message routing functionality."""
        # Mock the LLM response
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="chat",
            reason="General conversation",
            complexity="low"
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        assert result["current_module"] == "chat"
        assert result["routing_analysis"]["decision"] == "chat"
        assert result["routing_analysis"]["reason"] == "General conversation"
        assert result["routing_analysis"]["complexity"] == "low"
        assert "model_used" in result["routing_analysis"]

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_search_routing(self, mock_openai, sample_chat_state):
        """Test routing to search module."""
        sample_chat_state["messages"] = [HumanMessage(content="What's the latest news about AI?")]
        
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="search",
            reason="User asking for current information",
            complexity="medium"
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        assert result["current_module"] == "search"
        assert result["routing_analysis"]["decision"] == "search"
        assert result["routing_analysis"]["complexity"] == "medium"

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_analyzer_routing(self, mock_openai, sample_chat_state):
        """Test routing to analyzer module."""
        sample_chat_state["messages"] = [HumanMessage(content="Analyze this data for trends")]
        
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="analyzer",
            reason="User requesting data analysis",
            complexity="high"
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        assert result["current_module"] == "analyzer"
        assert result["routing_analysis"]["decision"] == "analyzer"
        assert result["routing_analysis"]["complexity"] == "high"

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_with_memory_context(self, mock_openai, sample_chat_state_with_memory):
        """Test router with memory context."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="chat",
            reason="Continuing conversation",
            complexity="low"
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state_with_memory)

        assert result["current_module"] == "chat"
        # Should have included memory context in the system prompt
        mock_structured.invoke.assert_called_once()

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_invalid_decision_fallback(self, mock_openai, sample_chat_state):
        """Test router fallback for invalid decisions."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="invalid_module",
            reason="Invalid routing decision",
            complexity="low"
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        # Should fallback to chat for invalid module
        assert result["current_module"] == "chat"

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_exception_handling(self, mock_openai, sample_chat_state):
        """Test router exception handling."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = Exception("API Error")
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        # Should fallback to chat on exception
        assert result["current_module"] == "chat"
        assert "error" in result["routing_analysis"]["reason"].lower()

    def test_router_node_no_user_message(self, sample_chat_state):
        """Test router with no user messages."""
        sample_chat_state["messages"] = [AIMessage(content="AI response")]

        result = router_node(sample_chat_state)

        assert result["current_module"] == "chat"
        assert result["routing_analysis"]["decision"] == "chat"
        assert "no user message" in result["routing_analysis"]["reason"].lower()

    def test_router_node_empty_messages(self, sample_chat_state):
        """Test router with empty message list."""
        sample_chat_state["messages"] = []

        result = router_node(sample_chat_state)

        assert result["current_module"] == "chat"
        assert result["routing_analysis"]["decision"] == "chat"


class TestIntegratorNode:
    """Test integrator_node function."""

    @patch('nodes.integrator_node.ChatOpenAI')
    def test_integrator_node_basic_integration(self, mock_openai, sample_chat_state):
        """Test basic integration functionality."""
        sample_chat_state["current_module"] = "chat"
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is a helpful response"
        mock_llm.invoke.return_value = mock_response
        mock_openai.return_value = mock_llm

        result = integrator_node(sample_chat_state)

        assert len(result["messages"]) == 2  # Original + AI response
        assert isinstance(result["messages"][1], AIMessage)
        assert result["messages"][1].content == "This is a helpful response"

    @patch('nodes.integrator_node.ChatOpenAI')
    def test_integrator_node_with_search_context(self, mock_openai, sample_chat_state):
        """Test integrator with search context."""
        sample_chat_state["current_module"] = "search"
        sample_chat_state["module_results"] = {
            "search": {
                "search_result_text": "Latest AI news from various sources",
                "citations": ["Source 1", "Source 2"],
                "sources": [{"title": "AI News", "url": "http://example.com"}]
            }
        }
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Based on recent search results, here's what I found about AI..."
        mock_llm.invoke.return_value = mock_response
        mock_openai.return_value = mock_llm

        result = integrator_node(sample_chat_state)

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][1], AIMessage)
        # Should include search context in system prompt
        mock_llm.invoke.assert_called_once()

    @patch('nodes.integrator_node.ChatOpenAI')
    def test_integrator_node_with_analysis_context(self, mock_openai, sample_chat_state):
        """Test integrator with analysis context."""
        sample_chat_state["current_module"] = "analyzer"
        sample_chat_state["module_results"] = {
            "analyzer": {
                "analysis_result_text": "Analysis shows positive trends in the data"
            }
        }
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Based on the analysis, I can see several key trends..."
        mock_llm.invoke.return_value = mock_response
        mock_openai.return_value = mock_llm

        result = integrator_node(sample_chat_state)

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][1], AIMessage)

    @patch('nodes.integrator_node.ChatOpenAI')
    def test_integrator_node_with_memory_context(self, mock_openai, sample_chat_state_with_memory):
        """Test integrator with memory context."""
        sample_chat_state_with_memory["current_module"] = "chat"
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Continuing our previous conversation..."
        mock_llm.invoke.return_value = mock_response
        mock_openai.return_value = mock_llm

        result = integrator_node(sample_chat_state_with_memory)

        assert len(result["messages"]) == 2
        # Should include memory context in system prompt
        mock_llm.invoke.assert_called_once()

    @patch('nodes.integrator_node.ChatOpenAI')
    def test_integrator_node_exception_handling(self, mock_openai, sample_chat_state):
        """Test integrator exception handling."""
        sample_chat_state["current_module"] = "chat"
        
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API Error")
        mock_openai.return_value = mock_llm

        result = integrator_node(sample_chat_state)

        # Should add error message
        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][1], AIMessage)
        assert "error" in result["messages"][1].content.lower()


class TestResponseRendererNode:
    """Test response_renderer_node function."""

    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_response_renderer_basic_formatting(self, mock_openai, sample_chat_state):
        """Test basic response formatting."""
        sample_chat_state["messages"] = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hello! How can I help you today?")
        ]
        sample_chat_state["current_module"] = "chat"
        
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_formatted_response = FormattedResponse(
            main_response="Hello! How can I help you today?",
            sources=[],
            follow_up_questions=None
        )
        mock_structured.invoke.return_value = mock_formatted_response
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = response_renderer_node(sample_chat_state)

        assert result["final_response"] == "Hello! How can I help you today?"
        assert result["sources"] == []
        assert result["follow_up_questions"] is None

    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_response_renderer_with_sources(self, mock_openai, sample_chat_state):
        """Test response formatting with sources."""
        sample_chat_state["messages"] = [
            HumanMessage(content="What's new in AI?"),
            AIMessage(content="Recent AI developments include... Sources: AI News Today")
        ]
        sample_chat_state["current_module"] = "search"
        
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_formatted_response = FormattedResponse(
            main_response="Recent AI developments include new machine learning techniques.",
            sources=["AI News Today - https://example.com/ai-news"],
            follow_up_questions=["What specific AI techniques are most promising?"]
        )
        mock_structured.invoke.return_value = mock_formatted_response
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = response_renderer_node(sample_chat_state)

        assert "Recent AI developments" in result["final_response"]
        assert len(result["sources"]) == 1
        assert "AI News Today" in result["sources"][0]
        assert len(result["follow_up_questions"]) == 1

    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_response_renderer_professional_style(self, mock_openai, sample_chat_state):
        """Test response formatting with professional style."""
        sample_chat_state["messages"] = [
            HumanMessage(content="Explain machine learning"),
            AIMessage(content="Machine learning is a subset of artificial intelligence...")
        ]
        sample_chat_state["current_module"] = "chat"
        sample_chat_state["personality"] = {"style": "professional", "tone": "formal"}
        
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_formatted_response = FormattedResponse(
            main_response="Machine learning represents a sophisticated subset of artificial intelligence.",
            sources=[],
            follow_up_questions=None
        )
        mock_structured.invoke.return_value = mock_formatted_response
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = response_renderer_node(sample_chat_state)

        assert "sophisticated" in result["final_response"]

    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_response_renderer_no_ai_message(self, mock_openai, sample_chat_state):
        """Test response renderer when no AI message exists."""
        sample_chat_state["messages"] = [HumanMessage(content="Hello")]
        sample_chat_state["current_module"] = "chat"

        result = response_renderer_node(sample_chat_state)

        assert result["final_response"] == "I apologize, but I don't have a response to format."
        assert result["sources"] == []
        assert result["follow_up_questions"] is None

    @patch('nodes.response_renderer_node.ChatOpenAI')
    def test_response_renderer_exception_handling(self, mock_openai, sample_chat_state):
        """Test response renderer exception handling."""
        sample_chat_state["messages"] = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hello there!")
        ]
        sample_chat_state["current_module"] = "chat"
        
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = Exception("Formatting error")
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = response_renderer_node(sample_chat_state)

        # Should return the original AI response on error
        assert result["final_response"] == "Hello there!"
        assert result["sources"] == []

    def test_response_renderer_default_personality(self, sample_chat_state):
        """Test response renderer with default personality settings."""
        sample_chat_state["messages"] = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!")
        ]
        sample_chat_state["current_module"] = "chat"
        sample_chat_state["personality"] = None

        with patch('nodes.response_renderer_node.ChatOpenAI') as mock_openai:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_formatted_response = FormattedResponse(
                main_response="Hi there!",
                sources=[],
                follow_up_questions=None
            )
            mock_structured.invoke.return_value = mock_formatted_response
            mock_llm.with_structured_output.return_value = mock_structured
            mock_openai.return_value = mock_llm

            result = response_renderer_node(sample_chat_state)

            assert result["final_response"] == "Hi there!" 