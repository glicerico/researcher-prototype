"""
Graph builder module that constructs the LangGraph for the conversation flow.
"""
import os
from langgraph.graph import StateGraph, END
from langsmith import Client
from nodes.base import ChatState, logger
from config import (
    LANGCHAIN_TRACING_V2,
    LANGCHAIN_API_KEY,
    LANGCHAIN_ENDPOINT,
    LANGCHAIN_PROJECT
)
from utils import visualize_langgraph

# Import all node functions
from nodes.initializer_node import initializer_node
from nodes.router_node import router_node
from nodes.search_optimizer_node import search_prompt_optimizer_node
from nodes.analysis_refiner_node import analysis_task_refiner_node
from nodes.search_node import search_node
from nodes.analyzer_node import analyzer_node
from nodes.integrator_node import integrator_node
from nodes.response_renderer_node import response_renderer_node

# Import new specialized search nodes
from nodes.semantic_scholar_node import semantic_scholar_search_node
from nodes.reddit_search_node import reddit_search_node
from nodes.pubmed_search_node import pubmed_search_node


def setup_tracing():
    """Configure LangSmith tracing based on environment variables."""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    logger.info(f"🔍 LangSmith tracing enabled for project: {LANGCHAIN_PROJECT}")


def create_chat_graph():
    """Create a LangGraph graph for orchestrating the flow of the interaction."""
    
    # Configure LangSmith tracing if enabled
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        setup_tracing()
    
    # Define the router function for conditional branching
    def router(state: ChatState) -> str:
        """Route to the appropriate module based on the current_module state."""
        logger.info(f"⚡ Flow: Routing to '{state['current_module']}' module")
        return state["current_module"]
    
    # Build and return the graph
    builder = StateGraph(ChatState)
    
    # Add all nodes
    builder.add_node("initializer", initializer_node)
    builder.add_node("router", router_node)
    builder.add_node("search_prompt_optimizer", search_prompt_optimizer_node)
    builder.add_node("analysis_task_refiner", analysis_task_refiner_node)
    builder.add_node("search", search_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("integrator", integrator_node)
    builder.add_node("response_renderer", response_renderer_node)
    
    # Add specialized search nodes
    builder.add_node("academic_search", semantic_scholar_search_node)
    builder.add_node("social_search", reddit_search_node)
    builder.add_node("medical_search", pubmed_search_node)
    
    # Define the workflow
    builder.set_entry_point("initializer")
    builder.add_edge("initializer", "router")
    
    # From router, conditionally go to different modules
    builder.add_conditional_edges(
        "router",
        router,
        {
            "search": "search_prompt_optimizer",
            "analyzer": "analysis_task_refiner",
            "academic_search": "academic_search",
            "social_search": "social_search", 
            "medical_search": "medical_search",
            "chat": "integrator" 
        }
    )
    
    # Connect the search optimization to search
    builder.add_edge("search_prompt_optimizer", "search")
    builder.add_edge("search", "integrator")
    
    # Connect specialized search nodes directly to integrator
    builder.add_edge("academic_search", "integrator")
    builder.add_edge("social_search", "integrator")
    builder.add_edge("medical_search", "integrator")
    
    # Connect the analysis refiner to analyzer
    builder.add_edge("analysis_task_refiner", "analyzer")
    builder.add_edge("analyzer", "integrator")
    
    # Connect the integrator to the response renderer
    builder.add_edge("integrator", "response_renderer")
    
    # End the graph after rendering the response (topic extraction moved to background)
    builder.add_edge("response_renderer", END)
    
    # Compile the graph
    graph = builder.compile()

    return graph


# Create a singleton instance of the graph
chat_graph = create_chat_graph()


def visualize_graph(output_file="graph.png"):
    """
    Generate a PNG visualization of the main chat LangGraph.
    
    Args:
        output_file: Path where to save the PNG file.
    
    Returns:
        bool: True if visualization was successful, False otherwise.
    """
    return visualize_langgraph(chat_graph, output_file, "Main Chat LangGraph")


def get_langsmith_client():
    """Get a LangSmith client if tracing is enabled."""
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        return Client(
            api_key=LANGCHAIN_API_KEY,
            api_url=LANGCHAIN_ENDPOINT
        )
    return None


# Automatically generate visualization whenever this module is run directly
if __name__ == "__main__":
    visualize_graph() 