from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from config import DEFAULT_MODEL


class PersonalityConfig(BaseModel):
    """Configuration for AI personality."""
    style: str = "helpful"
    tone: str = "friendly"
    additional_traits: Optional[Dict[str, Any]] = {}


class Message(BaseModel):
    """A chat message."""
    role: str
    content: str


class TopicSuggestion(BaseModel):
    """A suggested research topic extracted from conversation."""
    name: str
    description: str
    confidence_score: float


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    messages: List[Message]
    model: str = DEFAULT_MODEL
    temperature: float = 0.7
    max_tokens: int = 1000
    personality: Optional[PersonalityConfig] = None
    session_id: Optional[str] = None  # Optional session ID for conversation continuity


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    model: str
    usage: Dict[str, Any] = {}
    module_used: Optional[str] = None
    routing_analysis: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None  # Return the session ID used
    suggested_topics: List[TopicSuggestion] = []  # Research-worthy topics from conversation
    follow_up_questions: List[str] = []  # Optional follow up questions


class UserSummary(BaseModel):
    """Summary of a user profile for list views."""
    user_id: str
    created_at: float
    personality: PersonalityConfig  # Use the same structure as in UserProfile
    display_name: Optional[str] = None  # Keep this at the top-level for convenience
    # Any additional metadata can be included as needed


class UserProfile(BaseModel):
    """Complete user profile information."""
    user_id: str
    created_at: float
    metadata: Optional[Dict[str, Any]] = {}
    personality: PersonalityConfig 