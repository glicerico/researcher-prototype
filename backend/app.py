from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
import traceback
import time
from contextlib import asynccontextmanager
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import and configure logging first, before other imports
from logging_config import configure_logging, get_logger

# Configure application logging
logger = configure_logging()

# Now import other modules that might use logging
from models import ChatRequest, ChatResponse, Message, PersonalityConfig, UserSummary, UserProfile, TopicSuggestion
from pydantic import BaseModel

class MotivationConfigUpdate(BaseModel):
    threshold: Optional[float] = None
    boredom_rate: Optional[float] = None
    curiosity_decay: Optional[float] = None
    tiredness_decay: Optional[float] = None
    satisfaction_decay: Optional[float] = None
from storage import StorageManager, UserManager, ZepManager
from graph_builder import chat_graph
from autonomous_research_engine import initialize_autonomous_researcher

# Global motivation config override (persists across reinitializations)
_motivation_config_override = {}

import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application."""
    # Startup
    logger.info("🚀 Starting AI Chatbot API...")
    
    # Initialize and start the autonomous researcher
    try:
        logger.info("🔬 Initializing Autonomous Research Engine...")
        logger.info(f"App startup - Config override: {_motivation_config_override}")
        app.state.autonomous_researcher = initialize_autonomous_researcher(user_manager, _motivation_config_override)
        await app.state.autonomous_researcher.start()
        logger.info("🔬 Autonomous Research Engine initialized successfully")
    except Exception as e:
        logger.error(f"🔬 Failed to start Autonomous Research Engine: {str(e)}", exc_info=True)
        # Don't fail the app startup if research engine fails
        app.state.autonomous_researcher = None
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Chatbot API...")
    
    # Stop the autonomous researcher
    if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
        try:
            logger.info("🔬 Stopping Autonomous Research Engine...")
            await app.state.autonomous_researcher.stop()
            logger.info("🔬 Autonomous Research Engine stopped successfully")
        except Exception as e:
            logger.error(f"🔬 Error stopping Autonomous Research Engine: {str(e)}")

app = FastAPI(title="AI Chatbot API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get a module-specific logger
logger = get_logger(__name__)

# Initialize storage components
storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_data")
storage_manager = StorageManager(storage_dir)
user_manager = UserManager(storage_manager)

# Initialize Zep manager
zep_manager = ZepManager()


async def extract_and_store_topics_async(state: dict, user_id: str, session_id: str, conversation_context: str):
    """Background function to extract and store topic suggestions."""
    try:
        from nodes.topic_extractor_node import topic_extractor_node
        
        logger.info(f"🔍 Background: Starting topic extraction for session {session_id}")
        
        # Run topic extraction on the conversation state
        updated_state = topic_extractor_node(state)
        
        # Check if topic extraction was successful
        topic_results = updated_state.get("module_results", {}).get("topic_extractor", {})
        
        if topic_results.get("success", False):
            raw_topics = topic_results.get("result", [])
            
            if raw_topics:
                # Store topic suggestions in user profile
                success = user_manager.store_topic_suggestions(
                    user_id=user_id,
                    session_id=session_id,
                    topics=raw_topics,
                    conversation_context=conversation_context
                )
                
                if success:
                    logger.info(f"🔍 Background: Stored {len(raw_topics)} topic suggestions for user {user_id}, session {session_id}")
                else:
                    logger.error(f"🔍 Background: Failed to store topic suggestions for user {user_id}, session {session_id}")
            else:
                logger.info(f"🔍 Background: No topics extracted for session {session_id}")
        else:
            logger.warning(f"🔍 Background: Topic extraction failed for session {session_id}: {topic_results.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"🔍 Background: Error in topic extraction for session {session_id}: {str(e)}", exc_info=True)

def generate_display_name_from_user_id(user_id: str) -> str:
    """Generate a display name from a user ID."""
    if not user_id:
        return "User"
    
    # Check if it's a friendly ID format (adjective-noun-number) - new format
    if len(user_id.split('-')) == 3 and not user_id.startswith('user-'):
        parts = user_id.split('-')
        adjective = parts[0]
        noun = parts[1]
        number = parts[2]
        
        # Capitalize first letters and create a nice display name
        capitalized_adjective = adjective.capitalize()
        capitalized_noun = noun.capitalize()
        
        return f"{capitalized_adjective} {capitalized_noun} {number}"
    
    # Fallback for UUID format - use last 6 characters
    if len(user_id) >= 6:
        return f"User {user_id[-6:]}"
    
    # Ultimate fallback
    return f"User {user_id}"


def get_existing_user_id(user_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user ID from headers if it exists and is valid."""
    if user_id and user_manager.user_exists(user_id):
        return user_id
    return None


def get_or_create_user_id(user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from headers or create a new user."""
    if user_id and user_manager.user_exists(user_id):
        return user_id
    
    # Create a new user
    new_user_id = user_manager.create_user()
    logger.info(f"Created new user: {new_user_id}")
    return new_user_id


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_or_create_user_id)
):
    try:
        # Log the incoming request
        logger.debug(f"Chat request: {request}")
        
        # Convert messages to langchain core message types
        messages_for_state = []
        for m in request.messages:
            if m.role == "user":
                messages_for_state.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                messages_for_state.append(AIMessage(content=m.content))
            elif m.role == "system":
                messages_for_state.append(SystemMessage(content=m.content))
        
        # Prepare the state for the graph
        state = {
            "messages": messages_for_state,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "personality": request.personality.model_dump() if request.personality else None,
            "current_module": None,
            "module_results": {},
            "workflow_context": {},
            "user_id": user_id,
            "session_id": request.session_id  # Use session_id from request, can be None
        }
        
        # Save user's personality if provided
        if request.personality:
            user_manager.update_personality(user_id, request.personality.model_dump())
        
        # Trigger user activity for motivation system (if available)
        try:
            if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
                app.state.autonomous_researcher.motivation.on_user_activity()
                logger.debug("User activity triggered for motivation system")
        except Exception as e:
            logger.warning(f"Failed to trigger user activity for motivation system: {str(e)}")
        
        # Run the graph
        result = await chat_graph.ainvoke(state)
        
        # Check for errors
        if "error" in result:
            raise Exception(result["error"])
        
        # Extract the assistant's response (the last message)
        assistant_message = result["messages"][-1]
        
        # Store conversation in Zep (async, don't wait for completion)
        if len(request.messages) > 0:
            user_message = request.messages[-1].content  # Get the latest user message
            try:
                # Store in background - we don't want to slow down the response
                import asyncio
                asyncio.create_task(
                    zep_manager.store_conversation_turn(
                        user_id=user_id,
                        user_message=user_message,
                        ai_response=assistant_message.content,
                        session_id=result.get("session_id")  # Use the session_id from the workflow
                    )
                )
            except Exception as e:
                # Log error but don't fail the request
                logger.warning(f"Failed to store conversation in Zep: {str(e)}")
        
        # Process topic suggestions in background (don't wait for completion)
        if result.get("session_id") and len(request.messages) > 0:
            try:
                import asyncio
                asyncio.create_task(
                    extract_and_store_topics_async(
                        state=result,
                        user_id=user_id,
                        session_id=result["session_id"],
                        conversation_context=request.messages[-1].content[:200] + "..." if len(request.messages[-1].content) > 200 else request.messages[-1].content
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to start background topic extraction: {str(e)}")
        
        return ChatResponse(
            response=assistant_message.content,
            model=request.model,
            usage={},
            module_used=result.get("current_module", "unknown"),
            routing_analysis=result.get("routing_analysis"),
            user_id=user_id,
            session_id=result.get("session_id"),  # Return the session_id to frontend
            suggested_topics=[]  # Empty list - topics will be available via the topics endpoint after processing
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def get_models():
    """Get available models."""
    return {
        "models": {
            "gpt-4o": {"name": "GPT-4o", "provider": "OpenAI"},
            "gpt-4o-mini": {"name": "GPT-4o Mini", "provider": "OpenAI"},
            "gpt-4-turbo": {"name": "GPT-4 Turbo", "provider": "OpenAI"},
            "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "provider": "OpenAI"}
        }
    }


@app.get("/personality-presets")
async def get_personality_presets():
    """Get available personality presets."""
    return {
        "presets": {
            "helpful": {"style": "helpful", "tone": "friendly"},
            "professional": {"style": "expert", "tone": "professional"},
            "casual": {"style": "conversational", "tone": "casual"},
            "creative": {"style": "creative", "tone": "enthusiastic"},
            "concise": {"style": "concise", "tone": "direct"}
        }
    }


@app.get("/user", response_model=UserProfile)
async def get_current_user(user_id: Optional[str] = Depends(get_existing_user_id)):
    """Get the current user's profile."""
    if not user_id:
        raise HTTPException(status_code=404, detail="No user ID provided or user not found")
    
    user_data = user_manager.get_user(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfile(
        user_id=user_data["user_id"],
        created_at=user_data["created_at"],
        metadata=user_data.get("metadata", {}),
        personality=PersonalityConfig(**user_data.get("personality", {}))
    )


@app.put("/user/personality")
async def update_user_personality(
    personality: PersonalityConfig,
    user_id: str = Depends(get_or_create_user_id)
):
    """Update the user's personality settings."""
    success = user_manager.update_personality(user_id, personality.model_dump())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update personality")
    
    return {"success": True, "message": "Personality updated successfully"}


@app.put("/user/display-name")
async def update_user_display_name(
    display_name: str,
    user_id: str = Depends(get_or_create_user_id)
):
    """Update the user's display name."""
    success = user_manager.update_user(user_id, {"metadata": {"display_name": display_name}})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update display name")
    
    return {"success": True, "message": "Display name updated successfully"}


@app.get("/users", response_model=List[UserSummary])
async def list_users():
    """List all users with basic information for the user selector."""
    user_ids = user_manager.list_users()
    user_summaries = []
    
    for user_id in user_ids:
        user_data = user_manager.get_user(user_id)
        if user_data:
            # Get personality details
            personality = user_data.get("personality", {})
            personality_config = PersonalityConfig(
                style=personality.get("style", "helpful"),
                tone=personality.get("tone", "friendly"),
                additional_traits=personality.get("additional_traits", {})
            )
            
            # Get a display name (use metadata or fallback to generated name)
            metadata = user_data.get("metadata", {})
            display_name = metadata.get("display_name", generate_display_name_from_user_id(user_id))
            
            user_summaries.append(UserSummary(
                user_id=user_id,
                created_at=user_data.get("created_at", 0),
                personality=personality_config,
                display_name=display_name
            ))
    
    # Sort by most recently created
    user_summaries.sort(key=lambda x: x.created_at, reverse=True)
    
    return user_summaries


@app.post("/users")
async def create_user(display_name: Optional[str] = None):
    """Create a new user."""
    metadata = {}
    if display_name:
        metadata["display_name"] = display_name
    
    user_id = user_manager.create_user(metadata)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    return {
        "success": True,
        "user_id": user_id,
        "display_name": display_name or generate_display_name_from_user_id(user_id)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy", 
        "message": "AI Chatbot API is running",
        "autonomous_researcher": {
            "available": False,
            "enabled": False,
            "running": False
        }
    }
    
    # Check autonomous researcher status
    if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
        try:
            researcher_status = app.state.autonomous_researcher.get_status()
            health_status["autonomous_researcher"] = {
                "available": True,
                "enabled": researcher_status.get("enabled", False),
                "running": researcher_status.get("running", False),
                "interval_hours": researcher_status.get("research_interval_hours", 0),
                "engine_type": researcher_status.get("engine_type", "unknown")
            }
        except Exception as e:
            health_status["autonomous_researcher"]["error"] = str(e)
    
    return health_status


@app.get("/zep/status")
async def zep_status():
    """Get Zep memory status."""
    try:
        return {
            "enabled": zep_manager.is_enabled(),
            "configured": config.ZEP_ENABLED,
            "api_key_set": bool(config.ZEP_API_KEY)
        }
    except Exception as e:
        logger.error(f"Error getting Zep status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting Zep status: {str(e)}")


@app.get("/topics/suggestions/{session_id}")
async def get_topic_suggestions(
    session_id: str,
    user_id: str = Depends(get_or_create_user_id)
):
    """Get all suggested topics for a session."""
    try:
        # Get stored topic suggestions from user profile
        stored_topics = user_manager.get_topic_suggestions(user_id, session_id)
        
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
                "is_active_research": topic.get("is_active_research", False)
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
            "total_count": len(topic_suggestions)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving topic suggestions for user {user_id}, session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic suggestions: {str(e)}")


@app.get("/topics/suggestions")
async def get_all_topic_suggestions(
    user_id: str = Depends(get_or_create_user_id)
):
    """Get all suggested topics for a user across all sessions."""
    try:
        # Get all topic suggestions from user profile
        all_topics_by_session = user_manager.get_all_topic_suggestions(user_id)
        
        # Flatten and convert to response format
        all_topics = []
        for session_id, topics in all_topics_by_session.items():
            for topic in topics:
                all_topics.append({
                    "session_id": session_id,
                    "topic_id": topic.get("topic_id"),  # Add topic ID for safe deletion
                    "name": topic.get("topic_name", ""),
                    "description": topic.get("description", ""),
                    "confidence_score": topic.get("confidence_score", 0.0),
                    "suggested_at": topic.get("suggested_at", 0),
                    "conversation_context": topic.get("conversation_context", ""),
                    "is_active_research": topic.get("is_active_research", False)
                })
        
        # Sort by suggestion time (most recent first)
        all_topics.sort(key=lambda x: x["suggested_at"], reverse=True)
        
        return {
            "user_id": user_id,
            "topic_suggestions": all_topics,
            "total_count": len(all_topics),
            "sessions_count": len(all_topics_by_session)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving all topic suggestions for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic suggestions: {str(e)}")


@app.get("/topics/status/{session_id}")
async def get_topic_processing_status(
    session_id: str,
    user_id: str = Depends(get_or_create_user_id)
):
    """Check if topic suggestions are available for a session (useful for polling after chat)."""
    try:
        # Get stored topic suggestions from user profile
        stored_topics = user_manager.get_topic_suggestions(user_id, session_id)
        
        has_topics = len(stored_topics) > 0
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "has_topics": has_topics,
            "topic_count": len(stored_topics),
            "processing_complete": has_topics  # Simple check - if topics exist, processing is done
        }
        
    except Exception as e:
        logger.error(f"Error checking topic status for user {user_id}, session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking topic status: {str(e)}")


@app.get("/topics/stats")
async def get_topic_statistics(
    user_id: str = Depends(get_or_create_user_id)
):
    """Get statistics about the user's topic suggestions."""
    try:
        # Get all topic suggestions from user profile
        all_topics_by_session = user_manager.get_all_topic_suggestions(user_id)
        
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
            "oldest_topic_age_days": oldest_topic_age_days
        }
        
    except Exception as e:
        logger.error(f"Error retrieving topic statistics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic statistics: {str(e)}")


@app.delete("/topics/session/{session_id}")
async def delete_session_topics(
    session_id: str,
    user_id: str = Depends(get_or_create_user_id)
):
    """Delete all topic suggestions for a specific session using safe deletion."""
    try:
        # Use the new safe session deletion method
        result = user_manager.delete_session_safe(user_id, session_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "session_id": session_id,
                "topics_deleted": result["topics_deleted"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting topics for session {session_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session topics: {str(e)}")


@app.delete("/topics/cleanup")
async def cleanup_topics(
    user_id: str = Depends(get_or_create_user_id)
):
    """Clean up old and duplicate topics for the user."""
    try:
        # Ensure migration from profile.json if needed
        user_manager.migrate_topics_from_profile(user_id)
        
        # Load topics data
        topics_data = user_manager.get_user_topics(user_id)
        
        if not topics_data.get("sessions"):
            return {
                "success": True,
                "message": "No topics to clean up",
                "topics_removed": 0,
                "sessions_cleaned": 0
            }
        
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
        topics_data["metadata"]["total_topics"] = sum(
            len(topics) for topics in topics_data["sessions"].values()
        )
        topics_data["metadata"]["active_research_topics"] = sum(
            1 for session_topics in topics_data["sessions"].values()
            for topic in session_topics
            if topic.get("is_active_research", False)
        )
        topics_data["metadata"]["last_cleanup"] = current_time
        
        # Save updated topics
        success = user_manager.save_user_topics(user_id, topics_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clean up topics")
        
        return {
            "success": True,
            "message": f"Cleaned up {topics_removed} topics and {sessions_cleaned} empty sessions",
            "topics_removed": topics_removed,
            "sessions_cleaned": sessions_cleaned
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up topics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up topics: {str(e)}")


@app.get("/topics/session/{session_id}/top")
async def get_top_session_topics(
    session_id: str,
    limit: int = Query(default=3, ge=1, le=10),
    user_id: str = Depends(get_or_create_user_id)
):
    """Get the top N topics for a session, ordered by confidence score."""
    try:
        # Get stored topic suggestions from user profile
        stored_topics = user_manager.get_topic_suggestions(user_id, session_id)
        
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
                "is_active_research": topic.get("is_active_research", False)
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
            "available_count": len(stored_topics)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving top topics for user {user_id}, session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving top topics: {str(e)}")


@app.delete("/topics/topic/{topic_id}")
async def delete_topic_by_id(
    topic_id: str,
    user_id: str = Depends(get_or_create_user_id)
):
    """Delete a topic by its unique ID (safer than index-based deletion)."""
    try:
        # Use the safe ID-based deletion method
        result = user_manager.delete_topic_by_id(user_id, topic_id)
        
        if result["success"]:
            deleted_topic = result["deleted_topic"]
            return {
                "success": True,
                "message": f"Deleted topic: {deleted_topic['topic_name']}",
                "deleted_topic": {
                    "topic_id": deleted_topic["topic_id"],
                    "name": deleted_topic["topic_name"],
                    "description": deleted_topic["description"],
                    "session_id": deleted_topic["session_id"]
                }
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


# =================== RESEARCH FINDINGS API ENDPOINTS ===================

@app.get("/research/findings/{user_id}")
async def get_research_findings(
    user_id: str,
    topic_name: Optional[str] = Query(None, description="Filter by topic name"),
    unread_only: bool = Query(False, description="Only return unread findings")
):
    """Get research findings for a user, optionally filtered by topic or read status."""
    try:
        # Use the new API method from user_manager
        findings = user_manager.get_research_findings_for_api(user_id, topic_name, unread_only)
        
        return {
            "success": True,
            "user_id": user_id,
            "total_findings": len(findings),
            "filters": {
                "topic_name": topic_name,
                "unread_only": unread_only
            },
            "findings": findings
        }
        
    except Exception as e:
        logger.error(f"Error getting research findings for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research findings: {str(e)}")


@app.post("/research/findings/{finding_id}/mark_read")
async def mark_research_finding_read(
    finding_id: str,
    user_id: str = Depends(get_or_create_user_id)
):
    """Mark a research finding as read."""
    try:
        success = user_manager.mark_finding_as_read(user_id, finding_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")
        
        return {
            "success": True,
            "message": f"Marked finding {finding_id} as read",
            "finding_id": finding_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking finding as read for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error marking finding as read: {str(e)}")


@app.get("/research/status")
async def get_research_engine_status():
    """Get the current status of the autonomous research engine."""
    try:
        if hasattr(app.state, 'autonomous_researcher'):
            status = app.state.autonomous_researcher.get_status()
            return status
        else:
            return {
                "enabled": False,
                "running": False,
                "error": "Autonomous researcher not initialized"
            }
        
    except Exception as e:
        logger.error(f"Error getting research engine status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research status: {str(e)}")


@app.get("/research/debug/active-topics")
async def get_debug_active_topics():
    """Debug endpoint to see active research topics across all users."""
    try:
        debug_info = {
            "total_users": 0,
            "users_with_active_topics": 0,
            "total_active_topics": 0,
            "user_breakdown": []
        }
        
        # Get all users
        all_users = user_manager.list_users()
        debug_info["total_users"] = len(all_users)
        
        for user_id in all_users:
            try:
                active_topics = user_manager.get_active_research_topics(user_id)
                if active_topics:
                    debug_info["users_with_active_topics"] += 1
                    debug_info["total_active_topics"] += len(active_topics)
                    
                    debug_info["user_breakdown"].append({
                        "user_id": user_id,
                        "active_topics_count": len(active_topics),
                        "topics": [
                            {
                                "name": topic.get("topic_name"),
                                "description": topic.get("description", "")[:100] + "..." if len(topic.get("description", "")) > 100 else topic.get("description", ""),
                                "last_researched": topic.get("last_researched"),
                                "research_count": topic.get("research_count", 0)
                            }
                            for topic in active_topics
                        ]
                    })
                    
            except Exception as e:
                logger.error(f"Error getting active topics for user {user_id}: {str(e)}")
                continue
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Error getting debug active topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting debug info: {str(e)}")


@app.get("/research/debug/config-override")
async def get_config_override():
    """Debug endpoint to see what's in the config override."""
    return {"override": _motivation_config_override}

@app.post("/research/debug/clear-override")
async def clear_config_override():
    """Debug endpoint to clear the config override."""
    global _motivation_config_override
    _motivation_config_override = {}
    return {"success": True, "message": "Config override cleared"}

@app.get("/research/debug/motivation")
async def get_motivation_status():
    """Debug endpoint to check motivation system status."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            researcher = app.state.autonomous_researcher
            motivation = researcher.motivation
            
            # Only tick if the research engine is actually running
            # This ensures drives only evolve when the engine is active
            if researcher.is_running:
                motivation.tick()
            
            return {
                "motivation_system": {
                    "boredom": round(motivation.boredom, 4),
                    "curiosity": round(motivation.curiosity, 4),
                    "tiredness": round(motivation.tiredness, 4),
                    "satisfaction": round(motivation.satisfaction, 4),
                    "impetus": round(motivation.impetus(), 4),
                    "threshold": motivation.drives.threshold,
                    "should_research": motivation.should_research(),
                    "time_since_last_tick": round(time.time() - motivation.last_tick, 2)
                },
                "research_engine": {
                    "enabled": researcher.enabled,
                    "running": researcher.is_running,
                    "check_interval": researcher.check_interval
                },
                "drive_rates": {
                    "boredom_rate": motivation.drives.boredom_rate,
                    "curiosity_decay": motivation.drives.curiosity_decay,
                    "tiredness_decay": motivation.drives.tiredness_decay,
                    "satisfaction_decay": motivation.drives.satisfaction_decay
                }
            }
        else:
            return {
                "error": "Autonomous researcher not available"
            }
        
    except Exception as e:
        logger.error(f"Error getting motivation status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting motivation status: {str(e)}")


@app.post("/research/debug/trigger-user-activity")
async def trigger_user_activity():
    """Debug endpoint to simulate user activity (increases curiosity)."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            researcher = app.state.autonomous_researcher
            researcher.motivation.on_user_activity()
            
            return {
                "success": True,
                "message": "User activity triggered",
                "new_motivation_state": {
                    "boredom": round(researcher.motivation.boredom, 4),
                    "curiosity": round(researcher.motivation.curiosity, 4),
                    "impetus": round(researcher.motivation.impetus(), 4),
                    "should_research": researcher.motivation.should_research()
                }
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")
        
    except Exception as e:
        logger.error(f"Error triggering user activity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering user activity: {str(e)}")


@app.post("/research/debug/adjust-drives")
async def adjust_motivation_drives(
    boredom: Optional[float] = None,
    curiosity: Optional[float] = None,
    tiredness: Optional[float] = None,
    satisfaction: Optional[float] = None
):
    """Debug endpoint to manually set motivation drive values for testing."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            researcher = app.state.autonomous_researcher
            motivation = researcher.motivation
            
            old_values = {
                "boredom": motivation.boredom,
                "curiosity": motivation.curiosity, 
                "tiredness": motivation.tiredness,
                "satisfaction": motivation.satisfaction
            }
            
            # Update provided values
            if boredom is not None:
                motivation.boredom = max(0.0, min(1.0, boredom))
            if curiosity is not None:
                motivation.curiosity = max(0.0, min(1.0, curiosity))
            if tiredness is not None:
                motivation.tiredness = max(0.0, min(1.0, tiredness))
            if satisfaction is not None:
                motivation.satisfaction = max(0.0, min(1.0, satisfaction))
            
            new_values = {
                "boredom": motivation.boredom,
                "curiosity": motivation.curiosity,
                "tiredness": motivation.tiredness,
                "satisfaction": motivation.satisfaction
            }
            
            return {
                "success": True,
                "message": "Motivation drives adjusted",
                "old_values": old_values,
                "new_values": new_values,
                "impetus": round(motivation.impetus(), 4),
                "should_research": motivation.should_research()
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")
        
    except Exception as e:
        logger.error(f"Error adjusting motivation drives: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adjusting drives: {str(e)}")




@app.post("/research/debug/update-config")
async def update_motivation_config(config: MotivationConfigUpdate):
    """Debug endpoint to update motivation system configuration parameters."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            researcher = app.state.autonomous_researcher
            motivation = researcher.motivation
            drives_config = motivation.drives
            
            # Check if this is a complete config replacement (all parameters provided)
            all_params_provided = all(getattr(config, param) is not None for param in ['threshold', 'boredom_rate', 'curiosity_decay', 'tiredness_decay', 'satisfaction_decay'])
            
            if all_params_provided:
                # Complete replacement - clear override and set new values
                global _motivation_config_override
                _motivation_config_override = {}
            
            # Update provided values
            if config.threshold is not None:
                value = max(0.1, min(10.0, config.threshold))
                drives_config.threshold = value
                _motivation_config_override['threshold'] = value
            if config.boredom_rate is not None:
                value = max(0.0, min(0.1, config.boredom_rate))
                drives_config.boredom_rate = value
                _motivation_config_override['boredom_rate'] = value
            if config.curiosity_decay is not None:
                value = max(0.0, min(0.1, config.curiosity_decay))
                drives_config.curiosity_decay = value
                _motivation_config_override['curiosity_decay'] = value
            if config.tiredness_decay is not None:
                value = max(0.0, min(0.1, config.tiredness_decay))
                drives_config.tiredness_decay = value
                _motivation_config_override['tiredness_decay'] = value
            if config.satisfaction_decay is not None:
                value = max(0.0, min(0.1, config.satisfaction_decay))
                drives_config.satisfaction_decay = value
                _motivation_config_override['satisfaction_decay'] = value
            
            return {
                "success": True,
                "message": "Motivation configuration updated",
                "impetus": round(motivation.impetus(), 4),
                "should_research": motivation.should_research()
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")
        
    except Exception as e:
        logger.error(f"Error updating motivation config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@app.post("/research/debug/simulate-research-completion")
async def simulate_research_completion(quality_score: float = 0.7):
    """Debug endpoint to simulate research completion with specified quality."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            researcher = app.state.autonomous_researcher
            
            old_state = {
                "boredom": researcher.motivation.boredom,
                "curiosity": researcher.motivation.curiosity,
                "tiredness": researcher.motivation.tiredness,
                "satisfaction": researcher.motivation.satisfaction
            }
            
            researcher.motivation.on_research_completed(quality_score)
            
            new_state = {
                "boredom": researcher.motivation.boredom,
                "curiosity": researcher.motivation.curiosity,
                "tiredness": researcher.motivation.tiredness,
                "satisfaction": researcher.motivation.satisfaction
            }
            
            return {
                "success": True,
                "message": f"Research completion simulated with quality {quality_score}",
                "quality_score": quality_score,
                "old_state": old_state,
                "new_state": new_state,
                "impetus": round(researcher.motivation.impetus(), 4),
                "should_research": researcher.motivation.should_research()
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")
        
    except Exception as e:
        logger.error(f"Error simulating research completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error simulating research completion: {str(e)}")


@app.post("/research/trigger/{user_id}")
async def trigger_research_for_user(user_id: str):
    """Manually trigger research for a specific user (for testing/debugging)."""
    try:
        if hasattr(app.state, 'autonomous_researcher'):
            result = await app.state.autonomous_researcher.trigger_research_for_user(user_id)
            return result
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering research for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering research: {str(e)}")


@app.post("/research/control/start")
async def start_research_engine():
    """Start the autonomous research engine."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            # Enable and start
            app.state.autonomous_researcher.enable()
            await app.state.autonomous_researcher.start()
            return {
                "success": True,
                "message": "Autonomous research engine started successfully",
                "status": app.state.autonomous_researcher.get_status()
            }
        else:
            # Try to initialize if not available
            try:
                logger.info("🔬 Re-initializing Autonomous Research Engine...")
                app.state.autonomous_researcher = initialize_autonomous_researcher(user_manager, _motivation_config_override)
                app.state.autonomous_researcher.enable()
                await app.state.autonomous_researcher.start()
                logger.info("🔬 Autonomous Research Engine re-initialized and started successfully")
                return {
                    "success": True,
                    "message": "Autonomous research engine initialized and started successfully",
                    "status": app.state.autonomous_researcher.get_status()
                }
            except Exception as e:
                logger.error(f"🔬 Failed to initialize/start Autonomous Research Engine: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to start research engine: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting research engine: {str(e)}")


@app.post("/research/control/stop")
async def stop_research_engine():
    """Stop the autonomous research engine."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            # Stop and disable
            await app.state.autonomous_researcher.stop()
            app.state.autonomous_researcher.disable()
            return {
                "success": True,
                "message": "Autonomous research engine stopped successfully",
                "status": app.state.autonomous_researcher.get_status()
            }
        else:
            return {
                "success": True,
                "message": "Autonomous research engine was not running",
                "status": {
                    "enabled": False,
                    "running": False,
                    "error": "Research engine not initialized"
                }
            }
        
    except Exception as e:
        logger.error(f"Error stopping research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping research engine: {str(e)}")


@app.post("/research/control/restart")
async def restart_research_engine():
    """Restart the autonomous research engine."""
    try:
        if hasattr(app.state, 'autonomous_researcher') and app.state.autonomous_researcher:
            # Stop first
            await app.state.autonomous_researcher.stop()
            # Then enable and start again
            app.state.autonomous_researcher.enable()
            await app.state.autonomous_researcher.start()
            return {
                "success": True,
                "message": "Autonomous research engine restarted successfully",
                "status": app.state.autonomous_researcher.get_status()
            }
        else:
            # Try to initialize if not available
            try:
                logger.info("🔬 Initializing Autonomous Research Engine for restart...")
                app.state.autonomous_researcher = initialize_autonomous_researcher(user_manager, _motivation_config_override)
                app.state.autonomous_researcher.enable()
                await app.state.autonomous_researcher.start()
                logger.info("🔬 Autonomous Research Engine initialized and started successfully")
                return {
                    "success": True,
                    "message": "Autonomous research engine initialized and started successfully",
                    "status": app.state.autonomous_researcher.get_status()
                }
            except Exception as e:
                logger.error(f"🔬 Failed to initialize/restart Autonomous Research Engine: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to restart research engine: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restarting research engine: {str(e)}")


@app.get("/topics/user/{user_id}/research")
async def get_active_research_topics(user_id: str):
    """Get all active research topics for a user."""
    try:
        active_topics = user_manager.get_active_research_topics(user_id)
        
        # Format for API response
        api_topics = []
        for topic in active_topics:
            api_topics.append({
                "topic_name": topic.get("topic_name"),
                "description": topic.get("description"),
                "session_id": topic.get("session_id"),
                "research_enabled_at": topic.get("research_enabled_at"),
                "last_researched": topic.get("last_researched"),
                "research_count": topic.get("research_count", 0),
                "confidence_score": topic.get("confidence_score", 0.0)
            })
        
        return {
            "success": True,
            "user_id": user_id,
            "active_research_topics": api_topics,
            "total_count": len(api_topics)
        }
        
    except Exception as e:
        logger.error(f"Error getting active research topics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting active research topics: {str(e)}")


@app.put("/topics/topic/{topic_id}/research")
async def enable_disable_research_by_topic_id(
    topic_id: str,
    enable: bool = Query(True, description="True to enable, False to disable"),
    user_id: str = Depends(get_or_create_user_id)
):
    """Enable or disable research for a topic by its unique ID (safer than index-based operations)."""
    try:
        # Use the safe ID-based method to update research status
        result = user_manager.update_topic_research_status_by_id(user_id, topic_id, enable)
        
        if result["success"]:
            updated_topic = result["updated_topic"]
            action = "enabled" if enable else "disabled"
            return {
                "success": True,
                "message": f"Research {action} for topic: {updated_topic['topic_name']}",
                "topic": {
                    "topic_id": updated_topic["topic_id"],
                    "name": updated_topic["topic_name"],
                    "description": updated_topic["description"],
                    "session_id": updated_topic["session_id"],
                    "is_active_research": enable
                }
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
        logger.error(f"Error updating research status for topic ID {topic_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating research status: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT) 