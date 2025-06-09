from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException

from models import PersonalityConfig, UserSummary, UserProfile
from dependencies import (
    get_existing_user_id,
    get_or_create_user_id,
    user_manager,
    generate_display_name_from_user_id,
)
from logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/user", response_model=UserProfile)
async def get_current_user(user_id: Optional[str] = Depends(get_existing_user_id)):
    if not user_id:
        raise HTTPException(status_code=404, detail="No user ID provided or user not found")

    user_data = user_manager.get_user(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfile(
        user_id=user_data["user_id"],
        created_at=user_data["created_at"],
        metadata=user_data.get("metadata", {}),
        personality=PersonalityConfig(**user_data.get("personality", {})),
    )


@router.put("/user/personality")
async def update_user_personality(personality: PersonalityConfig, user_id: str = Depends(get_or_create_user_id)):
    success = user_manager.update_personality(user_id, personality.model_dump())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update personality")

    return {"success": True, "message": "Personality updated successfully"}


@router.put("/user/display-name")
async def update_user_display_name(display_name: str, user_id: str = Depends(get_or_create_user_id)):
    success = user_manager.update_user(user_id, {"metadata": {"display_name": display_name}})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update display name")

    return {"success": True, "message": "Display name updated successfully"}


@router.get("/users", response_model=List[UserSummary])
async def list_users():
    user_ids = user_manager.list_users()
    user_summaries = []

    for user_id in user_ids:
        user_data = user_manager.get_user(user_id)
        if user_data:
            personality = user_data.get("personality", {})
            personality_config = PersonalityConfig(
                style=personality.get("style", "helpful"),
                tone=personality.get("tone", "friendly"),
                additional_traits=personality.get("additional_traits", {}),
            )

            metadata = user_data.get("metadata", {})
            display_name = metadata.get("display_name", generate_display_name_from_user_id(user_id))

            user_summaries.append(
                UserSummary(
                    user_id=user_id,
                    created_at=user_data.get("created_at", 0),
                    personality=personality_config,
                    display_name=display_name,
                )
            )

    user_summaries.sort(key=lambda x: x.created_at, reverse=True)

    return user_summaries


@router.post("/users")
async def create_user(display_name: Optional[str] = None):
    metadata = {}
    if display_name:
        metadata["display_name"] = display_name

    user_id = user_manager.create_user(metadata)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return {
        "success": True,
        "user_id": user_id,
        "display_name": display_name or generate_display_name_from_user_id(user_id),
    }
