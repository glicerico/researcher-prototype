import pytest
from unittest.mock import patch, MagicMock
import time
import subprocess

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils import get_current_datetime_str, get_last_user_message, visualize_langgraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


class TestGetCurrentDatetimeStr:
    """Test get_current_datetime_str function."""

    @patch('time.localtime')
    @patch('time.strftime')
    def test_get_current_datetime_str(self, mock_strftime, mock_localtime):
        """Test that get_current_datetime_str returns correctly formatted time."""
        mock_localtime.return_value = time.struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))
        mock_strftime.return_value = "2024-01-01 12:00:00 UTC"
        
        result = get_current_datetime_str()
        
        assert result == "2024-01-01 12:00:00 UTC"
        mock_strftime.assert_called_once_with("%Y-%m-%d %H:%M:%S %Z", mock_localtime.return_value)
        mock_localtime.assert_called_once()

    def test_get_current_datetime_str_real(self):
        """Test that get_current_datetime_str returns a valid time string."""
        result = get_current_datetime_str()
        
        # Should be a string with the expected format pattern
        assert isinstance(result, str)
        assert len(result) >= 19  # At least "YYYY-MM-DD HH:MM:SS"
        # Should contain year, month, day pattern
        assert "-" in result
        assert ":" in result


class TestGetLastUserMessage:
    """Test get_last_user_message function."""

    def test_get_last_user_message_single_human(self):
        """Test getting last user message with single human message."""
        messages = [HumanMessage(content="Hello, how are you?")]
        
        result = get_last_user_message(messages)
        
        assert result == "Hello, how are you?"

    def test_get_last_user_message_multiple_messages(self):
        """Test getting last user message from mixed message types."""
        messages = [
            HumanMessage(content="First message"),
            AIMessage(content="AI response"),
            HumanMessage(content="Second message"),
            SystemMessage(content="System message"),
            HumanMessage(content="Last user message")
        ]
        
        result = get_last_user_message(messages)
        
        assert result == "Last user message"

    def test_get_last_user_message_no_human_messages(self):
        """Test getting last user message when no human messages exist."""
        messages = [
            AIMessage(content="AI response"),
            SystemMessage(content="System message")
        ]
        
        result = get_last_user_message(messages)
        
        assert result is None

    def test_get_last_user_message_empty_list(self):
        """Test getting last user message from empty list."""
        messages = []
        
        result = get_last_user_message(messages)
        
        assert result is None

    def test_get_last_user_message_ai_messages_only(self):
        """Test getting last user message with only AI messages."""
        messages = [
            AIMessage(content="First AI response"),
            AIMessage(content="Second AI response")
        ]
        
        result = get_last_user_message(messages)
        
        assert result is None

    def test_get_last_user_message_mixed_order(self):
        """Test getting last user message with mixed message order."""
        messages = [
            AIMessage(content="AI first"),
            HumanMessage(content="Human first"),
            AIMessage(content="AI second"),
            SystemMessage(content="System"),
            HumanMessage(content="Human second"),
            AIMessage(content="AI third")
        ]
        
        result = get_last_user_message(messages)
        
        assert result == "Human second"


class TestVisualizeLanggraph:
    """Test visualize_langgraph function."""

    @patch('subprocess.run')
    @patch('builtins.open')
    def test_visualize_langgraph_success_draw_png(self, mock_open, mock_subprocess):
        """Test successful graph visualization using draw_png method."""
        # Mock successful graphviz check
        mock_subprocess.return_value = MagicMock()
        
        # Mock graph with draw_png method
        mock_graph = MagicMock()
        mock_graph_obj = MagicMock()
        mock_graph.get_graph.return_value = mock_graph_obj
        mock_graph_obj.draw_png.return_value = b"PNG data"
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is True
        mock_graph_obj.draw_png.assert_called_once()
        mock_file.write.assert_called_once_with(b"PNG data")

    @patch('subprocess.run')
    @patch('builtins.open')
    @patch('os.remove')
    def test_visualize_langgraph_fallback_to_dot(self, mock_remove, mock_open, mock_subprocess):
        """Test graph visualization falling back to DOT format."""
        # Mock successful graphviz check for first call, successful conversion for second
        mock_subprocess.side_effect = [MagicMock(), MagicMock()]
        
        # Mock graph with draw_graphviz method (draw_png fails)
        mock_graph = MagicMock()
        mock_graph_obj = MagicMock()
        mock_graph.get_graph.return_value = mock_graph_obj
        mock_graph_obj.draw_png.side_effect = AttributeError("draw_png not available")
        mock_graph_obj.draw_graphviz.return_value = "digraph G { A -> B; }"
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is True
        mock_graph_obj.draw_graphviz.assert_called_once()
        mock_file.write.assert_called_once_with("digraph G { A -> B; }")
        mock_remove.assert_called_once_with("test.dot")

    @patch('subprocess.run')
    def test_visualize_langgraph_no_graphviz(self, mock_subprocess):
        """Test graph visualization when graphviz is not installed."""
        # Mock graphviz check failure
        mock_subprocess.side_effect = subprocess.SubprocessError("Graphviz not found")
        
        mock_graph = MagicMock()
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is False

    @patch('subprocess.run')
    def test_visualize_langgraph_exception_handling(self, mock_subprocess):
        """Test graph visualization with general exception."""
        # Mock successful graphviz check
        mock_subprocess.return_value = MagicMock()
        
        # Mock graph that raises exception
        mock_graph = MagicMock()
        mock_graph.get_graph.side_effect = Exception("Graph error")
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is False

    @patch('subprocess.run')
    @patch('builtins.open')
    @patch('os.remove')
    def test_visualize_langgraph_multiple_fallback_methods(self, mock_remove, mock_open, mock_subprocess):
        """Test graph visualization trying multiple methods."""
        # Mock successful graphviz check and conversion
        mock_subprocess.side_effect = [MagicMock(), MagicMock()]
        
        # Mock graph with to_dot method (other methods fail)
        mock_graph = MagicMock()
        mock_graph_obj = MagicMock()
        mock_graph.get_graph.return_value = mock_graph_obj
        mock_graph_obj.draw_png.side_effect = AttributeError("draw_png not available")
        mock_graph_obj.draw_graphviz.side_effect = AttributeError("draw_graphviz not available")
        mock_graph_obj.to_dot.return_value = "digraph G { A -> B; }"
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is True
        mock_graph_obj.to_dot.assert_called_once()

    @patch('subprocess.run')
    def test_visualize_langgraph_no_suitable_method(self, mock_subprocess):
        """Test graph visualization when no suitable method is available."""
        # Mock successful graphviz check
        mock_subprocess.return_value = MagicMock()
        
        # Mock graph with no suitable methods
        mock_graph = MagicMock()
        mock_graph_obj = MagicMock()
        mock_graph.get_graph.return_value = mock_graph_obj
        # Remove all methods
        del mock_graph_obj.draw_png
        del mock_graph_obj.draw_graphviz
        del mock_graph_obj.to_dot
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is False

    @patch('subprocess.run')
    def test_visualize_langgraph_no_get_graph_method(self, mock_subprocess):
        """Test graph visualization when graph has no get_graph method."""
        # Mock successful graphviz check
        mock_subprocess.return_value = MagicMock()
        
        # Mock graph without get_graph method
        mock_graph = MagicMock()
        del mock_graph.get_graph
        
        result = visualize_langgraph(mock_graph, "test.png", "TestGraph")
        
        assert result is False

    def test_visualize_langgraph_default_parameters(self):
        """Test graph visualization with default parameters."""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = subprocess.SubprocessError("Graphviz not found")
            
            mock_graph = MagicMock()
            
            # Test with default parameters
            result = visualize_langgraph(mock_graph)
            
            assert result is False
            # Should have attempted graphviz check
            mock_subprocess.assert_called_once()

    @patch('subprocess.run')
    @patch('builtins.open')
    def test_visualize_langgraph_custom_filename(self, mock_open, mock_subprocess):
        """Test graph visualization with custom filename."""
        # Mock successful graphviz check
        mock_subprocess.return_value = MagicMock()
        
        # Mock graph with draw_png method
        mock_graph = MagicMock()
        mock_graph_obj = MagicMock()
        mock_graph.get_graph.return_value = mock_graph_obj
        mock_graph_obj.draw_png.return_value = b"PNG data"
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = visualize_langgraph(mock_graph, "custom_graph.png", "CustomGraph")
        
        assert result is True
        # Should open the custom filename
        mock_open.assert_called_with("custom_graph.png", 'wb') 