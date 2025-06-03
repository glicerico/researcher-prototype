from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import traceback
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import and configure logging first, before other imports
from logging_config import configure_logging, get_logger

# Configure application logging
logger = configure_logging()

# Now import other modules that might use logging
from models import ChatRequest, ChatResponse, Message, PersonalityConfig, UserSummary, UserProfile, TopicSuggestion
from storage import StorageManager, UserManager, ZepManager
from graph_builder import create_chat_graph
import config

app = FastAPI(title="AI Chatbot API", version="1.0.0")

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

# Build the chat graph
chat_graph = create_chat_graph()

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
    
    # Check if it's a friendly ID format (user-adjective-noun-number)
    if user_id.startswith('user-') and len(user_id.split('-')) == 4:
        parts = user_id.split('-')
        adjective = parts[1]
        noun = parts[2]
        number = parts[3]
        
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
    return {"status": "healthy", "message": "AI Chatbot API is running"}


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
        
        # Convert to response format
        topic_suggestions = []
        for topic in stored_topics:
            topic_suggestions.append({
                "name": topic.get("topic_name", ""),
                "description": topic.get("description", ""),
                "confidence_score": topic.get("confidence_score", 0.0),
                "suggested_at": topic.get("suggested_at", 0),
                "conversation_context": topic.get("conversation_context", "")
            })
        
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
                    "name": topic.get("topic_name", ""),
                    "description": topic.get("description", ""),
                    "confidence_score": topic.get("confidence_score", 0.0),
                    "suggested_at": topic.get("suggested_at", 0),
                    "conversation_context": topic.get("conversation_context", "")
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
    """Delete all topic suggestions for a specific session."""
    try:
        # Get user profile
        profile = user_manager.get_user(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Remove topics for this session
        topic_suggestions = profile.get("topic_suggestions", {})
        if session_id in topic_suggestions:
            del topic_suggestions[session_id]
            
            # Update the profile
            profile["topic_suggestions"] = topic_suggestions
            success = user_manager.storage.write(user_manager._get_profile_path(user_id), profile)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete session topics")
            
            return {
                "success": True,
                "message": f"Deleted topics for session {session_id}",
                "session_id": session_id
            }
        else:
            return {
                "success": True,
                "message": f"No topics found for session {session_id}",
                "session_id": session_id
            }
        
    except Exception as e:
        logger.error(f"Error deleting topics for session {session_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session topics: {str(e)}")


@app.delete("/topics/cleanup")
async def cleanup_topics(
    user_id: str = Depends(get_or_create_user_id)
):
    """Clean up old and duplicate topics for the user."""
    try:
        # Get user profile
        profile = user_manager.get_user(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        topic_suggestions = profile.get("topic_suggestions", {})
        if not topic_suggestions:
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
        for session_id, topics in topic_suggestions.items():
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
                topic_suggestions[session_id] = deduplicated_topics
            else:
                sessions_to_remove.append(session_id)
                sessions_cleaned += 1
        
        # Remove empty sessions
        for session_id in sessions_to_remove:
            del topic_suggestions[session_id]
        
        # Update the profile
        profile["topic_suggestions"] = topic_suggestions
        success = user_manager.storage.write(user_manager._get_profile_path(user_id), profile)
        
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
            topic_suggestions.append({
                "index": index,
                "session_id": session_id,
                "name": topic.get("topic_name", ""),
                "description": topic.get("description", ""),
                "confidence_score": topic.get("confidence_score", 0.0),
                "suggested_at": topic.get("suggested_at", 0),
                "conversation_context": topic.get("conversation_context", ""),
                "is_active_research": topic.get("is_active_research", False)
            })
        
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


@app.delete("/topics/session/{session_id}/topic/{topic_index}")
async def delete_individual_topic(
    session_id: str,
    topic_index: int,
    user_id: str = Depends(get_or_create_user_id)
):
    """Delete an individual topic from a session."""
    try:
        # Get user profile
        profile = user_manager.get_user(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get session topics
        topic_suggestions = profile.get("topic_suggestions", {})
        session_topics = topic_suggestions.get(session_id, [])
        
        # Check if topic index is valid
        if topic_index < 0 or topic_index >= len(session_topics):
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Remove the specific topic
        deleted_topic = session_topics.pop(topic_index)
        
        # Update the profile
        if session_topics:
            topic_suggestions[session_id] = session_topics
        else:
            # Remove empty session
            del topic_suggestions[session_id]
        
        profile["topic_suggestions"] = topic_suggestions
        success = user_manager.storage.write(user_manager._get_profile_path(user_id), profile)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete topic")
        
        return {
            "success": True,
            "message": f"Deleted topic: {deleted_topic.get('topic_name', 'Unknown')}",
            "deleted_topic": {
                "name": deleted_topic.get("topic_name", ""),
                "description": deleted_topic.get("description", "")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting topic {topic_index} from session {session_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting topic: {str(e)}")


@app.post("/topics/session/{session_id}/topic/{topic_index}/enable-research")
async def enable_topic_research(
    session_id: str,
    topic_index: int,
    user_id: str = Depends(get_or_create_user_id)
):
    """Mark a topic as active research."""
    try:
        # Ensure migration from profile.json if needed
        user_manager.migrate_topics_from_profile(user_id)
        
        # Load topics data
        topics_data = user_manager.get_user_topics(user_id)
        
        # Get session topics
        session_topics = topics_data.get("sessions", {}).get(session_id, [])
        
        # Check if topic index is valid
        if topic_index < 0 or topic_index >= len(session_topics):
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Mark topic as active research
        session_topics[topic_index]["is_active_research"] = True
        session_topics[topic_index]["research_enabled_at"] = time.time()
        
        # Update the topics data
        topics_data["sessions"][session_id] = session_topics
        
        # Update metadata
        topics_data["metadata"]["active_research_topics"] = sum(
            1 for session_topics in topics_data["sessions"].values()
            for topic in session_topics
            if topic.get("is_active_research", False)
        )
        
        # Save updated topics
        success = user_manager.save_user_topics(user_id, topics_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to enable research for topic")
        
        topic_name = session_topics[topic_index].get("topic_name", "Unknown")
        
        return {
            "success": True,
            "message": f"Enabled research for topic: {topic_name}",
            "topic": {
                "name": topic_name,
                "description": session_topics[topic_index].get("description", ""),
                "is_active_research": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling research for topic {topic_index} in session {session_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error enabling research: {str(e)}")


@app.delete("/topics/session/{session_id}/topic/{topic_index}/disable-research")
async def disable_topic_research(
    session_id: str,
    topic_index: int,
    user_id: str = Depends(get_or_create_user_id)
):
    """Remove a topic from active research."""
    try:
        # Ensure migration from profile.json if needed
        user_manager.migrate_topics_from_profile(user_id)
        
        # Load topics data
        topics_data = user_manager.get_user_topics(user_id)
        
        # Get session topics
        session_topics = topics_data.get("sessions", {}).get(session_id, [])
        
        # Check if topic index is valid
        if topic_index < 0 or topic_index >= len(session_topics):
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Remove from active research
        session_topics[topic_index]["is_active_research"] = False
        session_topics[topic_index]["research_disabled_at"] = time.time()
        
        # Update the topics data
        topics_data["sessions"][session_id] = session_topics
        
        # Update metadata
        topics_data["metadata"]["active_research_topics"] = sum(
            1 for session_topics in topics_data["sessions"].values()
            for topic in session_topics
            if topic.get("is_active_research", False)
        )
        
        # Save updated topics
        success = user_manager.save_user_topics(user_id, topics_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to disable research for topic")
        
        topic_name = session_topics[topic_index].get("topic_name", "Unknown")
        
        return {
            "success": True,
            "message": f"Disabled research for topic: {topic_name}",
            "topic": {
                "name": topic_name,
                "description": session_topics[topic_index].get("description", ""),
                "is_active_research": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling research for topic {topic_index} in session {session_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error disabling research: {str(e)}")


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


@app.put("/topics/user/{user_id}/topic/{topic_name}/research")
async def enable_research_by_topic_name(
    user_id: str,
    topic_name: str,
    enable: bool = Query(True, description="True to enable, False to disable")
):
    """Enable or disable research for a topic by name (alternative to index-based API)."""
    try:
        # Load topics data
        topics_data = user_manager.get_user_topics(user_id)
        
        # Find the topic by name
        found = False
        for session_id, session_topics in topics_data.get("sessions", {}).items():
            for topic in session_topics:
                if topic.get("topic_name") == topic_name:
                    topic["is_active_research"] = enable
                    if enable:
                        topic["research_enabled_at"] = time.time()
                    else:
                        topic["research_disabled_at"] = time.time()
                    found = True
                    break
            if found:
                break
        
        if not found:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_name}' not found")
        
        # Update metadata
        topics_data["metadata"]["active_research_topics"] = sum(
            1 for session_topics in topics_data["sessions"].values()
            for topic in session_topics
            if topic.get("is_active_research", False)
        )
        
        # Save updated topics
        success = user_manager.save_user_topics(user_id, topics_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update topic research status")
        
        action = "enabled" if enable else "disabled"
        return {
            "success": True,
            "message": f"Research {action} for topic: {topic_name}",
            "topic_name": topic_name,
            "is_active_research": enable
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating research status for topic '{topic_name}', user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating research status: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 