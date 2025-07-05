"""
Graph visualization API endpoints for Zep Knowledge Graph.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from dependencies import get_or_create_user_id
from storage.zep_manager import ZepManager
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])

class GraphRequest(BaseModel):
    """Request model for graph data."""
    type: str  # "user" or "group"
    id: str    # user_id or group_id

class GraphNode(BaseModel):
    """Node in the knowledge graph."""
    uuid: str
    name: str
    summary: Optional[str] = None
    labels: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class GraphEdge(BaseModel):
    """Edge in the knowledge graph."""
    uuid: str
    source_node_uuid: str
    target_node_uuid: str
    type: str
    name: str
    fact: Optional[str] = None
    episodes: Optional[List[str]] = None
    created_at: str
    updated_at: str
    valid_at: Optional[str] = None
    expired_at: Optional[str] = None
    invalid_at: Optional[str] = None

class GraphTriplet(BaseModel):
    """A triplet representing a relationship in the knowledge graph."""
    sourceNode: GraphNode
    edge: GraphEdge
    targetNode: GraphNode

class GraphResponse(BaseModel):
    """Response model for graph data."""
    triplets: List[GraphTriplet]
    node_count: int
    edge_count: int


@router.post("/fetch", response_model=GraphResponse)
async def fetch_graph_data(
    request: GraphRequest,
    current_user_id: str = Depends(get_or_create_user_id)
):
    """
    Fetch graph data from Zep for visualization.
    
    Args:
        request: GraphRequest containing type and id
        current_user_id: The current user ID from auth
        
    Returns:
        GraphResponse containing triplets for visualization
    """
    try:
        logger.info(f"📊 Fetching graph data for {request.type}: {request.id}")
        
        # Initialize Zep manager
        zep_manager = ZepManager()
        
        if not zep_manager.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Zep service is not available"
            )
        
        # For user graphs, validate that the user is requesting their own data
        # or has appropriate permissions (could be extended for admin access)
        if request.type == "user" and request.id != current_user_id:
            logger.warning(f"User {current_user_id} attempted to access graph for user {request.id}")
            raise HTTPException(
                status_code=403,
                detail="You can only view your own knowledge graph"
            )
        
        # Fetch nodes and edges from Zep
        nodes = []
        edges = []
        
        try:
            # Try to fetch all graph data using general search
            if request.type == "user":
                search_results = await zep_manager.client.graph.search(
                    user_id=request.id,
                    query="*",  # Wildcard query to get all data
                    limit=50
                )
            else:  # group
                search_results = await zep_manager.client.graph.search(
                    group_id=request.id,
                    query="*",  # Wildcard query to get all data
                    limit=50
                )
            
            # Since we don't know the exact structure, let's handle both cases
            # The search might return mixed results or have different structure
            if search_results:
                # Try to distinguish between nodes and edges based on attributes
                for item in search_results:
                    if hasattr(item, 'source_node_uuid') and hasattr(item, 'target_node_uuid'):
                        # This looks like an edge
                        edges.append(item)
                    elif hasattr(item, 'uuid') and hasattr(item, 'name'):
                        # This looks like a node
                        nodes.append(item)
            
            logger.info(f"📊 Fetched {len(nodes)} nodes and {len(edges)} edges")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to fetch graph data from Zep: {error_msg}")
            
            # Check if this is a "user not found" error (404 from Zep)
            if "404" in error_msg and "not found" in error_msg.lower():
                logger.info(f"📊 User {request.id} not found in Zep - returning empty graph")
                # Return empty graph instead of error for users that don't exist in Zep yet
                return GraphResponse(
                    triplets=[],
                    node_count=0,
                    edge_count=0
                )
            else:
                # For other errors, still raise the exception
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch graph data: {error_msg}"
                )
        
        # Convert to triplets using the same logic as the frontend
        triplets = create_triplets(edges, nodes)
        
        return GraphResponse(
            triplets=triplets,
            node_count=len(nodes),
            edge_count=len(edges)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in fetch_graph_data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching graph data"
        )


def create_triplets(edges: List[Any], nodes: List[Any]) -> List[GraphTriplet]:
    """
    Create triplets from edges and nodes.
    This mirrors the logic in the frontend graph.ts file.
    
    Args:
        edges: List of edge objects from Zep
        nodes: List of node objects from Zep
        
    Returns:
        List of GraphTriplet objects
    """
    # Create a map of node UUIDs for quick lookup
    node_map = {node.uuid: node for node in nodes}
    
    # Track connected nodes
    connected_node_ids = set()
    
    # Create triplets from edges
    triplets = []
    
    for edge in edges:
        source_node = node_map.get(edge.source_node_uuid)
        target_node = node_map.get(edge.target_node_uuid)
        
        if source_node and target_node:
            connected_node_ids.add(source_node.uuid)
            connected_node_ids.add(target_node.uuid)
            
            # Convert Zep objects to our models
            triplet = GraphTriplet(
                sourceNode=GraphNode(
                    uuid=source_node.uuid,
                    name=source_node.name,
                    summary=getattr(source_node, 'summary', None),
                    labels=getattr(source_node, 'labels', None),
                    attributes=getattr(source_node, 'attributes', None),
                    created_at=str(source_node.created_at),
                    updated_at=str(source_node.updated_at)
                ),
                edge=GraphEdge(
                    uuid=edge.uuid,
                    source_node_uuid=edge.source_node_uuid,
                    target_node_uuid=edge.target_node_uuid,
                    type=edge.type,
                    name=edge.name,
                    fact=getattr(edge, 'fact', None),
                    episodes=getattr(edge, 'episodes', None),
                    created_at=str(edge.created_at),
                    updated_at=str(edge.updated_at),
                    valid_at=str(edge.valid_at) if hasattr(edge, 'valid_at') and edge.valid_at else None,
                    expired_at=str(edge.expired_at) if hasattr(edge, 'expired_at') and edge.expired_at else None,
                    invalid_at=str(edge.invalid_at) if hasattr(edge, 'invalid_at') and edge.invalid_at else None
                ),
                targetNode=GraphNode(
                    uuid=target_node.uuid,
                    name=target_node.name,
                    summary=getattr(target_node, 'summary', None),
                    labels=getattr(target_node, 'labels', None),
                    attributes=getattr(target_node, 'attributes', None),
                    created_at=str(target_node.created_at),
                    updated_at=str(target_node.updated_at)
                )
            )
            triplets.append(triplet)
    
    # Find isolated nodes (nodes that don't appear in any edge)
    isolated_nodes = [node for node in nodes if node.uuid not in connected_node_ids]
    
    # Create special triplets for isolated nodes
    for node in isolated_nodes:
        # Create a virtual edge for isolated nodes
        virtual_edge = GraphEdge(
            uuid=f"isolated-node-{node.uuid}",
            source_node_uuid=node.uuid,
            target_node_uuid=node.uuid,
            type="_isolated_node_",
            name="",
            created_at=str(node.created_at),
            updated_at=str(node.updated_at)
        )
        
        node_model = GraphNode(
            uuid=node.uuid,
            name=node.name,
            summary=getattr(node, 'summary', None),
            labels=getattr(node, 'labels', None),
            attributes=getattr(node, 'attributes', None),
            created_at=str(node.created_at),
            updated_at=str(node.updated_at)
        )
        
        triplet = GraphTriplet(
            sourceNode=node_model,
            edge=virtual_edge,
            targetNode=node_model
        )
        triplets.append(triplet)
    
    return triplets


@router.get("/test/{user_id}")
async def test_graph_connectivity(user_id: str):
    """Test endpoint to verify graph connectivity for a user."""
    try:
        zep_manager = ZepManager()
        
        if not zep_manager.is_enabled():
            return {"status": "error", "message": "Zep is not enabled"}
        
        # Quick test to see if we can access graph data
        try:
            search_results = await zep_manager.client.graph.search(
                user_id=user_id,
                query="*",  # Wildcard query to get all data
                limit=1
            )
            
            # Count nodes and edges
            nodes = []
            edges = []
            if search_results:
                for item in search_results:
                    if hasattr(item, 'source_node_uuid') and hasattr(item, 'target_node_uuid'):
                        edges.append(item)
                    elif hasattr(item, 'uuid') and hasattr(item, 'name'):
                        nodes.append(item)
            
            return {
                "status": "success",
                "has_nodes": len(nodes) > 0 if nodes else False,
                "has_edges": len(edges) > 0 if edges else False,
                "message": "Graph connectivity test successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to access graph data: {str(e)}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}"
        } 