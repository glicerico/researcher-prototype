"""
Graph builder module that constructs the LangGraph for the conversation flow.
"""
import os
from langgraph.graph import StateGraph, END, START
from langsmith import Client
from nodes.base import ChatState, logger
from config import (
    LANGCHAIN_TRACING_V2,
    LANGCHAIN_API_KEY,
    LANGCHAIN_ENDPOINT,
    LANGCHAIN_PROJECT
)

# Import all node functions
from nodes.initializer_node import initializer_node
from nodes.router_node import router_node
from nodes.search_optimizer_node import search_prompt_optimizer_node
from nodes.analysis_refiner_node import analysis_task_refiner_node
from nodes.search_node import search_node
from nodes.analyzer_node import analyzer_node
from nodes.memory_node import memory_retrieval_node, memory_storage_node
from nodes.integrator_node import integrator_node
from nodes.response_renderer_node import response_renderer_node


def setup_tracing():
    """Configure LangSmith tracing based on environment variables."""
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        # Set up environment variables for LangSmith tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
        logger.info(f"🔍 LangSmith tracing enabled for project: {LANGCHAIN_PROJECT}")
        return True
    return False


def build_graph():
    """Build the LangGraph workflow for the conversation."""
    # Set up LangSmith tracing if configured
    tracing_enabled = setup_tracing()
    
    # Create a new graph
    graph = StateGraph(ChatState)
    
    # Add all nodes to the graph
    graph.add_node("initialize", initializer_node)
    graph.add_node("router", router_node)
    graph.add_node("memory_retrieval", memory_retrieval_node)
    graph.add_node("search_optimizer", search_prompt_optimizer_node)
    graph.add_node("analysis_refiner", analysis_task_refiner_node)
    graph.add_node("search", search_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("integrator", integrator_node)
    graph.add_node("memory_storage", memory_storage_node)
    graph.add_node("renderer", response_renderer_node)
    
    # Define the router function for conditional branching
    def router(state: ChatState) -> str:
        """Route to the appropriate module based on the current_module state."""
        logger.info(f"⚡ Flow: Routing to '{state['current_module']}' module")
        return state["current_module"]

    # Add the entry point from START to router
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "memory_retrieval")
    graph.add_edge("memory_retrieval", "router")

    # Define the conditional edges
    graph.add_conditional_edges(
        "router",
        router, {
            "search": "search_optimizer",
            "analyzer": "analysis_refiner",
            "chat": "integrator" 
        }
    )
    
    # Search path
    graph.add_edge("search_optimizer", "search")
    graph.add_edge("search", "integrator")
    
    # Analysis path
    graph.add_edge("analysis_refiner", "analyzer")
    graph.add_edge("analyzer", "integrator")
    
    # Final steps
    graph.add_edge("integrator", "memory_storage")
    graph.add_edge("memory_storage", "renderer")
    graph.add_edge("renderer", END)
    
    # Compile the graph
    workflow = graph.compile()
    
    if tracing_enabled:
        logger.info("LangSmith tracing enabled for workflow")
    
    return workflow


# Create a singleton instance of the graph
chat_graph = build_graph()


def visualize_graph(output_file="graph.png"):
    """
    Generate a PNG visualization of the LangGraph using built-in functionality.
    
    Args:
        output_file: Path where to save the PNG file.
    
    Returns:
        bool: True if visualization was successful, False otherwise.
    """
    try:
        import os
        import subprocess
        
        # First, check if graphviz is installed
        try:
            subprocess.run(["dot", "-V"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: Graphviz not found. Install it with: sudo apt-get install graphviz")
            return False
            
        # Create a DOT file from the graph
        dot_file = output_file.replace('.png', '.dot')
        
        print(f"Generating visualization of LangGraph...")
        
        # Try using the built-in visualization methods
        try:
            # Method 1: Try using draw_png if available (most direct method)
            png_data = chat_graph.get_graph().draw_png()
            with open(output_file, 'wb') as f:
                f.write(png_data)
            print(f"Visualization saved to {output_file}")
            return True
        except (AttributeError, ImportError) as e:
            print(f"draw_png method not available: {str(e)}")
            
            # Method 2: Fall back to DOT format
            try:
                dot_data = chat_graph.get_graph().draw_graphviz()
                with open(dot_file, 'w') as f:
                    f.write(dot_data)
                # Use graphviz to convert to PNG
                subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
                print(f"Visualization saved to {output_file}")
                # Clean up the DOT file
                os.remove(dot_file)
                return True
            except (AttributeError, ImportError) as e:
                print(f"draw_graphviz method not available: {str(e)}")
                
                # Method 3: If all else fails, use any available method
                if hasattr(chat_graph, 'get_graph'):
                    graph_obj = chat_graph.get_graph()
                    for method_name in ['draw_png', 'draw_graphviz', 'to_dot']:
                        if hasattr(graph_obj, method_name):
                            try:
                                method = getattr(graph_obj, method_name)
                                result = method()
                                if method_name == 'draw_png':
                                    with open(output_file, 'wb') as f:
                                        f.write(result)
                                    print(f"Visualization saved to {output_file} using {method_name}")
                                    return True
                                elif method_name in ['draw_graphviz', 'to_dot']:
                                    with open(dot_file, 'w') as f:
                                        f.write(result)
                                    subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
                                    print(f"Visualization saved to {output_file} using {method_name}")
                                    os.remove(dot_file)
                                    return True
                            except Exception as e:
                                print(f"Method {method_name} failed: {str(e)}")
                                continue
                    else:
                        print("Could not generate visualization: No suitable method found in graph object")
                else:
                    print("Could not generate visualization: Graph object not accessible")
    except Exception as e:
        print(f"Error generating visualization: {str(e)}")
    
    return False


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