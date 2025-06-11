import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.topics import router
from fastapi import FastAPI
from dependencies import get_or_create_user_id

# Create test app
app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_research_manager():
    """Create a mock research manager for testing."""
    return MagicMock()


@pytest.fixture
def client():
    """Create test client with dependency override."""
    def get_test_user_id():
        return "test_user"
    
    app.dependency_overrides[get_or_create_user_id] = get_test_user_id
    client = TestClient(app)
    yield client
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_topics_data():
    """Sample topics data for testing."""
    current_time = time.time()
    return [
        {
            "topic_id": "topic_1",
            "topic_name": "AI Research",
            "description": "Latest developments in artificial intelligence",
            "confidence_score": 0.9,
            "suggested_at": current_time - 3600,  # 1 hour ago
            "conversation_context": "Discussion about AI",
            "is_active_research": True,
        },
        {
            "topic_id": "topic_2", 
            "topic_name": "Climate Change",
            "description": "Environmental impact and solutions",
            "confidence_score": 0.8,
            "suggested_at": current_time - 1800,  # 30 minutes ago
            "conversation_context": "Environmental conversation",
            "is_active_research": False,
        },
    ]


@pytest.fixture
def sample_all_topics_data():
    """Sample data for all topics across sessions."""
    current_time = time.time()
    return {
        "session_1": [
            {
                "topic_id": "topic_1",
                "topic_name": "AI Research",
                "description": "Latest developments in artificial intelligence",
                "confidence_score": 0.9,
                "suggested_at": current_time - 3600,
                "conversation_context": "Discussion about AI",
                "is_active_research": True,
            }
        ],
        "session_2": [
            {
                "topic_id": "topic_2",
                "topic_name": "Climate Change", 
                "description": "Environmental impact and solutions",
                "confidence_score": 0.8,
                "suggested_at": current_time - 1800,
                "conversation_context": "Environmental conversation",
                "is_active_research": False,
            }
        ],
    }


class TestGetTopicSuggestions:
    """Test getting topic suggestions for a session."""

    def test_get_topic_suggestions_success(self, client, mock_research_manager, sample_topics_data):
        """Test successful retrieval of topic suggestions."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = sample_topics_data
            
            response = client.get("/topics/suggestions/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["session_id"] == "test_session"
            assert data["user_id"] == "test_user"
            assert data["total_count"] == 2
            assert len(data["topic_suggestions"]) == 2
            
            # Check first topic (should be newest first due to sorting)
            topic = data["topic_suggestions"][0]
            assert topic["topic_id"] == "topic_2"  # Newest first
            assert topic["name"] == "Climate Change"
            assert topic["confidence_score"] == 0.8
            assert topic["is_active_research"] is False
            
            mock_research_manager.get_topic_suggestions.assert_called_once_with("test_user", "test_session")

    def test_get_topic_suggestions_legacy_id_handling(self, client, mock_research_manager):
        """Test handling of topics missing topic_id (legacy compatibility)."""
        legacy_topics = [
            {
                "topic_name": "Legacy Topic",
                "description": "A topic without ID",
                "confidence_score": 0.7,
                "suggested_at": time.time(),
                "conversation_context": "Legacy context",
                "is_active_research": False,
            }
        ]
        
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = legacy_topics
            
            response = client.get("/topics/suggestions/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            topic = data["topic_suggestions"][0]
            assert topic["topic_id"] == "legacy_test_session_0"
            assert topic["name"] == "Legacy Topic"

    def test_get_topic_suggestions_empty_results(self, client, mock_research_manager):
        """Test getting topic suggestions when none exist."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = []
            
            response = client.get("/topics/suggestions/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 0
            assert data["topic_suggestions"] == []

    def test_get_topic_suggestions_error_handling(self, client, mock_research_manager):
        """Test error handling in get topic suggestions."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.side_effect = Exception("Database error")
            
            response = client.get("/topics/suggestions/test_session")
            
            assert response.status_code == 500
            assert "Error retrieving topic suggestions" in response.json()["detail"]


class TestGetAllTopicSuggestions:
    """Test getting all topic suggestions across sessions."""

    def test_get_all_topic_suggestions_success(self, client, mock_research_manager, sample_all_topics_data):
        """Test successful retrieval of all topic suggestions."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_all_topic_suggestions.return_value = sample_all_topics_data
            
            response = client.get("/topics/suggestions")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["user_id"] == "test_user"
            assert data["total_count"] == 2
            assert data["sessions_count"] == 2
            assert len(data["topic_suggestions"]) == 2
            
            # Verify topics from both sessions are included
            topic_names = [topic["name"] for topic in data["topic_suggestions"]]
            assert "AI Research" in topic_names
            assert "Climate Change" in topic_names
            
            mock_research_manager.get_all_topic_suggestions.assert_called_once_with("test_user")

    def test_get_all_topic_suggestions_empty(self, client, mock_research_manager):
        """Test getting all topic suggestions when none exist."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_all_topic_suggestions.return_value = {}
            
            response = client.get("/topics/suggestions")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 0
            assert data["sessions_count"] == 0
            assert data["topic_suggestions"] == []

    def test_get_all_topic_suggestions_error_handling(self, client, mock_research_manager):
        """Test error handling in get all topic suggestions."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_all_topic_suggestions.side_effect = Exception("Database error")
            
            response = client.get("/topics/suggestions")
            
            assert response.status_code == 500
            assert "Error retrieving topic suggestions" in response.json()["detail"]


class TestGetTopicProcessingStatus:
    """Test topic processing status endpoint."""

    def test_get_topic_processing_status_with_topics(self, client, mock_research_manager, sample_topics_data):
        """Test getting processing status when topics exist."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = sample_topics_data
            
            response = client.get("/topics/status/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["session_id"] == "test_session"
            assert data["user_id"] == "test_user"
            assert data["has_topics"] is True
            assert data["topic_count"] == 2
            assert data["processing_complete"] is True

    def test_get_topic_processing_status_no_topics(self, client, mock_research_manager):
        """Test getting processing status when no topics exist."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = []
            
            response = client.get("/topics/status/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["has_topics"] is False
            assert data["topic_count"] == 0
            assert data["processing_complete"] is False

    def test_get_topic_processing_status_error_handling(self, client, mock_research_manager):
        """Test error handling in processing status endpoint."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.side_effect = Exception("Database error")
            
            response = client.get("/topics/status/test_session")
            
            assert response.status_code == 500
            assert "Error checking topic status" in response.json()["detail"]


class TestGetTopicStatistics:
    """Test topic statistics endpoint."""

    def test_get_topic_statistics_success(self, client, mock_research_manager, sample_all_topics_data):
        """Test successful topic statistics calculation."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_all_topic_suggestions.return_value = sample_all_topics_data
            
            response = client.get("/topics/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["user_id"] == "test_user"
            assert data["total_topics"] == 2
            assert data["total_sessions"] == 2
            assert data["average_confidence_score"] == pytest.approx(0.85, rel=1e-5)  # (0.9 + 0.8) / 2
            assert data["oldest_topic_age_days"] >= 0

    def test_get_topic_statistics_empty(self, client, mock_research_manager):
        """Test topic statistics with no topics."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_all_topic_suggestions.return_value = {}
            
            response = client.get("/topics/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_topics"] == 0
            assert data["total_sessions"] == 0
            assert data["average_confidence_score"] == 0.0
            assert data["oldest_topic_age_days"] == 0

    def test_get_topic_statistics_error_handling(self, client, mock_research_manager):
        """Test error handling in topic statistics."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_all_topic_suggestions.side_effect = Exception("Database error")
            
            response = client.get("/topics/stats")
            
            assert response.status_code == 500
            assert "Error retrieving topic statistics" in response.json()["detail"]


class TestDeleteSessionTopics:
    """Test deleting topics for a session."""

    def test_delete_session_topics_success(self, client, mock_research_manager):
        """Test successful session topic deletion."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_session_safe.return_value = {
                "success": True,
                "message": "Session deleted successfully",
                "topics_deleted": 3
            }
            
            response = client.delete("/topics/session/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["session_id"] == "test_session"
            assert data["topics_deleted"] == 3
            assert "deleted successfully" in data["message"]
            
            mock_research_manager.delete_session_safe.assert_called_once_with("test_user", "test_session")

    def test_delete_session_topics_failure(self, client, mock_research_manager):
        """Test failed session topic deletion."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_session_safe.return_value = {
                "success": False,
                "error": "Session not found"
            }
            
            response = client.delete("/topics/session/test_session")
            
            assert response.status_code == 500
            assert "Session not found" in response.json()["detail"]

    def test_delete_session_topics_exception(self, client, mock_research_manager):
        """Test exception handling in session topic deletion."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_session_safe.side_effect = Exception("Database error")
            
            response = client.delete("/topics/session/test_session")
            
            assert response.status_code == 500
            assert "Error deleting session topics" in response.json()["detail"]


class TestCleanupTopics:
    """Test topic cleanup functionality."""

    def test_cleanup_topics_success(self, client, mock_research_manager):
        """Test successful topic cleanup."""
        with patch('api.topics.research_manager', mock_research_manager):
            # Mock migration call
            mock_research_manager.migrate_topics_from_profile.return_value = True
            
            # Mock topics data with old and duplicate topics
            current_time = time.time()
            old_time = current_time - (35 * 24 * 60 * 60)  # 35 days ago
            
            topics_data = {
                "sessions": {
                    "session1": [
                        {
                            "topic_name": "Recent Topic",
                            "suggested_at": current_time - 3600,  # 1 hour ago
                        },
                        {
                            "topic_name": "Old Topic",
                            "suggested_at": old_time,  # 35 days ago (should be removed)
                        },
                        {
                            "topic_name": "Recent Topic",  # Duplicate (should be removed)
                            "suggested_at": current_time - 1800,
                        }
                    ]
                },
                "metadata": {}
            }
            
            mock_research_manager.get_user_topics.return_value = topics_data
            mock_research_manager.save_user_topics.return_value = True
            
            response = client.delete("/topics/cleanup")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["topics_removed"] == 2  # Old topic + duplicate
            assert data["sessions_cleaned"] == 0  # Session not empty after cleanup
            
            # Verify calls
            mock_research_manager.migrate_topics_from_profile.assert_called_once_with("test_user")
            mock_research_manager.get_user_topics.assert_called_once_with("test_user")
            mock_research_manager.save_user_topics.assert_called_once()

    def test_cleanup_topics_no_topics(self, client, mock_research_manager):
        """Test cleanup when no topics exist."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.migrate_topics_from_profile.return_value = True
            mock_research_manager.get_user_topics.return_value = {"sessions": {}}
            
            response = client.delete("/topics/cleanup")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "No topics to clean up"
            assert data["topics_removed"] == 0

    def test_cleanup_topics_save_failure(self, client, mock_research_manager):
        """Test cleanup when save fails."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.migrate_topics_from_profile.return_value = True
            mock_research_manager.get_user_topics.return_value = {
                "sessions": {"session1": [{"topic_name": "Topic", "suggested_at": time.time()}]},
                "metadata": {}
            }
            mock_research_manager.save_user_topics.return_value = False
            
            response = client.delete("/topics/cleanup")
            
            assert response.status_code == 500
            assert "Failed to clean up topics" in response.json()["detail"]

    def test_cleanup_topics_exception(self, client, mock_research_manager):
        """Test exception handling in cleanup."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.migrate_topics_from_profile.side_effect = Exception("Database error")
            
            response = client.delete("/topics/cleanup")
            
            assert response.status_code == 500
            assert "Error cleaning up topics" in response.json()["detail"]


class TestGetTopSessionTopics:
    """Test getting top topics for a session."""

    def test_get_top_session_topics_success(self, client, mock_research_manager, sample_topics_data):
        """Test successful retrieval of top session topics."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = sample_topics_data
            
            response = client.get("/topics/session/test_session/top?limit=2")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["session_id"] == "test_session"
            assert data["user_id"] == "test_user"
            assert data["total_count"] == 2
            assert data["available_count"] == 2
            assert len(data["topics"]) == 2
            
            # Should be sorted by confidence score (highest first)
            topics = data["topics"]
            assert topics[0]["name"] == "AI Research"  # 0.9 confidence
            assert topics[1]["name"] == "Climate Change"  # 0.8 confidence

    def test_get_top_session_topics_with_limit(self, client, mock_research_manager, sample_topics_data):
        """Test top topics with limit parameter."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = sample_topics_data
            
            response = client.get("/topics/session/test_session/top?limit=1")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 1
            assert data["available_count"] == 2
            assert len(data["topics"]) == 1
            assert data["topics"][0]["name"] == "AI Research"  # Highest confidence

    def test_get_top_session_topics_default_limit(self, client, mock_research_manager, sample_topics_data):
        """Test top topics with default limit."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = sample_topics_data
            
            response = client.get("/topics/session/test_session/top")
            
            assert response.status_code == 200
            data = response.json()
            
            # Default limit is 3, but we only have 2 topics
            assert data["total_count"] == 2
            assert len(data["topics"]) == 2

    def test_get_top_session_topics_empty(self, client, mock_research_manager):
        """Test top topics when no topics exist."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = []
            
            response = client.get("/topics/session/test_session/top")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 0
            assert data["available_count"] == 0
            assert data["topics"] == []

    def test_get_top_session_topics_error_handling(self, client, mock_research_manager):
        """Test error handling in top topics endpoint."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.side_effect = Exception("Database error")
            
            response = client.get("/topics/session/test_session/top")
            
            assert response.status_code == 500
            assert "Error retrieving top topics" in response.json()["detail"]


class TestDeleteTopicById:
    """Test deleting a topic by ID."""

    def test_delete_topic_by_id_success(self, client, mock_research_manager):
        """Test successful topic deletion by ID."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_topic_by_id.return_value = {
                "success": True,
                "deleted_topic": {
                    "topic_id": "topic_123",
                    "topic_name": "AI Research",
                    "description": "Latest AI developments",
                    "session_id": "session_1"
                }
            }
            
            response = client.delete("/topics/topic/topic_123")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "Deleted topic: AI Research" in data["message"]
            assert data["deleted_topic"]["topic_id"] == "topic_123"
            assert data["deleted_topic"]["name"] == "AI Research"
            
            mock_research_manager.delete_topic_by_id.assert_called_once_with("test_user", "topic_123")

    def test_delete_topic_by_id_not_found(self, client, mock_research_manager):
        """Test deleting non-existent topic."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_topic_by_id.return_value = {
                "success": False,
                "error": "Topic not found"
            }
            
            response = client.delete("/topics/topic/nonexistent")
            
            assert response.status_code == 404
            assert "Topic not found" in response.json()["detail"]

    def test_delete_topic_by_id_other_error(self, client, mock_research_manager):
        """Test other errors in topic deletion."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_topic_by_id.return_value = {
                "success": False,
                "error": "Database connection failed"
            }
            
            response = client.delete("/topics/topic/topic_123")
            
            assert response.status_code == 500
            assert "Database connection failed" in response.json()["detail"]

    def test_delete_topic_by_id_exception(self, client, mock_research_manager):
        """Test exception handling in topic deletion."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_topic_by_id.side_effect = Exception("Unexpected error")
            
            response = client.delete("/topics/topic/topic_123")
            
            assert response.status_code == 500
            assert "Error deleting topic" in response.json()["detail"]


class TestParameterValidation:
    """Test parameter validation in endpoints."""

    def test_top_topics_limit_validation(self, client, mock_research_manager):
        """Test limit parameter validation in top topics endpoint."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = []
            
            # Test valid limits
            response = client.get("/topics/session/test_session/top?limit=1")
            assert response.status_code == 200
            
            response = client.get("/topics/session/test_session/top?limit=10")
            assert response.status_code == 200
            
            # Test invalid limits (should fail validation)
            response = client.get("/topics/session/test_session/top?limit=0")
            assert response.status_code == 422  # Validation error
            
            response = client.get("/topics/session/test_session/top?limit=11")
            assert response.status_code == 422  # Validation error

    def test_session_id_parameter_handling(self, client, mock_research_manager):
        """Test session ID parameter handling."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.get_topic_suggestions.return_value = []
            
            # Test with special characters in session ID
            response = client.get("/topics/suggestions/session-with-dashes_123")
            assert response.status_code == 200
            
            # Verify the session ID was passed correctly
            mock_research_manager.get_topic_suggestions.assert_called_with("test_user", "session-with-dashes_123")

    def test_topic_id_parameter_handling(self, client, mock_research_manager):
        """Test topic ID parameter handling."""
        with patch('api.topics.research_manager', mock_research_manager):
            mock_research_manager.delete_topic_by_id.return_value = {
                "success": False,
                "error": "Topic not found"
            }
            
            # Test with various topic ID formats
            response = client.delete("/topics/topic/topic_123-abc_456")
            assert response.status_code == 404
            
            # Verify the topic ID was passed correctly
            mock_research_manager.delete_topic_by_id.assert_called_with("test_user", "topic_123-abc_456") 