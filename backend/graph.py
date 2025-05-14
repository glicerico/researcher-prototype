"""
Re-export the graph components from graph_builder.py for backwards compatibility.
"""
from graph_builder import chat_graph, create_chat_graph, visualize_graph

# Automatically generate visualization whenever this module is run directly
if __name__ == "__main__":
    visualize_graph() 