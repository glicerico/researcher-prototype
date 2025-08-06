from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from config import DEFAULT_MODEL


class PersonalityConfig(BaseModel):
    """Configuration for AI personality."""
    style: str = "helpful"
    tone: str = "friendly"
    additional_traits: Optional[Dict[str, Any]] = {}


class ContentPreferences(BaseModel):
    """User content preferences."""
    research_depth: str = "balanced"  # quick, balanced, detailed
    source_types: Dict[str, float] = {
        "academic_papers": 0.7,
        "news_articles": 0.8,
        "expert_blogs": 0.7,
        "government_reports": 0.6,
        "industry_reports": 0.6
    }
    topic_categories: Dict[str, float] = {}


class FormatPreferences(BaseModel):
    """User format preferences."""
    response_length: str = "medium"  # short, medium, long
    detail_level: str = "balanced"  # concise, balanced, comprehensive
    citation_style: str = "inline"  # inline, numbered, bibliography
    use_bullet_points: bool = True
    include_key_insights: bool = True


class InteractionPreferences(BaseModel):
    """User interaction preferences."""
    follow_up_questions: bool = True
    proactive_research: bool = True
    notification_frequency: str = "moderate"  # low, moderate, high


class PreferencesConfig(BaseModel):
    """Complete user preferences configuration."""
    content_preferences: ContentPreferences = ContentPreferences()
    format_preferences: FormatPreferences = FormatPreferences()
    interaction_preferences: InteractionPreferences = InteractionPreferences()


class ReadingPatterns(BaseModel):
    """User reading pattern analytics."""
    avg_reading_time_seconds: Dict[str, float] = {
        "short_responses": 0.0,
        "medium_responses": 0.0,
        "long_responses": 0.0
    }
    content_completion_rates: Dict[str, float] = {
        "research_findings": 0.0,
        "chat_responses": 0.0
    }


class InteractionSignals(BaseModel):
    """User interaction signals."""
    topics_initiated_by_user: List[str] = []
    most_engaged_source_types: List[str] = []
    preferred_research_timing: Optional[str] = None
    follow_up_question_frequency: float = 0.0


class FormatOptimizations(BaseModel):
    """Learned format optimizations."""
    prefers_structured_responses: Optional[bool] = None
    optimal_response_length: Optional[int] = None


class LearnedAdaptations(BaseModel):
    """Learned user adaptations."""
    tone_adjustments: Dict[str, str] = {}
    format_optimizations: FormatOptimizations = FormatOptimizations()


class EngagementAnalytics(BaseModel):
    """User engagement analytics."""
    reading_patterns: ReadingPatterns = ReadingPatterns()
    interaction_signals: InteractionSignals = InteractionSignals()
    learned_adaptations: LearnedAdaptations = LearnedAdaptations()
    user_overrides: Dict[str, Any] = {}


class AdaptationLogEntry(BaseModel):
    """Single adaptation log entry."""
    timestamp: float
    adaptation_type: str
    change_made: str
    changes_detail: Optional[Dict[str, Any]] = None
    user_feedback: Optional[str] = None
    effectiveness_score: Optional[float] = None


class PreferenceEvolution(BaseModel):
    """Preference evolution tracking."""
    source_type_preferences: List[Dict[str, Any]] = []
    format_preferences: List[Dict[str, Any]] = []
    content_preferences: List[Dict[str, Any]] = []


class PersonalizationHistory(BaseModel):
    """User personalization history."""
    adaptation_log: List[AdaptationLogEntry] = []
    preference_evolution: PreferenceEvolution = PreferenceEvolution()


class PersonalizationContext(BaseModel):
    """Personalization context for request processing."""
    content_preferences: ContentPreferences
    format_preferences: FormatPreferences  
    interaction_preferences: InteractionPreferences
    learned_adaptations: LearnedAdaptations
    engagement_patterns: Dict[str, Any]


class PreferenceOverride(BaseModel):
    """Request to override a learned preference."""
    preference_type: str
    override_value: Any
    disable_learning: bool = False


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
    preferences: Optional[PreferencesConfig] = None