from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException

from models import (
    PersonalityConfig, UserSummary, UserProfile, PreferencesConfig,
    EngagementAnalytics, PersonalizationHistory, PreferenceOverride
)
from dependencies import (
    get_existing_user_id,
    get_or_create_user_id,
    profile_manager,
    generate_display_name_from_user_id,
)
from storage.personalization_manager import PersonalizationManager
from logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Initialize PersonalizationManager (will be injected via dependencies later)
personalization_manager = None

def get_personalization_manager():
    """Get or create PersonalizationManager instance."""
    global personalization_manager
    if personalization_manager is None:
        from dependencies import storage_manager
        personalization_manager = PersonalizationManager(storage_manager, profile_manager)
    return personalization_manager


@router.get("/user", response_model=UserProfile)
async def get_current_user(user_id: Optional[str] = Depends(get_existing_user_id)):
    if not user_id:
        raise HTTPException(status_code=404, detail="No user ID provided or user not found")

    user_data = profile_manager.get_user(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Get preferences for complete profile
    preferences_data = profile_manager.get_preferences(user_id)
    preferences = PreferencesConfig(**preferences_data) if preferences_data else None

    return UserProfile(
        user_id=user_data["user_id"],
        created_at=user_data["created_at"],
        metadata=user_data.get("metadata", {}),
        personality=PersonalityConfig(**user_data.get("personality", {})),
        preferences=preferences
    )


@router.put("/user/personality")
async def update_user_personality(personality: PersonalityConfig, user_id: str = Depends(get_or_create_user_id)):
    success = profile_manager.update_personality(user_id, personality.model_dump())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update personality")

    return {"success": True, "message": "Personality updated successfully"}


@router.put("/user/display-name")
async def update_user_display_name(display_name: str, user_id: str = Depends(get_or_create_user_id)):
    success = profile_manager.update_user(user_id, {"metadata": {"display_name": display_name}})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update display name")

    return {"success": True, "message": "Display name updated successfully"}


@router.get("/users", response_model=List[UserSummary])
async def list_users():
    user_ids = profile_manager.list_users()
    user_summaries = []

    for user_id in user_ids:
        user_data = profile_manager.get_user(user_id)
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

    user_id = profile_manager.create_user(metadata)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Initialize personalization files for new user
    profile_manager.migrate_user_personalization_files(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "display_name": display_name or generate_display_name_from_user_id(user_id),
    }


@router.get("/user/preferences", response_model=PreferencesConfig)
async def get_user_preferences(user_id: str = Depends(get_or_create_user_id)):
    """Get user preferences."""
    try:
        logger.info(f"API: Getting preferences for user {user_id}")
        preferences_data = profile_manager.get_preferences(user_id)
        logger.debug(f"API: Retrieved preferences for user {user_id}: {list(preferences_data.keys())}")
        return PreferencesConfig(**preferences_data)
    except Exception as e:
        logger.error(f"API: Error getting preferences for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")


@router.put("/user/preferences")
async def update_user_preferences(preferences: PreferencesConfig, user_id: str = Depends(get_or_create_user_id)):
    """Update user preferences."""
    try:
        logger.info(f"API: Updating preferences for user {user_id}")
        logger.debug(f"API: New preferences for user {user_id}: {preferences.model_dump()}")
        
        success = profile_manager.update_preferences(user_id, preferences.model_dump())
        if not success:
            logger.error(f"API: Failed to update preferences for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        logger.info(f"API: Successfully updated preferences for user {user_id}")
        return {"success": True, "message": "Preferences updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error updating preferences for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.get("/user/engagement-analytics", response_model=EngagementAnalytics)
async def get_user_engagement_analytics(user_id: str = Depends(get_or_create_user_id)):
    """Get user engagement analytics."""
    analytics_data = profile_manager.get_engagement_analytics(user_id)
    return EngagementAnalytics(**analytics_data)


@router.get("/user/personalization-history", response_model=PersonalizationHistory)
async def get_user_personalization_history(user_id: str = Depends(get_or_create_user_id)):
    """Get user personalization history."""
    history_data = profile_manager.get_personalization_history(user_id)
    return PersonalizationHistory(**history_data)


@router.get("/user/personalization")
async def get_user_personalization_data(user_id: str = Depends(get_or_create_user_id)):
    """Get complete personalization data for transparency."""
    pm = get_personalization_manager()
    transparency_data = pm.get_learning_transparency_data(user_id)
    return transparency_data


@router.post("/user/engagement/track")
async def track_user_engagement(
    interaction_data: dict,
    user_id: str = Depends(get_or_create_user_id)
):
    """Track user engagement for learning."""
    try:
        pm = get_personalization_manager()
        
        interaction_type = interaction_data.get("interaction_type")
        metadata = interaction_data.get("metadata", {})
        
        if not interaction_type:
            logger.warning(f"API: Missing interaction_type in engagement tracking for user {user_id}")
            raise HTTPException(status_code=400, detail="Missing interaction_type")
        
        logger.info(f"API: Tracking engagement for user {user_id}: {interaction_type}")
        logger.debug(f"API: Engagement metadata for user {user_id}: {metadata}")
        
        success = pm.track_user_engagement(user_id, interaction_type, metadata)
        if not success:
            logger.error(f"API: Failed to track engagement for user {user_id}: {interaction_type}")
            raise HTTPException(status_code=500, detail="Failed to track engagement")
        
        logger.info(f"API: Successfully tracked engagement for user {user_id}: {interaction_type}")
        return {"success": True, "message": "Engagement tracked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error tracking engagement for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to track engagement: {str(e)}")


@router.put("/user/personalization/override")
async def override_learned_behavior(
    override_request: PreferenceOverride,
    user_id: str = Depends(get_or_create_user_id)
):
    """Allow user to override learned behaviors."""
    try:
        pm = get_personalization_manager()
        
        logger.info(f"API: User {user_id} overriding learned behavior: {override_request.preference_type} = {override_request.override_value}")
        logger.debug(f"API: Override request for user {user_id}: disable_learning={override_request.disable_learning}")
        
        success = pm.override_learned_behavior(
            user_id,
            override_request.preference_type,
            override_request.override_value,
            override_request.disable_learning
        )
        
        if not success:
            logger.error(f"API: Failed to override behavior for user {user_id}: {override_request.preference_type}")
            raise HTTPException(status_code=500, detail="Failed to override behavior")
        
        logger.info(f"API: Successfully applied behavior override for user {user_id}: {override_request.preference_type}")
        return {"success": True, "message": "Behavior override applied successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error overriding behavior for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to override behavior: {str(e)}")


@router.get("/user/personalization-context")
async def get_personalization_context(user_id: str = Depends(get_or_create_user_id)):
    """Get personalization context for request processing."""
    pm = get_personalization_manager()
    context = pm.get_personalization_context(user_id)
    return context
