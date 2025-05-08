from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    role: str
    content: str


class PersonalityConfig(BaseModel):
    """Configuration for the user's personality settings."""
    style: Optional[str] = "helpful"  # helpful, concise, expert, creative, etc.
    tone: Optional[str] = "friendly"  # friendly, professional, casual, enthusiastic, direct, etc.
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
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1000
    stream: Optional[bool] = False
    personality: Optional[PersonalityConfig] = None


class RoutingAnalysis(BaseModel):
    decision: str
    reason: str
    complexity: Optional[int] = None
    model_used: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Dict[str, Any] = {}
    module_used: str = "chat"
    routing_analysis: Optional[RoutingAnalysis] = None 