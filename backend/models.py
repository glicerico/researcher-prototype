from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    role: str
    content: str


class PersonalityConfig(BaseModel):
    """Configuration for the user's personality settings."""
    style: Optional[str] = "helpful"  # e.g., "helpful", "concise", "expert", "creative"
    tone: Optional[str] = "friendly"  # e.g., "friendly", "professional", "casual"
    additional_traits: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserProfile(BaseModel):
    """Complete user profile information."""
    user_id: str
    created_at: float
    personality: PersonalityConfig
    metadata: Optional[Dict[str, Any]] = {}
    display_name: Optional[str] = None


class UserSummary(BaseModel):
    """Summary of a user profile for list views."""
    user_id: str
    created_at: float
    personality: PersonalityConfig  # Use the same structure as in UserProfile
    display_name: Optional[str] = None  # Keep this at the top-level for convenience
    conversation_count: int
    # Any additional metadata can be included as needed


class ConversationSummary(BaseModel):
    """Summary of a conversation for list views."""
    conversation_id: str
    created_at: float
    updated_at: float
    metadata: Optional[Dict[str, Any]] = {}
    message_count: int


class ConversationDetail(BaseModel):
    """Detailed conversation information including messages."""
    conversation_id: str
    user_id: str
    created_at: float
    updated_at: float
    metadata: Optional[Dict[str, Any]] = {}
    messages: List[Dict[str, Any]]


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = "gpt-4o-mini"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False
    personality: Optional[PersonalityConfig] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    module_used: Optional[str] = None  # Which module handled the request 