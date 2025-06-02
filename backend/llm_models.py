from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class RoutingAnalysis(BaseModel):
    """Analysis for router to determine which module to use."""
    decision: str = Field(description="The chosen module name (chat, search, or analyzer)")
    reason: str = Field(description="A brief explanation of why this module was chosen")
    complexity: int = Field(description="Rate the complexity from 1-10 (1=very simple, 10=very complex)")


class SearchQuery(BaseModel):
    """Refined search query optimized for search engines."""
    query: str = Field(description="The optimized search query based on the user's question. Should be concise, focused on keywords, and contain the essential information needed for search.")
    search_type: str = Field(description="The type of search this is: 'factual' for facts and information, 'news' for current events, 'concept' for explanations of ideas or concepts")


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
        max_length=5  # Limit to max 5 topics as specified in config
    )
    
    @field_validator('topics')
    def validate_topics(cls, v):
        # Ensure we don't exceed the maximum number of topics
        if len(v) > 5:
            return v[:5]  # Limit to maximum 5 topics
        return v


class FormattedResponse(BaseModel):
    """Formatted assistant response with proper style and tone."""
    main_response: str = Field(description="The formatted main response content, styled according to the specified tone and style")
    follow_up_questions: Optional[List[str]] = Field(
        default=None, 
        description="Optional list of 1-2 relevant follow-up questions that naturally extend from the response content. Only include if they add value."
    )
    
    @field_validator('follow_up_questions')
    def validate_follow_up_questions(cls, v):
        if v and len(v) > 2:
            return v[:2]  # Limit to maximum 2 questions
        return v 