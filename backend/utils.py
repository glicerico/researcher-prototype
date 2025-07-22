"""
Utility functions used across the application.
"""
import time
from typing import List, Optional, Dict, Any

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

def get_node_prompt_mapping() -> Dict[str, Dict[str, Any]]:
    """
    Get mapping of graph nodes to their associated prompts and metadata.
    
    Returns:
        Dictionary mapping node names to prompt information
    """
    return {
        # Main Chat Graph nodes
        "initializer": {
            "prompt": None,
            "category": "System",
            "description": "Sets up user state and session",
            "color": "#E8F4FD"
        },
        "router": {
            "prompt": "ROUTER_SYSTEM_PROMPT",
            "category": "Router",
            "description": "Determines conversation flow path",
            "color": "#FFE6E6"
        },
        "search_prompt_optimizer": {
            "prompt": "SEARCH_OPTIMIZER_SYSTEM_PROMPT",
            "category": "Search",
            "description": "Optimizes search queries",
            "color": "#E6F3FF"
        },
        "analysis_task_refiner": {
            "prompt": "ANALYSIS_REFINER_SYSTEM_PROMPT",
            "category": "Analysis",
            "description": "Refines analysis tasks",
            "color": "#E6FFE6"
        },
        "search": {
            "prompt": "PERPLEXITY_SYSTEM_PROMPT",
            "category": "Search",
            "description": "Performs web search",
            "color": "#E6F3FF"
        },
        "analyzer": {
            "prompt": None,
            "category": "Analysis",
            "description": "Analyzes data and problems",
            "color": "#E6FFE6"
        },
        "integrator": {
            "prompt": "INTEGRATOR_SYSTEM_PROMPT",
            "category": "Integrator",
            "description": "Integrates all information",
            "color": "#F0E6FF"
        },
        "response_renderer": {
            "prompt": "RESPONSE_RENDERER_SYSTEM_PROMPT",
            "category": "Response",
            "description": "Formats final response",
            "color": "#FFF0E6"
        },
        
        # Research Graph nodes
        "research_initializer": {
            "prompt": None,
            "category": "Research",
            "description": "Initializes research workflow",
            "color": "#F0F8E6"
        },
        "research_query_generator": {
            "prompt": "RESEARCH_QUERY_GENERATION_PROMPT",
            "category": "Research",
            "description": "Generates research queries",
            "color": "#F0F8E6"
        },
        "research_quality_assessor": {
            "prompt": "RESEARCH_FINDINGS_QUALITY_ASSESSMENT_PROMPT",
            "category": "Research",
            "description": "Assesses research quality",
            "color": "#F0F8E6"
        },
        "research_deduplication": {
            "prompt": "RESEARCH_FINDINGS_DEDUPLICATION_PROMPT",
            "category": "Research",
            "description": "Checks for duplicates",
            "color": "#F0F8E6"
        },
        "research_storage": {
            "prompt": None,
            "category": "Research",
            "description": "Stores research findings",
            "color": "#F0F8E6"
        }
    }

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

def visualize_langgraph_with_prompts(graph, output_file: str = "graph.png", graph_name: str = "LangGraph") -> bool:
    """
    Generate an enhanced PNG visualization of a LangGraph with prompt annotations.
    
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
        
        # Get node-prompt mapping
        node_mapping = get_node_prompt_mapping()
        
        print(f"Generating enhanced visualization of {graph_name} with prompt annotations...")
        
        # Try to get DOT representation and enhance it
        try:
            # Get the base DOT representation
            dot_data = graph.get_graph().draw_graphviz()
            
            # Enhance the DOT data with prompt information
            enhanced_dot = enhance_dot_with_prompts(dot_data, node_mapping)
            
            # Save enhanced DOT file
            dot_file = output_file.replace('.png', '.dot')
            with open(dot_file, 'w') as f:
                f.write(enhanced_dot)
            
            # Convert to PNG
            subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
            print(f"Enhanced {graph_name} visualization saved to {output_file}")
            
            # Clean up the DOT file
            os.remove(dot_file)
            return True
            
        except Exception as e:
            print(f"Enhanced visualization failed: {str(e)}, falling back to basic visualization")
            return visualize_langgraph(graph, output_file, graph_name)
            
    except Exception as e:
        print(f"Error generating enhanced {graph_name} visualization: {str(e)}")
    
    return False

def enhance_dot_with_prompts(dot_data: str, node_mapping: Dict[str, Dict[str, Any]]) -> str:
    """
    Enhance DOT graph data with prompt information and styling.
    
    Args:
        dot_data: Original DOT graph data
        node_mapping: Mapping of nodes to prompt information
    
    Returns:
        Enhanced DOT data with prompt annotations
    """
    lines = dot_data.split('\n')
    enhanced_lines = []
    
    for line in lines:
        # Check if this line defines a node
        if ' [label=' in line and not '->' in line:
            # Extract node name
            node_name = line.split(' [')[0].strip().strip('"')
            
            if node_name in node_mapping:
                node_info = node_mapping[node_name]
                prompt_name = node_info.get('prompt', 'No Prompt')
                category = node_info.get('category', 'System')
                description = node_info.get('description', '')
                color = node_info.get('color', '#F0F0F0')
                
                # Create enhanced label with prompt information
                if prompt_name and prompt_name != 'No Prompt':
                    enhanced_label = f"{node_name}\\n[{category}]\\n{prompt_name}\\n{description}"
                else:
                    enhanced_label = f"{node_name}\\n[{category}]\\n{description}"
                
                # Replace the line with enhanced styling
                enhanced_line = f'    "{node_name}" [label="{enhanced_label}", style=filled, fillcolor="{color}", shape=box, fontsize=10];'
                enhanced_lines.append(enhanced_line)
            else:
                enhanced_lines.append(line)
        else:
            enhanced_lines.append(line)
    
    return '\n'.join(enhanced_lines)

def get_graph_flow_data(graph_type: str = "main") -> Dict[str, Any]:
    """
    Get structured flow data for a graph including nodes, edges, and prompt information.
    
    Args:
        graph_type: Type of graph ("main" or "research")
    
    Returns:
        Dictionary with graph flow information
    """
    node_mapping = get_node_prompt_mapping()
    
    if graph_type == "main":
        # Main chat graph flow
        nodes = [
            {"id": "initializer", "type": "start"},
            {"id": "router", "type": "decision"},
            {"id": "search_prompt_optimizer", "type": "process"},
            {"id": "analysis_task_refiner", "type": "process"},
            {"id": "search", "type": "process"},
            {"id": "analyzer", "type": "process"},
            {"id": "integrator", "type": "process"},
            {"id": "response_renderer", "type": "end"}
        ]
        
        edges = [
            {"from": "initializer", "to": "router"},
            {"from": "router", "to": "search_prompt_optimizer", "condition": "search"},
            {"from": "router", "to": "analysis_task_refiner", "condition": "analyzer"},
            {"from": "router", "to": "integrator", "condition": "chat"},
            {"from": "search_prompt_optimizer", "to": "search"},
            {"from": "search", "to": "integrator"},
            {"from": "analysis_task_refiner", "to": "analyzer"},
            {"from": "analyzer", "to": "integrator"},
            {"from": "integrator", "to": "response_renderer"}
        ]
        
    else:  # research graph
        nodes = [
            {"id": "research_initializer", "type": "start"},
            {"id": "research_query_generator", "type": "process"},
            {"id": "search", "type": "process"},
            {"id": "integrator", "type": "process"},
            {"id": "response_renderer", "type": "process"},
            {"id": "research_quality_assessor", "type": "process"},
            {"id": "research_deduplication", "type": "process"},
            {"id": "research_storage", "type": "end"}
        ]
        
        edges = [
            {"from": "research_initializer", "to": "research_query_generator"},
            {"from": "research_query_generator", "to": "search"},
            {"from": "search", "to": "integrator"},
            {"from": "integrator", "to": "response_renderer"},
            {"from": "response_renderer", "to": "research_quality_assessor"},
            {"from": "research_quality_assessor", "to": "research_deduplication"},
            {"from": "research_deduplication", "to": "research_storage"}
        ]
    
    # Enhance nodes with prompt information
    for node in nodes:
        node_id = node["id"]
        if node_id in node_mapping:
            node.update(node_mapping[node_id])
    
    return {
        "type": graph_type,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges)
    } 