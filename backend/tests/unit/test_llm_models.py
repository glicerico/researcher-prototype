import pytest
from pydantic import ValidationError
from llm_models import (
    MultiSourceAnalysis, 
    AnalysisTask,
    TopicSuggestions,
    TopicSuggestionItem,
    FormattedResponse,
    ResearchQualityAssessment,
    ResearchDeduplicationResult,
    SearchOptimization
)


class TestMultiSourceAnalysis:
    """Test MultiSourceAnalysis model."""

    def test_valid_multi_source_analysis(self):
        """Test creating valid MultiSourceAnalysis."""
        analysis = MultiSourceAnalysis(
            intent="search",
            reason="User needs current information",
            sources=["search", "academic_search"]
        )
        
        assert analysis.intent == "search"
        assert analysis.reason == "User needs current information"
        assert analysis.sources == ["search", "academic_search"]

    def test_multi_source_analysis_chat_intent(self):
        """Test chat intent with no sources."""
        analysis = MultiSourceAnalysis(
            intent="chat",
            reason="General conversation"
        )
        
        assert analysis.intent == "chat"
        assert analysis.sources == []

    def test_multi_source_analysis_missing_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            MultiSourceAnalysis()

        with pytest.raises(ValidationError):
            MultiSourceAnalysis(intent="chat")


class TestAnalysisTask:
    """Test AnalysisTask model."""

    def test_valid_analysis_task(self):
        """Test creating valid AnalysisTask."""
        task = AnalysisTask(
            objective="Analyze sales data trends",
            required_data="Monthly sales figures for 2023",
            proposed_approach="Statistical trend analysis with visualization",
            expected_output="Report with charts and key insights"
        )
        
        assert task.objective == "Analyze sales data trends"
        assert task.required_data == "Monthly sales figures for 2023"
        assert task.proposed_approach == "Statistical trend analysis with visualization"
        assert task.expected_output == "Report with charts and key insights"

    def test_analysis_task_missing_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            AnalysisTask()

        with pytest.raises(ValidationError):
            AnalysisTask(objective="Test objective")


class TestTopicSuggestions:
    """Test TopicSuggestions model."""

    def test_valid_topic_suggestions(self):
        """Test creating valid TopicSuggestions."""
        topics = [
            TopicSuggestionItem(name="AI Research", description="Latest developments", confidence_score=0.8),
            TopicSuggestionItem(name="Climate Change", description="Environmental impacts", confidence_score=0.7)
        ]
        suggestions = TopicSuggestions(topics=topics)
        
        assert len(suggestions.topics) == 2
        assert suggestions.topics[0].name == "AI Research"
        assert suggestions.topics[1].confidence_score == 0.7

    def test_topic_suggestions_max_limit(self):
        """Test that topic suggestions are limited to maximum."""
        # Create 6 topics (more than max 5)
        topics = [
            TopicSuggestionItem(name=f"Topic {i}", description=f"Desc {i}", confidence_score=0.8)
            for i in range(6)
        ]
        suggestions = TopicSuggestions(topics=topics)
        
        # Should be limited to 5
        assert len(suggestions.topics) <= 5


class TestFormattedResponse:
    """Test FormattedResponse model."""

    def test_valid_formatted_response(self):
        """Test creating valid FormattedResponse."""
        response = FormattedResponse(
            main_response="This is the main response content",
            follow_up_questions=["Question 1?", "Question 2?"],
            sources=["Source 1", "Source 2"]
        )
        
        assert response.main_response == "This is the main response content"
        assert len(response.follow_up_questions) == 2
        assert len(response.sources) == 2

    def test_formatted_response_follow_up_limit(self):
        """Test that follow-up questions are limited."""
        response = FormattedResponse(
            main_response="Test response",
            follow_up_questions=["Q1?", "Q2?", "Q3?"]  # 3 questions, should be limited to 2
        )
        
        assert len(response.follow_up_questions) <= 2


class TestResearchQualityAssessment:
    """Test ResearchQualityAssessment model."""

    def test_valid_quality_assessment(self):
        """Test creating valid ResearchQualityAssessment."""
        assessment = ResearchQualityAssessment(
            overall_quality_score=0.8,
            recency_score=0.9,
            relevance_score=0.7,
            depth_score=0.6,
            credibility_score=0.8,
            novelty_score=0.5,
            key_insights=["Insight 1", "Insight 2"],
            source_urls=["http://example.com"],
            findings_summary="Summary of key findings"
        )
        
        assert assessment.overall_quality_score == 0.8
        assert len(assessment.key_insights) == 2
        assert assessment.findings_summary == "Summary of key findings"

    def test_quality_assessment_score_validation(self):
        """Test that scores are within valid range."""
        # Valid scores
        assessment = ResearchQualityAssessment(
            overall_quality_score=0.5,
            recency_score=0.0,
            relevance_score=1.0,
            depth_score=0.7,
            credibility_score=0.3,
            novelty_score=0.9,
            key_insights=["Test insight"],
            findings_summary="Test summary"
        )
        
        assert 0.0 <= assessment.overall_quality_score <= 1.0
        assert 0.0 <= assessment.recency_score <= 1.0
        assert 0.0 <= assessment.relevance_score <= 1.0


class TestSearchOptimization:
    """Test SearchOptimization model."""

    def test_valid_search_optimization(self):
        """Test creating valid SearchOptimization."""
        optimization = SearchOptimization(
            query="optimized search query",
            recency_filter="month",
            search_mode="academic",
            context_size="high",
            confidence={"recency_filter": 0.8, "search_mode": 0.9}
        )
        
        assert optimization.query == "optimized search query"
        assert optimization.recency_filter == "month"
        assert optimization.search_mode == "academic"
        assert optimization.context_size == "high"

    def test_search_optimization_invalid_values(self):
        """Test that invalid enum values are handled."""
        optimization = SearchOptimization(
            query="test query",
            recency_filter="invalid_filter",  # Should be set to None
            search_mode="invalid_mode",  # Should be set to None
            context_size="invalid_size"  # Should be set to None
        )
        
        assert optimization.recency_filter is None
        assert optimization.search_mode is None
        assert optimization.context_size is None


class TestResearchDeduplicationResult:
    """Test ResearchDeduplicationResult model."""

    def test_valid_deduplication_result(self):
        """Test creating valid ResearchDeduplicationResult."""
        result = ResearchDeduplicationResult(
            is_duplicate=False,
            similarity_score=0.3,
            unique_aspects=["Novel approach", "Different methodology"],
            recommendation="keep"
        )
        
        assert result.is_duplicate is False
        assert result.similarity_score == 0.3
        assert len(result.unique_aspects) == 2
        assert result.recommendation == "keep"

    def test_deduplication_result_recommendation_validation(self):
        """Test that invalid recommendations are handled."""
        result = ResearchDeduplicationResult(
            is_duplicate=True,
            similarity_score=0.9,
            unique_aspects=[],
            recommendation="invalid_recommendation"  # Should default to "keep"
        )
        
        assert result.recommendation == "keep"