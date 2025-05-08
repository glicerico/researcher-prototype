#!/usr/bin/env python

import os
import sys
import json
from pathlib import Path
import argparse
import re
import subprocess

# Add the current directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def extract_graph_from_source():
    """Extract graph structure by analyzing the source code file."""
    try:
        # Determine the path to graph.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        graph_file = os.path.join(script_dir, "graph.py")
        
        if not os.path.exists(graph_file):
            print(f"Could not find graph.py at {graph_file}")
            return None
        
        # Read the file
        with open(graph_file, 'r') as f:
            content = f.read()
        
        # Extract nodes using regex
        nodes = []
        node_pattern = r'builder\.add_node\(["\'](\w+)["\'],\s*\w+\)'
        for match in re.finditer(node_pattern, content):
            node_id = match.group(1)
            nodes.append({"id": node_id})
        
        # Extract regular edges
        edges = []
        edge_pattern = r'builder\.add_edge\(["\'](\w+)["\'],\s*["\']((?:\w+)|(?:END))["\']\)'
        for match in re.finditer(edge_pattern, content):
            source = match.group(1)
            target = match.group(2)
            edges.append({"source": source, "target": target})
        
        # Extract conditional edges
        conditional_pattern = r'builder\.add_conditional_edges\(["\'](\w+)["\'],\s*\w+,\s*{([^}]+)}\)'
        for match in re.finditer(conditional_pattern, content):
            source = match.group(1)
            conditions_text = match.group(2)
            
            # Parse the condition dictionary
            condition_pattern = r'["\']([\w-]+)["\']\s*:\s*["\']([\w-]+)["\']'
            for cond_match in re.finditer(condition_pattern, conditions_text):
                condition = cond_match.group(1)
                target = cond_match.group(2)
                edges.append({"source": source, "target": target, "condition": condition})
        
        # Create a graph dict manually
        if nodes and edges:
            return {"nodes": nodes, "edges": edges}
        else:
            # Provide a static fallback if parsing fails
            return {
                "nodes": [
                    {"id": "orchestrator"},
                    {"id": "router"},
                    {"id": "chat"},
                    {"id": "search"},
                    {"id": "analyzer"}
                ],
                "edges": [
                    {"source": "orchestrator", "target": "router"},
                    {"source": "router", "target": "chat", "condition": "chat"},
                    {"source": "router", "target": "search", "condition": "search"},
                    {"source": "router", "target": "analyzer", "condition": "analyzer"},
                    {"source": "chat", "target": "END"},
                    {"source": "search", "target": "END"},
                    {"source": "analyzer", "target": "END"}
                ]
            }
    except Exception as e:
        print(f"Error while parsing graph.py: {str(e)}")
        return None

def generate_dot_file(graph_dict, dot_file):
    """Generate a DOT file from the graph dictionary."""
    with open(dot_file, 'w') as f:
        f.write("digraph LangGraph {\n")
        f.write("    rankdir=TB;\n")
        f.write("    node [shape=box, style=filled, fontname=\"Arial\"];\n")
        
        # Define node styles
        f.write("    orchestrator [label=\"🔄 orchestrator\", fillcolor=\"#f9d5e5\"];\n")
        f.write("    router [label=\"🔀 router\", fillcolor=\"#eeeeee\"];\n")
        f.write("    chat [label=\"💬 chat\", fillcolor=\"#d5f9e8\"];\n")
        f.write("    search [label=\"🔍 search\", fillcolor=\"#e5f9d5\"];\n")
        f.write("    analyzer [label=\"📊 analyzer\", fillcolor=\"#d5e5f9\"];\n")
        f.write("    END [label=\"END\", shape=oval, fillcolor=\"#f5f5f5\"];\n")
        
        # Add edges
        for edge in graph_dict.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            condition = edge.get("condition")
            
            if condition:
                # For conditional edges, add a label
                f.write(f"    {source} -> {target} [label=\" {condition} \"];\n")
            else:
                f.write(f"    {source} -> {target};\n")
        
        f.write("}\n")

def visualize_graph(output_file=None, direct_parse=False):
    """
    Visualize the LangGraph topology using Graphviz.
    
    Args:
        output_file: Path to save the PNG output, defaults to graph.png
        direct_parse: Whether to bypass importing the graph module and parse from source
    """
    try:
        # Try to get the graph structure
        graph_dict = None
        methods_tried = []
        
        # If direct_parse is specified, skip trying to import the graph module
        if direct_parse:
            print("Using direct source code parsing (bypassing module import)...")
            methods_tried.append("direct source code parsing")
            graph_dict = extract_graph_from_source()
        else:
            # Try importing and using the chat_graph module
            try:
                from graph import chat_graph
            except ModuleNotFoundError as e:
                module_name = str(e).split("'")[1]
                print(f"Error: Could not import module '{module_name}'")
                print("\nPossible solutions:")
                print("1. Make sure you've activated the virtual environment:")
                print("   source backend/venv/bin/activate")
                print("2. Try using the --direct-parse option to bypass module import:")
                print("   ./visualize_graph.sh --direct-parse")
                print("3. Install the required dependencies:")
                print("   pip install -r backend/requirements.txt")
                sys.exit(1)
                
            # Method 1: Try the newer method (get_graph_json)
            try:
                methods_tried.append("get_graph_json()")
                graph_schema = chat_graph.get_graph_json()
                graph_dict = json.loads(graph_schema)
            except AttributeError:
                pass
            
            # Method 2: Try accessing internal properties directly
            if not graph_dict:
                try:
                    methods_tried.append("internal graph properties")
                    if hasattr(chat_graph, 'graph'):
                        # Access the internal graph object (works for some versions)
                        graph = chat_graph.graph
                        
                        # Try to extract nodes and edges from the internal representation
                        nodes = []
                        edges = []
                        
                        # Extract nodes (adapting to available properties)
                        if hasattr(graph, 'nodes'):
                            for node_id in graph.nodes:
                                nodes.append({"id": node_id})
                        
                        # Extract edges (adapting to available properties)
                        if hasattr(graph, 'edges'):
                            for source, targets in graph.edges.items():
                                for target_info in targets:
                                    if isinstance(target_info, dict):
                                        # New format with conditions
                                        target = target_info.get('target')
                                        condition = target_info.get('condition')
                                        if target:
                                            edge = {"source": source, "target": target}
                                            if condition:
                                                edge["condition"] = condition
                                            edges.append(edge)
                                    elif isinstance(target_info, str):
                                        # Simple format
                                        edges.append({"source": source, "target": target_info})
                        
                        # Create a graph dict manually
                        if nodes and edges:
                            graph_dict = {"nodes": nodes, "edges": edges}
                except Exception:
                    pass
            
            # Method 3: Try to extract the graph from source code
            if not graph_dict:
                methods_tried.append("source code analysis")
                graph_dict = extract_graph_from_source()
        
        if not graph_dict:
            methods_tried_str = ", ".join(methods_tried)
            raise ValueError(f"Could not extract graph structure with any available method. Tried: {methods_tried_str}")
        
        # Default output file name
        if output_file is None:
            output_file = "graph.png"
        
        # Create temp DOT file
        dot_file = output_file.replace('.png', '.dot')
        generate_dot_file(graph_dict, dot_file)
        
        # Generate PNG using graphviz
        try:
            # Check if graphviz is installed
            try:
                subprocess.run(["dot", "-V"], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Error: Graphviz not found. Please install it with:")
                print("   sudo apt-get install graphviz")
                sys.exit(1)
            
            # Run the dot command to generate PNG
            subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
            print(f"Generated graph visualization: {output_file}")
            
            # Cleanup temporary dot file
            os.remove(dot_file)
            
        except subprocess.CalledProcessError as e:
            print(f"Error running Graphviz: {e}")
            print(f"Please check if Graphviz is installed correctly.")
            print(f"DOT file saved at: {dot_file}")
            sys.exit(1)
            
    except AttributeError as e:
        print(f"Error accessing graph structure: {str(e)}")
        print("\nThis may be due to using an incompatible version of langgraph.")
        print("Options to fix this issue:")
        print("1. Update langgraph: pip install -U langgraph")
        print("2. Check if 'langchain_community' is installed: pip install langchain-community")
        print("3. Ensure you're using a compatible version: pip install 'langgraph>=0.0.15'")
        print("4. Use the --direct-parse option to bypass module import:")
        print("   ./visualize_graph.sh --direct-parse")
        sys.exit(1)
    except Exception as e:
        print(f"Error visualizing graph: {str(e)}")
        print("Try using the --direct-parse option to bypass module import:")
        print("   ./visualize_graph.sh --direct-parse")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize the LangGraph topology using Graphviz")
    parser.add_argument(
        "--output", "-o", 
        help="Output PNG file path (defaults to graph.png)"
    )
    parser.add_argument(
        "--direct-parse", "-d",
        action="store_true",
        help="Parse graph structure directly from source code (bypasses module import)"
    )
    
    args = parser.parse_args()
    
    # Check if output file is provided, otherwise use default
    output_file = args.output or "graph.png"
    
    visualize_graph(output_file=output_file, direct_parse=args.direct_parse) 