"""
Graph builder module that constructs the LangGraph for the conversation flow.
"""
from langgraph.graph import StateGraph, END
from nodes.base import ChatState, logger

# Import all node functions
from nodes.initializer_node import initializer_node
from nodes.router_node import router_node
from nodes.search_optimizer_node import search_prompt_optimizer_node
from nodes.analysis_refiner_node import analysis_task_refiner_node
from nodes.search_node import search_node
from nodes.analyzer_node import analyzer_node
from nodes.integrator_node import integrator_node
from nodes.response_renderer_node import response_renderer_node


def create_chat_graph():
    """Create a LangGraph graph for orchestrating the flow of the interaction."""
    
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
            "chat": "integrator" 
        }
    )
    
    # Connect the search optimization to search
    builder.add_edge("search_prompt_optimizer", "search")
    builder.add_edge("search", "integrator")
    
    # Connect the analysis refiner to analyzer
    builder.add_edge("analysis_task_refiner", "analyzer")
    builder.add_edge("analyzer", "integrator")
    
    # Connect the integrator to the response renderer
    builder.add_edge("integrator", "response_renderer")
    
    # End the graph after rendering the response
    builder.add_edge("response_renderer", END)
    
    # Compile the graph
    graph = builder.compile()

    return graph


# Create a singleton instance of the graph
chat_graph = create_chat_graph()


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


# Automatically generate visualization whenever this module is run directly
if __name__ == "__main__":
    visualize_graph() 