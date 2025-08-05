"""
Research initializer node for setting up synthetic conversation states for autonomous research.
"""
import time
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from nodes.base import (
    ChatState,
    logger,
    get_current_datetime_str
)
from config import DEFAULT_MODEL


def research_initializer_node(state: ChatState) -> ChatState:
    """Initialize state for autonomous research with synthetic conversation context."""
    logger.info("🔬 Research Initializer: Setting up autonomous research state")
    
    # Initialize state objects for research workflow
    state["workflow_context"] = state.get("workflow_context", {})
    state["module_results"] = state.get("module_results", {})
    
    # Get research context from workflow_context
    research_context = state["workflow_context"].get("research_context", {})
    topic_name = research_context.get("topic_name", "Unknown Topic")
    topic_description = research_context.get("topic_description", "")
    user_id = research_context.get("user_id", "unknown")
    
    # Create synthetic conversation state for research
    # This mimics a user asking for research on the topic
    research_query = state["workflow_context"].get("research_query", f"Find recent developments about {topic_name}")
    
    # Create synthetic messages for the research workflow
    synthetic_messages = [
        SystemMessage(content=f"Current time: {get_current_datetime_str()}. You are conducting autonomous research."),
        HumanMessage(content=research_query)
    ]
    
    # Update state with synthetic conversation
    state["messages"] = synthetic_messages
    state["user_id"] = user_id
    
    # Set research-specific parameters
    state["model"] = research_context.get("model", DEFAULT_MODEL)
    state["temperature"] = 0.3  # Lower temperature for more focused research
    state["max_tokens"] = 2000
    state["personality"] = {"style": "research", "tone": "analytical"}
    
    # Generate a research thread ID
    research_thread_id = f"research_{user_id}_{topic_name.replace(' ', '_')}_{int(time.time())}"
    state["thread_id"] = research_thread_id
    
    # Store research metadata
    state["workflow_context"]["research_metadata"] = {
        "topic_name": topic_name,
        "topic_description": topic_description,
        "research_query": research_query,
        "research_thread_id": research_thread_id,
        "started_at": time.time(),
        "user_id": user_id
    }
    
    # Set the target module for research workflow
    state["current_module"] = "search"  # Research always goes through search
    
    logger.info(f"🔬 Research Initializer: Initialized research for topic '{topic_name}' with query '{research_query[:50]}...'")
    
    return state 