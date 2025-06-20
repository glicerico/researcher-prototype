from fastapi import APIRouter, Depends, HTTPException, Query
import time

from dependencies import get_or_create_user_id, research_manager
from logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/topics/suggestions/{session_id}")
async def get_topic_suggestions(session_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Get all suggested topics for a session."""
    try:
        # Get stored topic suggestions from user profile
        stored_topics = research_manager.get_topic_suggestions(user_id, session_id)

        # Convert to response format with topic IDs
        topic_suggestions = []
        for i, topic in enumerate(stored_topics):
            topic_suggestion = {
                "index": i,  # Keep index for backward compatibility
                "topic_id": topic.get("topic_id"),  # Add topic ID for safe deletion
                "name": topic.get("topic_name", ""),
                "description": topic.get("description", ""),
                "confidence_score": topic.get("confidence_score", 0.0),
                "suggested_at": topic.get("suggested_at", 0),
                "conversation_context": topic.get("conversation_context", ""),
                "is_active_research": topic.get("is_active_research", False),
            }

            # Add topic ID if missing (for backward compatibility)
            if not topic_suggestion["topic_id"]:
                topic_suggestion["topic_id"] = f"legacy_{session_id}_{i}"
                logger.warning(f"Topic at index {i} in session {session_id} missing topic_id, using legacy ID")

            topic_suggestions.append(topic_suggestion)

        # Sort by suggestion time (most recent first)
        topic_suggestions.sort(key=lambda x: x["suggested_at"], reverse=True)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "topic_suggestions": topic_suggestions,
            "total_count": len(topic_suggestions),
        }

    except Exception as e:
        logger.error(f"Error retrieving topic suggestions for user {user_id}, session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic suggestions: {str(e)}")


@router.get("/topics/suggestions")
async def get_all_topic_suggestions(user_id: str = Depends(get_or_create_user_id)):
    """Get all suggested topics for a user across all sessions."""
    try:
        # Get all topic suggestions from user profile
        all_topics_by_session = research_manager.get_all_topic_suggestions(user_id)

        # Flatten and convert to response format
        all_topics = []
        for session_id, topics in all_topics_by_session.items():
            for topic in topics:
                all_topics.append(
                    {
                        "session_id": session_id,
                        "topic_id": topic.get("topic_id"),  # Add topic ID for safe deletion
                        "name": topic.get("topic_name", ""),
                        "description": topic.get("description", ""),
                        "confidence_score": topic.get("confidence_score", 0.0),
                        "suggested_at": topic.get("suggested_at", 0),
                        "conversation_context": topic.get("conversation_context", ""),
                        "is_active_research": topic.get("is_active_research", False),
                    }
                )

        # Sort by suggestion time (most recent first)
        all_topics.sort(key=lambda x: x["suggested_at"], reverse=True)

        return {
            "user_id": user_id,
            "topic_suggestions": all_topics,
            "total_count": len(all_topics),
            "sessions_count": len(all_topics_by_session),
        }

    except Exception as e:
        logger.error(f"Error retrieving all topic suggestions for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic suggestions: {str(e)}")


@router.get("/topics/status/{session_id}")
async def get_topic_processing_status(session_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Check if topic suggestions are available for a session (useful for polling after chat)."""
    try:
        # Get stored topic suggestions from user profile
        stored_topics = research_manager.get_topic_suggestions(user_id, session_id)

        has_topics = len(stored_topics) > 0

        return {
            "session_id": session_id,
            "user_id": user_id,
            "has_topics": has_topics,
            "topic_count": len(stored_topics),
            "processing_complete": has_topics,  # Simple check - if topics exist, processing is done
        }

    except Exception as e:
        logger.error(f"Error checking topic status for user {user_id}, session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking topic status: {str(e)}")


@router.get("/topics/stats")
async def get_topic_statistics(user_id: str = Depends(get_or_create_user_id)):
    """Get statistics about the user's topic suggestions."""
    try:
        # Get all topic suggestions from user profile
        all_topics_by_session = research_manager.get_all_topic_suggestions(user_id)

        # Calculate statistics
        total_topics = 0
        total_sessions = len(all_topics_by_session)
        confidence_scores = []
        oldest_timestamp = None

        for session_id, topics in all_topics_by_session.items():
            total_topics += len(topics)
            for topic in topics:
                confidence_scores.append(topic.get("confidence_score", 0.0))
                suggested_at = topic.get("suggested_at", 0)
                if oldest_timestamp is None or suggested_at < oldest_timestamp:
                    oldest_timestamp = suggested_at

        # Calculate average confidence
        average_confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Calculate oldest topic age in days
        current_time = time.time()
        oldest_topic_age_days = 0
        if oldest_timestamp:
            oldest_topic_age_days = int((current_time - oldest_timestamp) / (24 * 60 * 60))

        return {
            "user_id": user_id,
            "total_topics": total_topics,
            "total_sessions": total_sessions,
            "average_confidence_score": average_confidence_score,
            "oldest_topic_age_days": oldest_topic_age_days,
        }

    except Exception as e:
        logger.error(f"Error retrieving topic statistics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic statistics: {str(e)}")


@router.delete("/topics/session/{session_id}")
async def delete_session_topics(session_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Delete all topic suggestions for a specific session using safe deletion."""
    try:
        # Use the new safe session deletion method
        result = research_manager.delete_session_safe(user_id, session_id)

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "session_id": session_id,
                "topics_deleted": result["topics_deleted"],
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting topics for session {session_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session topics: {str(e)}")


@router.delete("/topics/cleanup")
async def cleanup_topics(user_id: str = Depends(get_or_create_user_id)):
    """Clean up old and duplicate topics for the user."""
    try:
        # Ensure migration from profile.json if needed
        research_manager.migrate_topics_from_profile(user_id)

        # Load topics data
        topics_data = research_manager.get_user_topics(user_id)

        if not topics_data.get("sessions"):
            return {"success": True, "message": "No topics to clean up", "topics_removed": 0, "sessions_cleaned": 0}

        current_time = time.time()
        retention_days = 30  # Keep topics for 30 days
        retention_threshold = current_time - (retention_days * 24 * 60 * 60)

        topics_removed = 0
        sessions_cleaned = 0
        sessions_to_remove = []

        # Clean up old topics and duplicates
        for session_id, topics in topics_data["sessions"].items():
            # Filter out old topics
            filtered_topics = []
            for topic in topics:
                suggested_at = topic.get("suggested_at", 0)
                if suggested_at >= retention_threshold:
                    filtered_topics.append(topic)
                else:
                    topics_removed += 1

            # Remove duplicate topics within the session (by name)
            seen_names = set()
            deduplicated_topics = []
            for topic in filtered_topics:
                topic_name = topic.get("topic_name", "").lower()
                if topic_name not in seen_names:
                    seen_names.add(topic_name)
                    deduplicated_topics.append(topic)
                else:
                    topics_removed += 1

            if deduplicated_topics:
                topics_data["sessions"][session_id] = deduplicated_topics
            else:
                sessions_to_remove.append(session_id)
                sessions_cleaned += 1

        # Remove empty sessions
        for session_id in sessions_to_remove:
            del topics_data["sessions"][session_id]

        # Update metadata
        topics_data["metadata"]["total_topics"] = sum(len(topics) for topics in topics_data["sessions"].values())
        topics_data["metadata"]["active_research_topics"] = sum(
            1
            for session_topics in topics_data["sessions"].values()
            for topic in session_topics
            if topic.get("is_active_research", False)
        )
        topics_data["metadata"]["last_cleanup"] = current_time

        # Save updated topics
        success = research_manager.save_user_topics(user_id, topics_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to clean up topics")

        return {
            "success": True,
            "message": f"Cleaned up {topics_removed} topics and {sessions_cleaned} empty sessions",
            "topics_removed": topics_removed,
            "sessions_cleaned": sessions_cleaned,
        }

    except Exception as e:
        logger.error(f"Error cleaning up topics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up topics: {str(e)}")


@router.get("/topics/session/{session_id}/top")
async def get_top_session_topics(
    session_id: str, limit: int = Query(default=3, ge=1, le=10), user_id: str = Depends(get_or_create_user_id)
):
    """Get the top N topics for a session, ordered by confidence score."""
    try:
        # Get stored topic suggestions from user profile
        stored_topics = research_manager.get_topic_suggestions(user_id, session_id)

        # Convert to response format and sort by confidence
        topic_suggestions = []
        for index, topic in enumerate(stored_topics):
            topic_suggestion = {
                "index": index,
                "topic_id": topic.get("topic_id"),  # Add topic ID for safe deletion
                "session_id": session_id,
                "name": topic.get("topic_name", ""),
                "description": topic.get("description", ""),
                "confidence_score": topic.get("confidence_score", 0.0),
                "suggested_at": topic.get("suggested_at", 0),
                "conversation_context": topic.get("conversation_context", ""),
                "is_active_research": topic.get("is_active_research", False),
            }

            # Add topic ID if missing (for backward compatibility)
            if not topic_suggestion["topic_id"]:
                topic_suggestion["topic_id"] = f"legacy_{session_id}_{index}"
                logger.warning(f"Topic at index {index} in session {session_id} missing topic_id, using legacy ID")

            topic_suggestions.append(topic_suggestion)

        # Sort by confidence score (highest first) and limit results
        topic_suggestions.sort(key=lambda x: x["confidence_score"], reverse=True)
        top_topics = topic_suggestions[:limit]

        return {
            "session_id": session_id,
            "user_id": user_id,
            "topics": top_topics,
            "total_count": len(top_topics),
            "available_count": len(stored_topics),
        }

    except Exception as e:
        logger.error(f"Error retrieving top topics for user {user_id}, session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving top topics: {str(e)}")


@router.delete("/topics/topic/{topic_id}")
async def delete_topic_by_id(topic_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Delete a topic by its unique ID (safer than index-based deletion)."""
    try:
        # Use the safe ID-based deletion method
        result = research_manager.delete_topic_by_id(user_id, topic_id)

        if result["success"]:
            deleted_topic = result["deleted_topic"]
            return {
                "success": True,
                "message": f"Deleted topic: {deleted_topic['topic_name']}",
                "deleted_topic": {
                    "topic_id": deleted_topic["topic_id"],
                    "name": deleted_topic["topic_name"],
                    "description": deleted_topic["description"],
                    "session_id": deleted_topic["session_id"],
                },
            }
        else:
            # Map specific errors to appropriate HTTP status codes
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting topic by ID {topic_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting topic: {str(e)}")
