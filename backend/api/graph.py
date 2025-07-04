from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_existing_user_id, zep_manager
from logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/graph")
async def get_graph(user_id: str = Depends(get_existing_user_id)):
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    data = await zep_manager.get_knowledge_graph(user_id)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge graph")

    return data
