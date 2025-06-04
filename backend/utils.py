"""
Utility functions used across the application.
"""
import time
from typing import List, Optional

def get_current_datetime_str() -> str:
    """Return the current date and time as a formatted string."""
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())

def get_last_user_message(messages: List["BaseMessage"]) -> Optional[str]:
    """
    Get the content of the last user message from a list of messages.
    
    Args:
        messages: List of BaseMessage objects (typically from state["messages"])
        
    Returns:
        The content of the last HumanMessage, or None if no HumanMessage found
    """
    # Import here to avoid circular imports
    from langchain_core.messages import HumanMessage
    
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None

def visualize_langgraph(graph, output_file: str = "graph.png", graph_name: str = "LangGraph") -> bool:
    """
    Generate a PNG visualization of a LangGraph using built-in functionality.
    
    Args:
        graph: The compiled LangGraph object to visualize
        output_file: Path where to save the PNG file
        graph_name: Name of the graph for logging purposes
    
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
        
        print(f"Generating visualization of {graph_name}...")
        
        # Try using the built-in visualization methods
        try:
            # Method 1: Try using draw_png if available (most direct method)
            png_data = graph.get_graph().draw_png()
            with open(output_file, 'wb') as f:
                f.write(png_data)
            print(f"{graph_name} visualization saved to {output_file}")
            return True
        except (AttributeError, ImportError) as e:
            print(f"draw_png method not available: {str(e)}")
            
            # Method 2: Fall back to DOT format
            try:
                dot_data = graph.get_graph().draw_graphviz()
                with open(dot_file, 'w') as f:
                    f.write(dot_data)
                # Use graphviz to convert to PNG
                subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
                print(f"{graph_name} visualization saved to {output_file}")
                # Clean up the DOT file
                os.remove(dot_file)
                return True
            except (AttributeError, ImportError) as e:
                print(f"draw_graphviz method not available: {str(e)}")
                
                # Method 3: If all else fails, use any available method
                if hasattr(graph, 'get_graph'):
                    graph_obj = graph.get_graph()
                    for method_name in ['draw_png', 'draw_graphviz', 'to_dot']:
                        if hasattr(graph_obj, method_name):
                            try:
                                method = getattr(graph_obj, method_name)
                                result = method()
                                if method_name == 'draw_png':
                                    with open(output_file, 'wb') as f:
                                        f.write(result)
                                    print(f"{graph_name} visualization saved to {output_file} using {method_name}")
                                    return True
                                elif method_name in ['draw_graphviz', 'to_dot']:
                                    with open(dot_file, 'w') as f:
                                        f.write(result)
                                    subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
                                    print(f"{graph_name} visualization saved to {output_file} using {method_name}")
                                    os.remove(dot_file)
                                    return True
                            except Exception as e:
                                print(f"Method {method_name} failed: {str(e)}")
                                continue
                    else:
                        print(f"Could not generate {graph_name} visualization: No suitable method found in graph object")
                else:
                    print(f"Could not generate {graph_name} visualization: Graph object not accessible")
    except Exception as e:
        print(f"Error generating {graph_name} visualization: {str(e)}")
    
    return False 