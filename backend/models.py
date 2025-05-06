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