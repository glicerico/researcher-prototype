"""
Graph API endpoints for managing knowledge graphs.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from dependencies import get_or_create_user_id
from storage.zep_manager import ZepManager
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class GraphRequest(BaseModel):
    """Request model for graph data."""
    type: str  # "user" or "group"
    id: str    # user_id or group_id


class GraphResponse(BaseModel):
    """Response model for graph data."""
    triplets: List[Dict[str, Any]]


@router.post("/api/graph/fetch")
async def fetch_graph_data(
    request: GraphRequest,
    current_user: str = Depends(get_or_create_user_id)
) -> GraphResponse:
    """
    Fetch graph data from Zep for visualization.
    
    Args:
        request: GraphRequest containing type and id
        current_user: The current user ID from authentication
        
    Returns:
        GraphResponse containing triplets for visualization
    """
    try:
        # Log the request
        logger.info(f"Fetching graph data for {request.type}: {request.id}")
        
        # Initialize ZepManager
        zep_manager = ZepManager()
        
        if not zep_manager.is_enabled():
            logger.warning("ZepManager is not enabled")
            return GraphResponse(triplets=[])
        
        # For user graphs, validate that the user is requesting their own data
        # or has appropriate permissions (could be extended for admin access)
        if request.type == "user" and request.id != current_user:
            logger.warning(f"User {current_user} attempted to access graph for user {request.id}")
            raise HTTPException(
                status_code=403,
                detail="You can only view your own knowledge graph"
            )
        
        # Currently only support user graphs (groups not implemented yet)
        if request.type != "user":
            raise HTTPException(
                status_code=400,
                detail="Only user graphs are currently supported"
            )
        
        # Fetch all nodes and edges for the user using the proper API methods
        logger.debug(f"Fetching nodes and edges for user {request.id}")
        
        # Use Promise.all equivalent - run both fetches concurrently
        import asyncio
        nodes_task = zep_manager.get_all_nodes_by_user_id(request.id)
        edges_task = zep_manager.get_all_edges_by_user_id(request.id)
        
        nodes, edges = await asyncio.gather(nodes_task, edges_task)
        
        logger.debug(f"Retrieved {len(nodes)} nodes and {len(edges)} edges for user {request.id}")
        
        # Check if we got any data
        if not nodes and not edges:
            logger.info(f"No graph data found for user {request.id}")
            return GraphResponse(triplets=[])
        
        # Create triplets from nodes and edges
        triplets = zep_manager.create_triplets(edges, nodes)
        
        logger.info(f"Successfully created {len(triplets)} triplets for user {request.id}")
        
        return GraphResponse(triplets=triplets)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching graph for {request.type} {request.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph data: {str(e)}") 