import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodes.topic_extractor_node import topic_extractor_node
from nodes.base import ChatState
from langchain_core.messages import HumanMessage, AIMessage
from llm_models import TopicSuggestions, TopicSuggestionItem


def test_topic_extractor_structured_output():
    """Test that the topic extractor uses structured output correctly."""
    
    # Create a test state with sufficient conversation history
    state = {
        "messages": [
            HumanMessage(content="What are the latest trends in AI research?"),
            AIMessage(content="Current AI research trends include transformer architectures, multimodal learning, and ethical AI frameworks.")
        ],
        "module_results": {}
    }
    
    # Create mock topic suggestions
    mock_topic_suggestions = TopicSuggestions(
        topics=[
            TopicSuggestionItem(
                name="AI Research Trends",
                description="Latest developments in artificial intelligence research and methodologies",
                confidence_score=0.85
            ),
            TopicSuggestionItem(
                name="Transformer Architecture",
                description="Evolution of transformer models and their applications",
                confidence_score=0.75
            )
        ]
    )
    
    with patch('nodes.topic_extractor_node.ChatOpenAI') as mock_openai:
        # Mock the structured extractor
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_topic_suggestions
        mock_instance.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_instance
        
        # Run the topic extractor
        result = topic_extractor_node(state)
        
        # Verify the structured output was used
        mock_instance.with_structured_output.assert_called_once()
        assert mock_instance.with_structured_output.call_args[0][0] == TopicSuggestions
        
        # Check the results
        assert result["module_results"]["topic_extractor"]["success"] is True
        topics = result["module_results"]["topic_extractor"]["result"]
        
        # Should have 2 topics
        assert len(topics) == 2
        
        # Check topic structure
        assert topics[0]["name"] == "AI Research Trends"
        assert topics[0]["confidence_score"] == 0.85
        assert topics[1]["name"] == "Transformer Architecture"
        assert topics[1]["confidence_score"] == 0.75


def test_topic_extractor_confidence_filtering():
    """Test that topics are filtered by confidence threshold."""
    
    # Create a test state
    state = {
        "messages": [
            HumanMessage(content="Test message"),
            AIMessage(content="Test response")
        ],
        "module_results": {}
    }
    
    # Create mock topic suggestions with varying confidence
    mock_topic_suggestions = TopicSuggestions(
        topics=[
            TopicSuggestionItem(
                name="High Confidence Topic",
                description="This should be included",
                confidence_score=0.8
            ),
            TopicSuggestionItem(
                name="Low Confidence Topic", 
                description="This should be filtered out",
                confidence_score=0.4  # Below default threshold of 0.6
            )
        ]
    )
    
    with patch('nodes.topic_extractor_node.ChatOpenAI') as mock_openai:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_topic_suggestions
        mock_instance.with_structured_output.return_value = mock_structured
        mock_openai.return_value = mock_instance
        
        # Run the topic extractor
        result = topic_extractor_node(state)
        
        # Check the results - only high confidence topic should remain
        topics = result["module_results"]["topic_extractor"]["result"]
        assert len(topics) == 1
        assert topics[0]["name"] == "High Confidence Topic"
        assert topics[0]["confidence_score"] == 0.8


def test_topic_extractor_insufficient_history():
    """Test behavior with insufficient conversation history."""
    
    # Create a state with only one message
    state = {
        "messages": [
            HumanMessage(content="Hello")
        ],
        "module_results": {}
    }
    
    # Run the topic extractor
    result = topic_extractor_node(state)
    
    # Should fail due to insufficient history
    assert result["module_results"]["topic_extractor"]["success"] is False
    assert result["module_results"]["topic_extractor"]["message"] == "Insufficient conversation history"
    assert result["module_results"]["topic_extractor"]["result"] == []


if __name__ == "__main__":
    pytest.main([__file__]) 