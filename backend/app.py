from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import traceback
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 