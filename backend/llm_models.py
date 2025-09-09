"""
Pydantic models for LLM structured output parsing.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict



class MultiSourceAnalysis(BaseModel):
    """Structured output for multi-source search analysis."""
    intent: str = Field(description="The intent classification: chat, search, or analysis")
    reason: str = Field(description="Brief explanation of why this intent was selected")
    sources: List[str] = Field(default=[], description="List of sources to execute for search intent: search, academic_search, social_search, medical_search")


class AnalysisTask(BaseModel):
    """Structured analysis task description."""
    objective: str = Field(description="The primary objective of the analysis task")
    required_data: str = Field(description="Description of what data or information is needed to complete the analysis")
    proposed_approach: str = Field(description="The recommended approach to analyze the data and complete the task")
    expected_output: str = Field(description="The format and content of the expected output from the analysis")


class TopicSuggestionItem(BaseModel):
    """A single research-worthy topic suggestion."""
    name: str = Field(description="A concise, descriptive name for the topic (2-6 words)")
    description: str = Field(description="A brief explanation of what research would cover (1-2 sentences)")
    confidence_score: float = Field(description="Float between 0.0-1.0 indicating how research-worthy this topic is", ge=0.0, le=1.0)
    staleness_coefficient: float = Field(
        description="How quickly research pressure builds for this topic (0.1=very slow, 1.0=normal, 2.0=urgent)", 
        ge=0.1, 
        le=2.0,
        default=1.0
    )


class TopicSuggestions(BaseModel):
    """Collection of research-worthy topics extracted from conversation."""
    topics: List[TopicSuggestionItem] = Field(
        description="List of research-worthy topics extracted from the conversation",
        json_schema_extra={"max_length": 5}  # Limit to max 5 topics as specified in config
    )
    
    @field_validator('topics')
    def validate_topics(cls, v):
        # Ensure we don't exceed the maximum number of topics
        if len(v) > 5:
            return v[:5]  # Limit to maximum 5 topics
        return v


class FormattedResponse(BaseModel):
    """A formatted response with optional follow-up questions and sources."""
    main_response: str = Field(description="The main, formatted response content.")
    follow_up_questions: List[str] = Field(
        description="A list of 1-2 relevant follow-up questions phrased as if the user is asking them (e.g., 'What are the key benefits of this approach?' rather than 'Would you like to know about the key benefits?').",
        default_factory=list
    )
    sources: Optional[List[str]] = Field(
        description="Optional list of source citations or references.",
        default=None
    )
    
    @field_validator('follow_up_questions')
    def validate_follow_up_questions(cls, v):
        if v and len(v) > 2:
            return v[:2]  # Limit to maximum 2 questions
        return v


class ResearchQualityAssessment(BaseModel):
    """Quality assessment for research findings."""
    overall_quality_score: float = Field(description="Overall quality score from 0.0 (poor) to 1.0 (excellent)", ge=0.0, le=1.0)
    recency_score: float = Field(description="How recent and up-to-date the information is from 0.0 to 1.0", ge=0.0, le=1.0)
    relevance_score: float = Field(description="How well the content matches the research topic from 0.0 to 1.0", ge=0.0, le=1.0)
    depth_score: float = Field(description="How comprehensive and detailed the information is from 0.0 to 1.0", ge=0.0, le=1.0)
    credibility_score: float = Field(description="How trustworthy and authoritative the sources are from 0.0 to 1.0", ge=0.0, le=1.0)
    novelty_score: float = Field(description="How new or unique the information is compared to common knowledge from 0.0 to 1.0", ge=0.0, le=1.0)
    key_insights: List[str] = Field(description="List of key insights extracted from the research findings", json_schema_extra={"max_length": 5})
    source_urls: List[str] = Field(description="List of source URLs mentioned in the findings", default_factory=list, json_schema_extra={"max_length": 10})
    findings_summary: str = Field(description="Brief summary of the key findings (1-3 sentences)")
    
    @field_validator('key_insights')
    def validate_key_insights(cls, v):
        if len(v) > 5:
            return v[:5]  # Limit to maximum 5 insights
        return v
    
    @field_validator('source_urls')
    def validate_source_urls(cls, v):
        if len(v) > 10:
            return v[:10]  # Limit to maximum 10 URLs
        return v


class SearchOptimization(BaseModel):
    """Optimized search query with parameters and confidences."""
    query: str = Field(description="The optimized search query")
    social_query: Optional[str] = Field(
        description="Hacker News optimized query (only when social_search is selected)",
        default=None
    )
    academic_query: Optional[str] = Field(
        description="OpenAlex optimized query (only when academic_search is selected)",
        default=None
    )
    recency_filter: Optional[str] = Field(
        description="Recency filter preference: 'week' | 'month' | 'year' | null",
        default=None
    )
    search_mode: Optional[str] = Field(
        description="Preferred search mode based on intent and profile: 'web' | 'academic' | null",
        default=None
    )
    context_size: Optional[str] = Field(
        description="Preferred web search context size: 'low' | 'medium' | 'high' | null",
        default=None
    )
    confidence: Optional[Dict[str, float]] = Field(
        description="Confidence per decision key: recency_filter, search_mode, context_size (0.0-1.0)",
        default_factory=dict
    )

    @field_validator('recency_filter')
    def validate_recency_filter(cls, v):
        if v is not None and v not in ['week', 'month', 'year']:
            return None  # Default to no filter if invalid
        return v

    @field_validator('search_mode')
    def validate_search_mode(cls, v):
        if v is not None and v not in ['web', 'academic']:
            return None
        return v

    @field_validator('context_size')
    def validate_context_size(cls, v):
        if v is not None and v not in ['low', 'medium', 'high']:
            return None
        return v

    @field_validator('confidence')
    def validate_confidence(cls, v: Dict[str, float]):
        if not v:
            return {}
        clamped: Dict[str, float] = {}
        for key, value in v.items():
            try:
                clamped[key] = max(0.0, min(1.0, float(value)))
            except Exception:
                continue
        return clamped


class ResearchDeduplicationResult(BaseModel):
    """Result of research findings deduplication analysis."""
    is_duplicate: bool = Field(description="True if the new findings are substantially similar to existing ones")
    similarity_score: float = Field(description="Similarity score from 0.0 (completely different) to 1.0 (identical)", ge=0.0, le=1.0)
    unique_aspects: List[str] = Field(description="List of unique elements in the new findings that add value", json_schema_extra={"max_length": 5})
    recommendation: str = Field(description="Recommendation: 'keep' if findings add value, 'discard' if too similar")
    
    @field_validator('recommendation')
    def validate_recommendation(cls, v):
        if v.lower() not in ['keep', 'discard']:
            return 'keep'  # Default to keep if invalid recommendation
        return v.lower()
    
    @field_validator('unique_aspects')
    def validate_unique_aspects(cls, v):
        if len(v) > 5:
            return v[:5]  # Limit to maximum 5 aspects
        return v 


class RelevanceFilterDecision(BaseModel):
    """Structured model for relevance filtering decisions per source."""
    filtered_content: str = Field(description="The filtered, still-formatted content to use for this source.")
    kept_count: int = Field(description="Approximate number of items retained after filtering", ge=0)
    reason: Optional[str] = Field(description="Optional short note on filtering rationale", default=None)


class RelevanceSelection(BaseModel):
    """Indices-based relevance selection to avoid text regeneration risk."""
    selected_indices: List[int] = Field(description="Zero-based indices of relevant items from the provided list")
    reason: Optional[str] = Field(description="Optional short rationale for the selection", default=None)


class EvidenceSummary(BaseModel):
    """Model for evidence summarizer output."""
    summary_text: str = Field(description="Concise summary with citation markers")