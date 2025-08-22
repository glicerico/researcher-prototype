"""
Research graph builder module that constructs the LangGraph for autonomous research workflow.
"""
import os
from langgraph.graph import StateGraph, END
from nodes.base import ChatState, logger
from config import (
    LANGCHAIN_TRACING_V2,
    LANGCHAIN_API_KEY,
    LANGCHAIN_ENDPOINT,
    LANGCHAIN_PROJECT
)
from utils import visualize_langgraph

# Import research-specific nodes
from nodes.research_initializer_node import research_initializer_node
from nodes.research_query_generator_node import research_query_generator_node
from nodes.research_quality_assessor_node import research_quality_assessor_node
from nodes.research_deduplication_node import research_deduplication_node
from nodes.research_storage_node import research_storage_node

# Import reused nodes from existing graph  
from nodes.integrator_node import integrator_node
from nodes.response_renderer_node import response_renderer_node

# Import multi-source search coordination
from nodes.research_source_selector_node import research_source_selector_node
from nodes.source_coordinator_node import source_coordinator_node
from nodes.search_optimizer_node import search_prompt_optimizer_node


def setup_research_tracing():
    """Configure LangSmith tracing for research graph."""
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = f"{LANGCHAIN_PROJECT}-research"  # Separate project for research
        logger.info(f"🔍 LangSmith tracing enabled for research project: {LANGCHAIN_PROJECT}-research")


def create_research_graph():
    """Create a LangGraph graph for orchestrating autonomous research workflow."""
    
    # Configure LangSmith tracing if enabled
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        setup_research_tracing()
    
    # Build the research graph
    builder = StateGraph(ChatState)
    
    # Add research-specific nodes
    builder.add_node("research_initializer", research_initializer_node)
    builder.add_node("research_query_generator", research_query_generator_node)
    builder.add_node("research_source_selector", research_source_selector_node)
    
    # Add source coordinator node (handles all search sources internally)
    builder.add_node("source_coordinator", source_coordinator_node)
    # Add shared search optimizer to refine queries before multi-source search
    builder.add_node("search_prompt_optimizer", search_prompt_optimizer_node)
    
    # Add processing nodes
    builder.add_node("integrator", integrator_node)
    builder.add_node("response_renderer", response_renderer_node)
    builder.add_node("research_quality_assessor", research_quality_assessor_node)
    builder.add_node("research_deduplication", research_deduplication_node)
    builder.add_node("research_storage", research_storage_node)
    
    # Define the research workflow
    builder.set_entry_point("research_initializer")
    
    # Multi-source research workflow:
    # Initialize -> Generate Query -> Select Sources -> Coordinate Multi-Source Search -> Integrate -> Process
    builder.add_edge("research_initializer", "research_query_generator")
    builder.add_edge("research_query_generator", "research_source_selector")
    # Run optimizer after selecting sources so it can generate source-aware queries (e.g., HN social_query)
    builder.add_edge("research_source_selector", "search_prompt_optimizer")
    builder.add_edge("search_prompt_optimizer", "source_coordinator")
    builder.add_edge("source_coordinator", "integrator")
    builder.add_edge("integrator", "response_renderer")
    builder.add_edge("response_renderer", "research_quality_assessor")
    builder.add_edge("research_quality_assessor", "research_deduplication")
    builder.add_edge("research_deduplication", "research_storage")
    
    # End the graph after storage
    builder.add_edge("research_storage", END)
    
    # Compile the research graph
    research_graph = builder.compile()
    
    logger.info("🔬 Research graph compiled successfully")
    return research_graph


# Create a singleton instance of the research graph
research_graph = create_research_graph()


def visualize_research_graph(output_file="research_graph.png"):
    """
    Generate a PNG visualization of the research LangGraph.
    
    Args:
        output_file: Path where to save the PNG file.
    
    Returns:
        bool: True if visualization was successful, False otherwise.
    """
    return visualize_langgraph(research_graph, output_file, "Research LangGraph")


def generate_all_graph_visualizations():
    """
    Generate visualizations for both the main chat graph and research graph.
    
    Returns:
        dict: Results of visualization generation for both graphs
    """
    results = {}
    
    print("🔬 Generating all graph visualizations...")
    
    # Generate research graph visualization
    print("\n1. Generating Research Graph visualization...")
    research_result = visualize_research_graph("research_graph.png")
    results["research_graph"] = {
        "success": research_result,
        "filename": "research_graph.png"
    }
    
    # Generate main chat graph visualization
    try:
        from graph_builder import visualize_graph
        print("\n2. Generating Main Chat Graph visualization...")
        chat_result = visualize_graph("chat_graph.png")
        results["chat_graph"] = {
            "success": chat_result,
            "filename": "chat_graph.png"
        }
    except ImportError as e:
        print(f"Could not import main graph visualization: {e}")
        results["chat_graph"] = {
            "success": False,
            "error": str(e)
        }
    
    # Summary
    print(f"\n📊 Visualization Summary:")
    for graph_name, result in results.items():
        status = "✅ Success" if result.get("success") else "❌ Failed"
        filename = result.get("filename", "N/A")
        print(f"  {graph_name}: {status} - {filename}")
    
    return results


def show_help():
    """Show usage information for the research graph builder."""
    print("""
🔬 Research Graph Builder - Visualization Tool

USAGE:
  python research_graph_builder.py [option|filename]

OPTIONS:
  --help, -h        Show this help message
  --all             Generate both research graph and main chat graph visualizations
  <filename.png>    Generate research graph with custom filename

EXAMPLES:
  python research_graph_builder.py                          # Generate research_graph.png
  python research_graph_builder.py --all                    # Generate both graphs
  python research_graph_builder.py my_custom_graph.png      # Custom filename
  python research_graph_builder.py --help                   # Show this help

OUTPUT FILES:
  research_graph.png    - Research workflow visualization
  chat_graph.png        - Main chat workflow visualization (with --all)
    """)


# Automatically generate visualization when this module is run directly
if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg in ["--help", "-h"]:
            # Show help
            show_help()
        elif arg == "--all":
            # Generate both graphs
            generate_all_graph_visualizations()
        else:
            # Use custom filename
            output_file = arg
            print(f"Generating research graph visualization: {output_file}")
            success = visualize_research_graph(output_file)
            if success:
                print(f"✅ Successfully generated: {output_file}")
            else:
                print(f"❌ Failed to generate: {output_file}")
    else:
        # Default behavior
        visualize_research_graph() 