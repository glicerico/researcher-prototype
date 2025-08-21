import pytest
from prompts import (
    MULTI_SOURCE_SYSTEM_PROMPT,
    SEARCH_OPTIMIZER_SYSTEM_PROMPT,
    ANALYSIS_REFINER_SYSTEM_PROMPT,
    PERPLEXITY_SYSTEM_PROMPT,
    INTEGRATOR_SYSTEM_PROMPT,
    RESPONSE_RENDERER_SYSTEM_PROMPT,
    TOPIC_EXTRACTOR_SYSTEM_PROMPT
)

def test_multi_source_system_prompt_formatting():
    """Test that the multi-source system prompt can be formatted correctly."""
    formatted = MULTI_SOURCE_SYSTEM_PROMPT.format(current_time="2023-06-01 12:00:00", memory_context_section="")
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "CHAT" in formatted
    assert "SEARCH" in formatted 
    assert "ANALYSIS" in formatted
    assert len(formatted) > 100


def test_search_optimizer_system_prompt_formatting():
    """Test that the search optimizer system prompt can be formatted correctly."""
    formatted = SEARCH_OPTIMIZER_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00", 
        user_profile_section="Test profile",
        memory_context_section=""
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "Test profile" in formatted
    assert len(formatted) > 100


def test_analysis_refiner_system_prompt_formatting():
    """Test that the analysis refiner system prompt can be formatted correctly."""
    formatted = ANALYSIS_REFINER_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00",
        memory_context_section=""
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert len(formatted) > 100


def test_perplexity_system_prompt_formatting():
    """Test that the Perplexity system prompt can be formatted correctly."""
    formatted = PERPLEXITY_SYSTEM_PROMPT.format(current_time="2023-06-01 12:00:00")
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert len(formatted) > 50


def test_integrator_system_prompt_formatting():
    """Test that the integrator system prompt can be formatted correctly."""
    formatted = INTEGRATOR_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00",
        memory_context_section="Test memory",
        context_section="Test context"
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "Test memory" in formatted
    assert "Test context" in formatted
    assert len(formatted) > 100


def test_response_renderer_system_prompt_formatting():
    """Test that the response renderer system prompt can be formatted correctly."""
    formatted = RESPONSE_RENDERER_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00",
        response_length="medium",
        detail_level="balanced",
        use_bullet_points="True",
        include_key_insights="True",
        prefers_structured="True",
        optimal_length="500",
        style="helpful",
        tone="friendly",
        module_used="search"
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "medium" in formatted
    assert "search" in formatted
    assert len(formatted) > 100


def test_topic_extractor_system_prompt_formatting():
    """Test that the topic extractor system prompt can be formatted correctly."""
    formatted = TOPIC_EXTRACTOR_SYSTEM_PROMPT.format(
        current_time="2023-06-01 12:00:00",
        existing_topics_section="Existing topics",
        min_confidence=0.7,
        max_suggestions=3
    )
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "Existing topics" in formatted
    assert "0.7" in formatted
    assert len(formatted) > 100


def test_all_prompts_are_strings():
    """Test that all prompts are string types."""
    prompts = [
        MULTI_SOURCE_SYSTEM_PROMPT,
        SEARCH_OPTIMIZER_SYSTEM_PROMPT,
        ANALYSIS_REFINER_SYSTEM_PROMPT,
        PERPLEXITY_SYSTEM_PROMPT,
        INTEGRATOR_SYSTEM_PROMPT,
        RESPONSE_RENDERER_SYSTEM_PROMPT,
        TOPIC_EXTRACTOR_SYSTEM_PROMPT
    ]
    
    for prompt in prompts:
        assert isinstance(prompt, str)
        assert len(prompt) > 10  # All prompts should have substantial content


def test_prompts_contain_formatting_placeholders():
    """Test that prompts contain expected formatting placeholders."""
    # Multi-source prompt should have current_time and memory_context_section
    assert "{current_time}" in MULTI_SOURCE_SYSTEM_PROMPT
    assert "{memory_context_section}" in MULTI_SOURCE_SYSTEM_PROMPT
    
    # Search optimizer should have user profile and memory context
    assert "{current_time}" in SEARCH_OPTIMIZER_SYSTEM_PROMPT
    assert "{user_profile_section}" in SEARCH_OPTIMIZER_SYSTEM_PROMPT
    
    # Integrator should have context sections
    assert "{current_time}" in INTEGRATOR_SYSTEM_PROMPT
    assert "{context_section}" in INTEGRATOR_SYSTEM_PROMPT