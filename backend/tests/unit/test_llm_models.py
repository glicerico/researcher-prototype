"""
Tests for LLM models using Pydantic for structured output.
"""
import pytest
from pydantic import ValidationError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from llm_models import (
    RoutingAnalysis, 
    AnalysisTask, 
    FormattedResponse, 
    TopicSuggestions,
    TopicSuggestionItem,
    ResearchQualityAssessment,
    ResearchDeduplicationResult
)


class TestRoutingAnalysis:
    """Test RoutingAnalysis model."""

    def test_routing_analysis_valid(self):
        """Test creating valid RoutingAnalysis."""
        analysis = RoutingAnalysis(
            decision="chat",
            reason="General conversation",
            complexity=1  # int, not string
        )
        
        assert analysis.decision == "chat"
        assert analysis.reason == "General conversation"
        assert analysis.complexity == 1

    def test_routing_analysis_all_decisions(self):
        """Test all valid routing decisions."""
        valid_decisions = ["chat", "search", "analyzer"]
        
        for decision in valid_decisions:
            analysis = RoutingAnalysis(
                decision=decision,
                reason=f"Test {decision}",
                complexity=5  # int between 1-10
            )
            assert analysis.decision == decision

    def test_routing_analysis_all_complexities(self):
        """Test all valid complexity levels."""
        valid_complexities = [1, 5, 10]  # int values
        
        for complexity in valid_complexities:
            analysis = RoutingAnalysis(
                decision="chat",
                reason="Test complexity",
                complexity=complexity
            )
            assert analysis.complexity == complexity

    def test_routing_analysis_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            RoutingAnalysis()
        
        with pytest.raises(ValidationError):
            RoutingAnalysis(decision="chat")
        
        with pytest.raises(ValidationError):
            RoutingAnalysis(decision="chat", reason="Test")


class TestAnalysisTask:
    """Test AnalysisTask model."""

    def test_analysis_task_valid(self):
        """Test creating valid AnalysisTask."""
        task = AnalysisTask(
            objective="Analyze data trends",
            required_data="Historical sales data",  # correct field name
            proposed_approach="Statistical analysis method",  # correct field name
            expected_output="Summary of key trends and insights"
        )
        
        assert task.objective == "Analyze data trends"
        assert task.required_data == "Historical sales data"
        assert task.proposed_approach == "Statistical analysis method"
        assert task.expected_output == "Summary of key trends and insights"

    def test_analysis_task_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            AnalysisTask()
        
        with pytest.raises(ValidationError):
            AnalysisTask(objective="Test objective")


class TestFormattedResponse:
    """Test FormattedResponse model."""

    def test_formatted_response_minimal(self):
        """Test creating FormattedResponse with minimal required fields."""
        response = FormattedResponse(
            main_response="This is the main response"
            # sources is optional, not required
        )
        
        assert response.main_response == "This is the main response"
        assert response.sources is None
        assert response.follow_up_questions == []

    def test_formatted_response_with_sources(self):
        """Test FormattedResponse with sources."""
        sources = [
            "Source 1 - https://example.com/1",
            "Source 2 - https://example.com/2"
        ]
        
        response = FormattedResponse(
            main_response="Response with sources",
            sources=sources,
            follow_up_questions=["What about topic X?"]
        )
        
        assert response.sources == sources
        assert response.follow_up_questions == ["What about topic X?"]

    def test_formatted_response_required_fields(self):
        """Test that only main_response is required."""
        with pytest.raises(ValidationError):
            FormattedResponse()
        
        # This should work - only main_response is required
        response = FormattedResponse(main_response="Test response")
        assert response.main_response == "Test response"


class TestTopicSuggestionItem:
    """Test TopicSuggestionItem model."""

    def test_topic_suggestion_item_valid(self):
        """Test creating valid TopicSuggestionItem."""
        item = TopicSuggestionItem(
            name="AI Research",
            description="Latest developments in artificial intelligence",
            confidence_score=0.85
        )
        
        assert item.name == "AI Research"
        assert item.description == "Latest developments in artificial intelligence"
        assert item.confidence_score == 0.85

    def test_topic_suggestion_item_confidence_bounds(self):
        """Test confidence score validation."""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0]
        for score in valid_scores:
            item = TopicSuggestionItem(
                name="Test Topic",
                description="Test description",
                confidence_score=score
            )
            assert item.confidence_score == score

        # Invalid confidence scores should be handled by Pydantic validation
        with pytest.raises(ValidationError):
            TopicSuggestionItem(
                name="Test Topic",
                description="Test description", 
                confidence_score=1.5  # > 1.0
            )

    def test_topic_suggestion_item_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            TopicSuggestionItem()


class TestTopicSuggestions:
    """Test TopicSuggestions model."""

    def test_topic_suggestions_valid(self):
        """Test creating valid TopicSuggestions."""
        suggestions = TopicSuggestions(
            topics=[  # correct field name is 'topics'
                TopicSuggestionItem(
                    name="AI Research",
                    description="AI developments",
                    confidence_score=0.9
                ),
                TopicSuggestionItem(
                    name="Climate Change",
                    description="Climate research",
                    confidence_score=0.8
                )
            ]
        )
        
        assert len(suggestions.topics) == 2
        assert suggestions.topics[0].name == "AI Research"
        assert suggestions.topics[1].name == "Climate Change"

    def test_topic_suggestions_empty(self):
        """Test TopicSuggestions with empty list."""
        suggestions = TopicSuggestions(topics=[])
        assert suggestions.topics == []

    def test_topic_suggestions_required_field(self):
        """Test that topics field is required."""
        with pytest.raises(ValidationError):
            TopicSuggestions()


class TestResearchQualityAssessment:
    """Test ResearchQualityAssessment model."""

    def test_research_quality_assessment_valid(self):
        """Test creating valid ResearchQualityAssessment."""
        assessment = ResearchQualityAssessment(
            overall_quality_score=0.85,  # correct field name
            recency_score=0.9,
            relevance_score=0.8,
            depth_score=0.85,
            credibility_score=0.9,
            novelty_score=0.75,
            key_insights=["Insight 1", "Insight 2"],
            findings_summary="High quality research findings",  # correct field name
            source_urls=["https://example.com/1", "https://example.com/2"]
        )
        
        assert assessment.overall_quality_score == 0.85
        assert assessment.recency_score == 0.9
        assert len(assessment.key_insights) == 2
        assert assessment.findings_summary == "High quality research findings"

    def test_research_quality_assessment_score_bounds(self):
        """Test that scores are within valid bounds."""
        # Valid scores
        valid_assessment = ResearchQualityAssessment(
            overall_quality_score=0.0,
            recency_score=1.0,
            relevance_score=0.5,
            depth_score=0.7,
            credibility_score=0.8,
            novelty_score=0.3,
            key_insights=[],
            findings_summary="Test summary",
            source_urls=[]
        )
        assert valid_assessment.overall_quality_score == 0.0
        assert valid_assessment.recency_score == 1.0

    def test_research_quality_assessment_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            ResearchQualityAssessment()


class TestResearchDeduplicationResult:
    """Test ResearchDeduplicationResult model."""

    def test_research_deduplication_result_valid(self):
        """Test creating valid ResearchDeduplicationResult."""
        result = ResearchDeduplicationResult(
            is_duplicate=False,
            similarity_score=0.3,
            unique_aspects=["New insight 1", "New insight 2"],
            recommendation="keep"
        )
        
        assert result.is_duplicate is False
        assert result.similarity_score == 0.3
        assert len(result.unique_aspects) == 2
        assert result.recommendation == "keep"

    def test_research_deduplication_result_duplicate(self):
        """Test ResearchDeduplicationResult for duplicate case."""
        result = ResearchDeduplicationResult(
            is_duplicate=True,
            similarity_score=0.95,
            unique_aspects=[],
            recommendation="discard"
        )
        
        assert result.is_duplicate is True
        assert result.similarity_score == 0.95
        assert result.recommendation == "discard"

    def test_research_deduplication_result_recommendations(self):
        """Test valid recommendation values."""
        valid_recommendations = ["keep", "discard"]
        
        for rec in valid_recommendations:
            result = ResearchDeduplicationResult(
                is_duplicate=False,
                similarity_score=0.5,
                unique_aspects=["Some aspect"],
                recommendation=rec
            )
            assert result.recommendation == rec

    def test_research_deduplication_result_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            ResearchDeduplicationResult() 