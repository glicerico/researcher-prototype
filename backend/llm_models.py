"""
Pydantic models for LLM structured output parsing.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class RoutingAnalysis(BaseModel):
    """Analysis of user input to route to appropriate module."""
    decision: str = Field(description="The routing decision: 'chat', 'search', or 'analyzer'")
    reason: str = Field(description="Brief explanation of why this routing decision was made")
    complexity: int = Field(description="Estimated complexity level as integer from 1 (simple) to 10 (complex)", ge=1, le=10)


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