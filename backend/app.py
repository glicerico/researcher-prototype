from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import and configure logging first, before other imports
from logging_config import configure_logging, get_logger

# Configure application logging
logger = configure_logging()

# Now import other modules that might use logging
from models import ChatRequest, ChatResponse, Message, PersonalityConfig, UserSummary, UserProfile, ConversationSummary, ConversationDetail
from graph_builder import chat_graph, get_langsmith_client
from nodes.base import user_manager, conversation_manager
from nodes.router_node import router_node
import config
import traceback
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

app = FastAPI(title="Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify the actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get a module-specific logger
logger = get_logger(__name__)

# Helper function to get user_id from header with fallback to creating new user
async def get_user_id(x_user_id: Optional[str] = Header(None)):
    """Get or create a user ID."""
    if x_user_id and user_manager.user_exists(x_user_id):
        return x_user_id
    
    # Create a new user if none provided or invalid
    new_user_id = user_manager.create_user()
    logger.info(f"Created new user with ID: {new_user_id}")
    return new_user_id


# Models for API requests/responses
class ConversationSummary(BaseModel):
    conversation_id: str
    created_at: float
    updated_at: float
    metadata: Optional[Dict[str, Any]] = {}
    message_count: int


class ConversationDetail(BaseModel):
    conversation_id: str
    user_id: str
    created_at: float
    updated_at: float
    metadata: Optional[Dict[str, Any]] = {}
    messages: List[Dict[str, Any]]


class UserProfile(BaseModel):
    user_id: str
    created_at: float
    personality: PersonalityConfig
    metadata: Optional[Dict[str, Any]] = {}
    display_name: Optional[str] = None  # Add display_name at the top-level for consistency


@app.get("/")
async def root():
    return {"message": "Chatbot API is running"}


@app.get("/models")
async def get_models():
    return {"models": config.SUPPORTED_MODELS}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
    conversation_id: Optional[str] = Header(None)
):
    try:
        # Log the incoming request
        logger.debug(f"Chat request: {request}")
        
        # Prepare the state for the graph
        state = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "personality": request.personality.dict() if request.personality else None,
            "current_module": None,
            "module_results": {},
            "workflow_context": {},
            "user_id": user_id,
            "conversation_id": conversation_id
        }
        
        # Save user's personality if provided
        if request.personality:
            user_manager.update_personality(user_id, request.personality.dict())
        
        # Run the graph
        result = chat_graph.invoke(state)
        
        # Check for errors
        if "error" in result:
            raise Exception(result["error"])
        
        # Extract the assistant's response (the last message)
        assistant_message = result["messages"][-1]
        
        return ChatResponse(
            response=assistant_message["content"],
            model=request.model,
            usage={},
            module_used=result.get("current_module", "unknown"),
            routing_analysis=result.get("routing_analysis")
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug")
async def debug(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
    conversation_id: Optional[str] = Header(None)
):
    """Debug endpoint to check what's happening with the request."""
    try:
        # Prepare the state for the graph (same as in chat endpoint)
        state = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "personality": request.personality.dict() if request.personality else None,
            "current_module": None,
            "module_results": {},
            "workflow_context": {},
            "user_id": user_id,
            "conversation_id": conversation_id
        }
        
        # For debug only: process just the routing part
        routing_result = router_node(state.copy())
        
        return {
            "request_received": True,
            "initial_state": state,
            "api_key_set": bool(config.OPENAI_API_KEY),
            "model": request.model,
            "router_model": config.ROUTER_MODEL,
            "routing_result": {
                "decision": routing_result.get("current_module"),
                "full_analysis": routing_result.get("routing_analysis"),
            },
            "supported_models": config.SUPPORTED_MODELS
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/personality-presets")
async def get_personality_presets():
    """Return predefined personality presets that users can choose from."""
    presets = {
        "default": PersonalityConfig(style="helpful", tone="friendly"),
        "professional": PersonalityConfig(style="expert", tone="professional"),
        "creative": PersonalityConfig(style="creative", tone="enthusiastic"),
        "concise": PersonalityConfig(style="concise", tone="direct"),
    }
    
    # Convert to dict for JSON response
    return {
        "presets": {k: v.dict() for k, v in presets.items()}
    }


# User management endpoints
@app.get("/users/me", response_model=UserProfile)
async def get_current_user(user_id: str = Depends(get_user_id)):
    """Get the current user's profile."""
    user_data = user_manager.get_user(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert personality to the right format
    if "personality" in user_data:
        personality = PersonalityConfig(**user_data["personality"])
    else:
        personality = PersonalityConfig()
    
    # Get display name from metadata
    metadata = user_data.get("metadata", {})
    display_name = metadata.get("display_name", f"User {user_id[-6:]}")
    
    return UserProfile(
        user_id=user_data["user_id"],
        created_at=user_data.get("created_at", 0),
        personality=personality,
        metadata=user_data.get("metadata", {}),
        display_name=display_name
    )


@app.patch("/users/me/personality")
async def update_user_personality(
    personality: PersonalityConfig,
    user_id: str = Depends(get_user_id)
):
    """Update the current user's personality."""
    success = user_manager.update_personality(user_id, personality.dict())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update personality")
    
    return {"success": True, "personality": personality}


# New endpoint to list all users with basic info
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
            
            # Get a display name (use metadata or fallback to part of UUID)
            metadata = user_data.get("metadata", {})
            display_name = metadata.get("display_name", f"User {user_id[-6:]}")
            
            # Count conversations
            conversations = conversation_manager.list_conversations(user_id)
            
            user_summaries.append(UserSummary(
                user_id=user_id,
                created_at=user_data.get("created_at", 0),
                personality=personality_config,
                display_name=display_name,
                conversation_count=len(conversations)
            ))
    
    # Sort by most recently created
    user_summaries.sort(key=lambda x: x.created_at, reverse=True)
    
    return user_summaries


# Endpoint to create a new user with display name
@app.post("/users", response_model=UserProfile)
async def create_user(display_name: Optional[str] = None):
    """Create a new user with an optional display name."""
    metadata = {}
    if display_name:
        metadata["display_name"] = display_name
        
    user_id = user_manager.create_user(metadata)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    return await get_current_user(user_id)


# Update user display name
@app.patch("/users/{user_id}/display-name", response_model=UserProfile)
async def update_user_display_name(user_id: str, display_name: str):
    """Update a user's display name."""
    if not user_manager.user_exists(user_id):
        raise HTTPException(status_code=404, detail="User not found")
        
    success = user_manager.update_user(user_id, {"metadata": {"display_name": display_name}})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update display name")
    
    # Return the full user profile for consistency
    return await get_current_user(user_id)


# Conversation management endpoints
@app.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations(
    user_id: str = Depends(get_user_id),
    limit: int = Query(10, ge=1, le=100)
):
    """Get the user's conversations."""
    conversations = conversation_manager.list_conversations(user_id)
    return conversations[:limit]


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id)
):
    """Get a specific conversation."""
    conversation = conversation_manager.get_conversation(user_id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@app.post("/conversations")
async def create_conversation(
    name: Optional[str] = None,
    user_id: str = Depends(get_user_id)
):
    """Create a new conversation."""
    metadata = {}
    if name:
        metadata["name"] = name
    
    conversation_id = conversation_manager.create_conversation(user_id, metadata)
    if not conversation_id:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    
    return {
        "success": True,
        "conversation_id": conversation_id
    }


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id)
):
    """Delete a conversation."""
    success = conversation_manager.delete_conversation(user_id, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found or couldn't be deleted")
    
    return {"success": True, "message": f"Conversation {conversation_id} deleted"}


@app.get("/traces")
async def get_traces(limit: int = Query(10, ge=1, le=100)):
    """Get recent LangSmith traces if tracing is enabled."""
    langsmith_client = get_langsmith_client()
    if not langsmith_client:
        return {
            "error": "LangSmith tracing is not enabled",
            "enabled": False,
            "setup_instructions": "Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in your .env file"
        }
    
    try:
        # Get traces from LangSmith
        trace_project = config.LANGCHAIN_PROJECT
        traces = langsmith_client.list_runs(
            project_name=trace_project,
            limit=limit
        )
        
        # Format for API response
        trace_data = []
        for trace in traces:
            trace_data.append({
                "id": trace.id,
                "name": trace.name,
                "start_time": trace.start_time.isoformat() if trace.start_time else None,
                "end_time": trace.end_time.isoformat() if trace.end_time else None,
                "status": trace.status,
                "error": trace.error,
                "url": f"{config.LANGCHAIN_ENDPOINT}/projects/{trace_project}/r/{trace.id}"
            })
        
        return {
            "enabled": True,
            "project": trace_project,
            "traces": trace_data,
            "langsmith_url": f"{config.LANGCHAIN_ENDPOINT}/projects/{trace_project}"
        }
    except Exception as e:
        logger.error(f"Error fetching LangSmith traces: {str(e)}", exc_info=True)
        return {
            "enabled": True,
            "error": str(e),
            "message": "Failed to fetch traces from LangSmith"
        }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    ) 