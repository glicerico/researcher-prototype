import pytest
from prompts import (
    ROUTER_SYSTEM_PROMPT,
    SEARCH_OPTIMIZER_SYSTEM_PROMPT,
    ANALYSIS_REFINER_SYSTEM_PROMPT,
    PERPLEXITY_SYSTEM_PROMPT,
    INTEGRATOR_SYSTEM_PROMPT,
    SEARCH_RESULTS_TEMPLATE,
    ANALYSIS_RESULTS_TEMPLATE,
    RESPONSE_RENDERER_SYSTEM_PROMPT
)

def test_router_system_prompt_formatting():
    """Test that the router system prompt can be formatted correctly."""
    formatted = ROUTER_SYSTEM_PROMPT.format(current_time="2023-06-01 12:00:00")
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "1. chat" in formatted
    assert "2. search" in formatted
    assert "3. analyzer" in formatted

def test_search_optimizer_system_prompt_formatting():
    """Test that the search optimizer system prompt can be formatted correctly."""
    formatted = SEARCH_OPTIMIZER_SYSTEM_PROMPT.format(current_time="2023-06-01 12:00:00")
    assert "Current date and time: 2023-06-01 12:00:00" in formatted
    assert "transform the LATEST user question" in formatted

def test_search_results_template_formatting():
    """Test that the search results template can be formatted correctly."""
    search_results = "Result 1\nResult 2\nResult 3"
    formatted = SEARCH_RESULTS_TEMPLATE.format(search_result_text=search_results)
    assert "Result 1" in formatted
    assert "Result 2" in formatted
    assert "Result 3" in formatted
    assert "IMPORTANT FACTUAL INFORMATION FROM SEARCH" in formatted

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