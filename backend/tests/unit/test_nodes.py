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
            complexity=3  # int value between 1-10
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        assert result["current_module"] == "chat"
        assert result["routing_analysis"]["decision"] == "chat"
        assert result["routing_analysis"]["reason"] == "General conversation"
        assert result["routing_analysis"]["complexity"] == 3
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
            complexity=5  # int value instead of string
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        assert result["current_module"] == "search"
        assert result["routing_analysis"]["decision"] == "search"
        assert result["routing_analysis"]["reason"] == "User asking for current information"
        assert result["routing_analysis"]["complexity"] == 5

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_analyzer_routing(self, mock_openai, sample_chat_state):
        """Test routing to analyzer module."""
        sample_chat_state["messages"] = [HumanMessage(content="Analyze this data for trends")]

        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="analyzer",
            reason="User requesting data analysis",
            complexity=8  # int value instead of string
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        assert result["current_module"] == "analyzer"
        assert result["routing_analysis"]["decision"] == "analyzer"

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_with_memory_context(self, mock_openai, sample_chat_state_with_memory):
        """Test router with memory context."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="chat",
            reason="Continuing conversation",
            complexity=2  # int value instead of string
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state_with_memory)

        assert result["current_module"] == "chat"
        assert result["routing_analysis"]["decision"] == "chat"

    @patch('nodes.router_node.ChatOpenAI')
    def test_router_node_invalid_decision_fallback(self, mock_openai, sample_chat_state):
        """Test router fallback for invalid decisions."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_routing_result = RoutingAnalysis(
            decision="invalid_module",
            reason="Invalid routing decision",
            complexity=1  # int value instead of string
        )
        mock_structured.invoke.return_value = mock_routing_result
        mock_llm.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_llm

        result = router_node(sample_chat_state)

        # Router should fallback to chat for invalid decisions
        assert result["current_module"] == "chat"  # Router node likely does fallback

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

        # Integrator adds response to workflow_context, not directly to messages
        assert "workflow_context" in result
        assert "integrator_response" in result["workflow_context"]
        assert result["workflow_context"]["integrator_response"] == "This is a helpful response"

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

        # Integrator stores results in workflow_context, not messages
        assert "workflow_context" in result
        assert "integrator_response" in result["workflow_context"]
        assert "Based on recent search results" in result["workflow_context"]["integrator_response"]

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

        # Integrator stores results in workflow_context, not messages
        assert "workflow_context" in result
        assert "integrator_response" in result["workflow_context"]
        assert "Based on the analysis" in result["workflow_context"]["integrator_response"]

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

        # Integrator stores results in workflow_context, not messages
        assert "workflow_context" in result
        assert "integrator_response" in result["workflow_context"]
        assert "Continuing our previous conversation" in result["workflow_context"]["integrator_response"]

    @patch('nodes.integrator_node.ChatOpenAI')
    def test_integrator_node_exception_handling(self, mock_openai, sample_chat_state):
        """Test integrator exception handling."""
        sample_chat_state["current_module"] = "chat"
        
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API Error")
        mock_openai.return_value = mock_llm

        result = integrator_node(sample_chat_state)

        # Should add error to workflow context
        assert "workflow_context" in result
        assert "integrator_error" in result["workflow_context"]


class TestResponseRendererNode:
    """Test response_renderer_node function."""

    def test_response_renderer_with_integrator_response(self, sample_chat_state):
        """Test response renderer with proper integrator response."""
        sample_chat_state["messages"] = [
            HumanMessage(content="Hello"),
        ]
        sample_chat_state["current_module"] = "chat"
        sample_chat_state["personality"] = {"style": "helpful", "tone": "friendly"}
        sample_chat_state["workflow_context"] = {
            "integrator_response": "Hello! How can I help you today?"
        }

        with patch('nodes.response_renderer_node.ChatOpenAI') as mock_openai:
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

            # Should add the formatted response as an AI message
            assert len(result["messages"]) == 2
            assert isinstance(result["messages"][1], AIMessage)
            assert result["messages"][1].content == "Hello! How can I help you today?"

    def test_response_renderer_with_sources_and_followups(self, sample_chat_state):
        """Test response renderer with sources and follow-up questions."""
        sample_chat_state["messages"] = [HumanMessage(content="What's new in AI?")]
        sample_chat_state["current_module"] = "search"
        sample_chat_state["personality"] = {"style": "professional", "tone": "formal"}
        sample_chat_state["workflow_context"] = {
            "integrator_response": "Recent AI developments include new techniques."
        }

        with patch('nodes.response_renderer_node.ChatOpenAI') as mock_openai:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_formatted_response = FormattedResponse(
                main_response="Recent AI developments include new machine learning techniques.",
                sources=["AI News Today - https://example.com/ai-news", "Tech Report - https://example.com/tech"],
                follow_up_questions=["What specific AI techniques are most promising?", "How will this impact industry?"]
            )
            mock_structured.invoke.return_value = mock_formatted_response
            mock_llm.with_structured_output.return_value = mock_structured
            mock_openai.return_value = mock_llm

            result = response_renderer_node(sample_chat_state)

            # Should add the formatted response with sources and follow-ups
            assert len(result["messages"]) == 2
            assert isinstance(result["messages"][1], AIMessage)
            response_content = result["messages"][1].content
            
            # Check main response
            assert "Recent AI developments include new machine learning techniques." in response_content
            
            # Check sources were appended
            assert "**Sources:**" in response_content
            assert "AI News Today - https://example.com/ai-news" in response_content
            assert "Tech Report - https://example.com/tech" in response_content
            
            # Check follow-up questions were appended
            assert "1. What specific AI techniques are most promising?" in response_content
            assert "2. How will this impact industry?" in response_content

    def test_response_renderer_no_integrator_response(self, sample_chat_state):
        """Test response renderer when no integrator response exists."""
        sample_chat_state["messages"] = [HumanMessage(content="Hello")]
        sample_chat_state["current_module"] = "chat"
        sample_chat_state["personality"] = {"style": "helpful", "tone": "friendly"}
        sample_chat_state["workflow_context"] = {}  # No integrator response

        result = response_renderer_node(sample_chat_state)

        # Should add error message
        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][1], AIMessage)
        assert "error" in result["messages"][1].content.lower()
        assert "Unknown error" in result["messages"][1].content

    def test_response_renderer_with_integrator_error(self, sample_chat_state):
        """Test response renderer when integrator had an error."""
        sample_chat_state["messages"] = [HumanMessage(content="Hello")]
        sample_chat_state["current_module"] = "chat"
        sample_chat_state["personality"] = {"style": "helpful", "tone": "friendly"}
        sample_chat_state["workflow_context"] = {
            "integrator_error": "API connection failed"
        }

        result = response_renderer_node(sample_chat_state)

        # Should add error message with specific error
        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][1], AIMessage)
        assert "API connection failed" in result["messages"][1].content

    def test_response_renderer_with_none_personality(self, sample_chat_state):
        """Test response renderer with None personality uses defaults."""
        sample_chat_state["messages"] = [HumanMessage(content="Hello")]
        sample_chat_state["current_module"] = "chat"
        sample_chat_state["personality"] = None  # None personality
        sample_chat_state["workflow_context"] = {
            "integrator_response": "Hello! How can I help you today?"
        }

        with patch('nodes.response_renderer_node.ChatOpenAI') as mock_openai:
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

            # Should handle None personality gracefully with defaults
            assert len(result["messages"]) == 2
            assert isinstance(result["messages"][1], AIMessage)
            assert result["messages"][1].content == "Hello! How can I help you today?"
            
            # Verify the system prompt was called with default values
            system_call = mock_structured.invoke.call_args[0][0][0]  # First message should be system prompt
            assert "helpful" in system_call.content  # Default style
            assert "friendly" in system_call.content  # Default tone

    def test_response_renderer_llm_exception_fallback(self, sample_chat_state):
        """Test response renderer falls back to raw response on LLM exception."""
        sample_chat_state["messages"] = [HumanMessage(content="Hello")]
        sample_chat_state["current_module"] = "chat" 
        sample_chat_state["personality"] = {"style": "helpful", "tone": "friendly"}
        sample_chat_state["workflow_context"] = {
            "integrator_response": "Raw response from integrator"
        }

        with patch('nodes.response_renderer_node.ChatOpenAI') as mock_openai:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.invoke.side_effect = Exception("LLM formatting failed")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_openai.return_value = mock_llm

            result = response_renderer_node(sample_chat_state)

            # Should fallback to raw response when formatting fails
            assert len(result["messages"]) == 2
            assert isinstance(result["messages"][1], AIMessage)
            assert result["messages"][1].content == "Raw response from integrator" 