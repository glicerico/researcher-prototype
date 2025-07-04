from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_existing_user_id, zep_manager
from logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/zep/graph")
async def get_user_graph(user_id: str = Depends(get_existing_user_id), limit: int = 50):
    """Return the user's knowledge graph from Zep."""
    if not zep_manager.is_enabled():
        return {"enabled": False, "nodes": [], "edges": []}

    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        nodes = await zep_manager.client.graph.node.get_by_user_id(user_id, limit=limit)
        edges = await zep_manager.client.graph.edge.get_by_user_id(user_id, limit=limit)
        node_dicts = [n.dict() for n in nodes]
        edge_dicts = [e.dict() for e in edges]
        return {"enabled": True, "nodes": node_dicts, "edges": edge_dicts}
    except Exception as e:
        logger.error(f"Failed to fetch knowledge graph: {e}")
        raise HTTPException(status_code=500, detail="Error fetching knowledge graph")
