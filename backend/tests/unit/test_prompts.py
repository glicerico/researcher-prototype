import pytest
from prompts import (
    ROUTER_SYSTEM_PROMPT,
    SEARCH_OPTIMIZER_SYSTEM_PROMPT,
    ANALYSIS_REFINER_SYSTEM_PROMPT,
    PERPLEXITY_SYSTEM_PROMPT,
    INTEGRATOR_SYSTEM_PROMPT,
    RESPONSE_RENDERER_SYSTEM_PROMPT,
    TOPIC_EXTRACTOR_SYSTEM_PROMPT
)

def test_router_system_prompt_formatting():
    """Test that the router system prompt can be formatted correctly."""
    formatted = ROUTER_SYSTEM_PROMPT.format(current_time="2023-06-01 12:00:00", memory_context_section="")
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "1. chat" in formatted
    assert "2. search" in formatted
    assert "3. analyzer" in formatted

def test_search_optimizer_system_prompt_formatting():
    """Test that the search optimizer system prompt can be formatted correctly."""
    formatted = SEARCH_OPTIMIZER_SYSTEM_PROMPT.format(current_time="2023-06-01 12:00:00", memory_context_section="")
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "transform the LATEST user question" in formatted


def test_response_renderer_system_prompt_formatting():
    """Test that the response renderer system prompt can be formatted correctly."""
    formatted = RESPONSE_RENDERER_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00",
        style="concise",
        tone="professional",
        module_used="search"
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "concise" in formatted
    assert "professional" in formatted
    assert "search" in formatted

def test_topic_extractor_system_prompt_formatting():
    """Test that the topic extractor system prompt can be formatted correctly."""
    formatted = TOPIC_EXTRACTOR_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00",
        existing_topics_section="Test existing topics section",
        min_confidence=0.6,
        max_suggestions=5
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "Test existing topics section" in formatted
    assert "0.6" in formatted
    assert "5" in formatted
    assert "research-worthy topics" in formatted
    assert "NEW topics" in formatted  # Should emphasize new topics
    # Should NOT contain JSON structure since we use Pydantic structured output
    assert "{{" not in formatted  # No JSON formatting instructions 