# integration_test.py
import os
import pytest
from graph_builder import create_chat_graph

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), 
                   reason="No OpenAI API key found")
def test_openai_integration(chat_graph):
    """Test that the chat graph works with the real OpenAI API."""
    # Create a test state
    state = {
        "messages": [
            {"role": "user", "content": "Say 'This is a test' and nothing else"}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.0,  # Use 0 for deterministic results
        "max_tokens": 20
    }
    
    # Run the graph with the real API
    result = chat_graph.invoke(state)
    
    # Check the result
    assert "messages" in result
    assert len(result["messages"]) == 2
    assert result["messages"][1]["role"] == "assistant"
    print(f"API Response: {result['messages'][1]['content']}")
