"""
Flow analyzer service for generating and managing LangGraph flow visualizations.
"""
import os
import json
from typing import Dict, Any, List, Optional
from utils import (
    visualize_langgraph_with_prompts, 
    get_graph_flow_data,
    get_node_prompt_mapping
)


class FlowAnalyzer:
    """Service for analyzing and visualizing LangGraph flows with prompt annotations."""
    
    def __init__(self):
        """Initialize the flow analyzer."""
        self.diagrams_dir = "static/diagrams"
        self.ensure_diagrams_directory()
    
    def ensure_diagrams_directory(self):
        """Ensure the diagrams directory exists."""
        os.makedirs(self.diagrams_dir, exist_ok=True)
    
    def generate_flow_diagrams(self, force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Generate flow diagrams for both main chat and research graphs.
        Uses cached diagrams if they exist unless force_regenerate is True.
        
        Args:
            force_regenerate: If True, regenerate diagrams even if they exist
        
        Returns:
            Dictionary with generation results and file paths
        """
        results = {
            "success": True,
            "diagrams": {},
            "errors": []
        }
        
        try:
            # Define diagram paths
            main_diagram_path = os.path.join(self.diagrams_dir, "main_chat_flow.png")
            research_diagram_path = os.path.join(self.diagrams_dir, "research_flow.png")
            
            # Check if diagrams already exist (unless forcing regeneration)
            if not force_regenerate and os.path.exists(main_diagram_path) and os.path.exists(research_diagram_path):
                # Use existing diagrams
                results["diagrams"]["main_chat"] = {
                    "path": main_diagram_path,
                    "url": "/static/diagrams/main_chat_flow.png",
                    "generated": False,  # Indicates using cached version
                    "cached": True
                }
                results["diagrams"]["research"] = {
                    "path": research_diagram_path,
                    "url": "/static/diagrams/research_flow.png", 
                    "generated": False,  # Indicates using cached version
                    "cached": True
                }
                return results
            
            # Import graphs (only if we need to generate)
            from graph_builder import chat_graph
            from research_graph_builder import research_graph
            
            # Generate main chat flow diagram
            if force_regenerate or not os.path.exists(main_diagram_path):
                main_success = visualize_langgraph_with_prompts(
                    chat_graph, 
                    main_diagram_path, 
                    "Main Chat Flow"
                )
                
                if main_success:
                    results["diagrams"]["main_chat"] = {
                        "path": main_diagram_path,
                        "url": "/static/diagrams/main_chat_flow.png",
                        "generated": True
                    }
                else:
                    results["errors"].append("Failed to generate main chat flow diagram")
            else:
                # Use existing diagram
                results["diagrams"]["main_chat"] = {
                    "path": main_diagram_path,
                    "url": "/static/diagrams/main_chat_flow.png",
                    "generated": False,
                    "cached": True
                }
            
            # Generate research flow diagram
            if force_regenerate or not os.path.exists(research_diagram_path):
                research_success = visualize_langgraph_with_prompts(
                    research_graph, 
                    research_diagram_path, 
                    "Research Flow"
                )
                
                if research_success:
                    results["diagrams"]["research"] = {
                        "path": research_diagram_path,
                        "url": "/static/diagrams/research_flow.png",
                        "generated": True
                    }
                else:
                    results["errors"].append("Failed to generate research flow diagram")
            else:
                # Use existing diagram
                results["diagrams"]["research"] = {
                    "path": research_diagram_path,
                    "url": "/static/diagrams/research_flow.png",
                    "generated": False,
                    "cached": True
                }
            
            # If any diagram failed, mark as partial success
            if results["errors"]:
                results["success"] = len(results["diagrams"]) > 0
                
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error generating diagrams: {str(e)}")
        
        return results
    
    def get_flow_data(self, graph_type: str = "main") -> Dict[str, Any]:
        """
        Get structured flow data for a specific graph type.
        
        Args:
            graph_type: Type of graph ("main" or "research")
        
        Returns:
            Dictionary with flow data including nodes, edges, and prompt information
        """
        try:
            return get_graph_flow_data(graph_type)
        except Exception as e:
            return {
                "error": f"Failed to get flow data: {str(e)}",
                "type": graph_type,
                "nodes": [],
                "edges": []
            }
    
    def get_node_prompt_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed prompt information for a specific node.
        
        Args:
            node_id: ID of the node
        
        Returns:
            Dictionary with node and prompt information, or None if not found
        """
        node_mapping = get_node_prompt_mapping()
        return node_mapping.get(node_id)
    
    def get_prompt_usage_map(self) -> Dict[str, List[str]]:
        """
        Get a mapping of prompts to the nodes that use them.
        
        Returns:
            Dictionary mapping prompt names to lists of node IDs
        """
        node_mapping = get_node_prompt_mapping()
        prompt_usage = {}
        
        for node_id, node_info in node_mapping.items():
            prompt_name = node_info.get('prompt')
            if prompt_name:
                if prompt_name not in prompt_usage:
                    prompt_usage[prompt_name] = []
                prompt_usage[prompt_name].append(node_id)
        
        return prompt_usage
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of all flows and their prompt usage.
        
        Returns:
            Dictionary with flow summary information
        """
        try:
            main_flow = self.get_flow_data("main")
            research_flow = self.get_flow_data("research")
            prompt_usage = self.get_prompt_usage_map()
            
            # Count nodes by category
            category_counts = {}
            all_nodes = main_flow.get("nodes", []) + research_flow.get("nodes", [])
            
            for node in all_nodes:
                category = node.get("category", "Unknown")
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                "flows": {
                    "main_chat": {
                        "node_count": main_flow.get("node_count", 0),
                        "edge_count": main_flow.get("edge_count", 0),
                        "type": "conditional"
                    },
                    "research": {
                        "node_count": research_flow.get("node_count", 0),
                        "edge_count": research_flow.get("edge_count", 0),
                        "type": "linear"
                    }
                },
                "prompt_usage": prompt_usage,
                "category_distribution": category_counts,
                "total_nodes": len(all_nodes),
                "total_prompts": len(prompt_usage)
            }
            
        except Exception as e:
            return {
                "error": f"Failed to generate flow summary: {str(e)}",
                "flows": {},
                "prompt_usage": {},
                "category_distribution": {}
            }
    
    def save_flow_metadata(self) -> bool:
        """
        Save flow metadata to JSON file for frontend consumption.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            metadata = {
                "main_chat_flow": self.get_flow_data("main"),
                "research_flow": self.get_flow_data("research"),
                "flow_summary": self.get_flow_summary(),
                "node_prompt_mapping": get_node_prompt_mapping(),
                "generated_at": __import__('time').time()
            }
            
            metadata_path = os.path.join(self.diagrams_dir, "flow_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving flow metadata: {str(e)}")
            return False


# Create singleton instance
flow_analyzer = FlowAnalyzer() 