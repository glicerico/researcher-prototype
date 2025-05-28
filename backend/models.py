from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class PersonalityConfig(BaseModel):
    """Configuration for AI personality."""
    style: str = "helpful"
    tone: str = "friendly"
    additional_traits: Optional[Dict[str, Any]] = {}


class Message(BaseModel):
    """A chat message."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    messages: List[Message]
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1000
    personality: Optional[PersonalityConfig] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    model: str
    usage: Dict[str, Any] = {}
    module_used: Optional[str] = None
    routing_analysis: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


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