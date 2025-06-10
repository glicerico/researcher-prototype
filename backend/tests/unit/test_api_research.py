import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.research import router, MotivationConfigUpdate
from app import app


@pytest.fixture
def research_client():
    """Create a test client for research API endpoints."""
    test_app = app
    test_app.include_router(router, prefix="/api")
    return TestClient(test_app)


@pytest.fixture
def mock_research_manager():
    """Mock research manager for testing."""
    with patch('api.research.research_manager') as mock:
        yield mock


@pytest.fixture
def mock_profile_manager():
    """Mock profile manager for testing."""
    with patch('api.research.profile_manager') as mock:
        yield mock


@pytest.fixture
def sample_research_findings():
    """Sample research findings data for testing."""
    return [
        {
            "id": "finding_1",
            "topic_name": "AI Research",
            "title": "Latest AI Developments",
            "summary": "Recent advances in AI technology",
            "url": "https://example.com/ai-news",
            "timestamp": "2024-01-01T12:00:00Z",
            "is_read": False,
            "quality_score": 0.85
        },
        {
            "id": "finding_2", 
            "topic_name": "Machine Learning",
            "title": "ML Algorithm Improvements",
            "summary": "New machine learning techniques",
            "url": "https://example.com/ml-news",
            "timestamp": "2024-01-02T12:00:00Z",
            "is_read": True,
            "quality_score": 0.92
        }
    ]


class TestResearchFindingsEndpoints:
    """Test research findings API endpoints."""

    def test_get_research_findings_success(self, research_client, mock_research_manager, sample_research_findings):
        """Test successful retrieval of research findings."""
        mock_research_manager.get_research_findings_for_api.return_value = sample_research_findings

        response = research_client.get("/api/research/findings/test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == "test_user"
        assert data["total_findings"] == 2
        assert len(data["findings"]) == 2
        assert data["findings"][0]["id"] == "finding_1"

    def test_get_research_findings_with_topic_filter(self, research_client, mock_research_manager):
        """Test getting findings filtered by topic."""
        filtered_findings = [{"id": "finding_1", "topic_name": "AI Research"}]
        mock_research_manager.get_research_findings_for_api.return_value = filtered_findings

        response = research_client.get("/api/research/findings/test_user?topic_name=AI Research")
        
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["topic_name"] == "AI Research"
        mock_research_manager.get_research_findings_for_api.assert_called_with(
            "test_user", "AI Research", False
        )

    def test_get_research_findings_unread_only(self, research_client, mock_research_manager):
        """Test getting only unread findings."""
        unread_findings = [{"id": "finding_1", "is_read": False}]
        mock_research_manager.get_research_findings_for_api.return_value = unread_findings

        response = research_client.get("/api/research/findings/test_user?unread_only=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["unread_only"] is True
        mock_research_manager.get_research_findings_for_api.assert_called_with(
            "test_user", None, True
        )

    def test_get_research_findings_error(self, research_client, mock_research_manager):
        """Test error handling when getting research findings fails."""
        mock_research_manager.get_research_findings_for_api.side_effect = Exception("Database error")

        response = research_client.get("/api/research/findings/test_user")
        
        assert response.status_code == 500
        assert "Error getting research findings" in response.json()["detail"]

    @patch('api.research.get_or_create_user_id')
    def test_mark_research_finding_read_success(self, mock_get_user, research_client, mock_research_manager):
        """Test successfully marking a finding as read."""
        mock_get_user.return_value = "test_user"
        mock_research_manager.mark_finding_as_read.return_value = True

        response = research_client.post("/api/research/findings/finding_1/mark_read")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["finding_id"] == "finding_1"
        mock_research_manager.mark_finding_as_read.assert_called_with("test_user", "finding_1")

    @patch('api.research.get_or_create_user_id')
    def test_mark_research_finding_read_not_found(self, mock_get_user, research_client, mock_research_manager):
        """Test marking non-existent finding as read."""
        mock_get_user.return_value = "test_user"
        mock_research_manager.mark_finding_as_read.return_value = False

        response = research_client.post("/api/research/findings/nonexistent/mark_read")
        
        assert response.status_code == 404
        assert "Finding not found" in response.json()["detail"]

    @patch('api.research.get_or_create_user_id')
    def test_delete_research_finding_success(self, mock_get_user, research_client, mock_research_manager):
        """Test successful deletion of a research finding."""
        mock_get_user.return_value = "test_user"
        mock_research_manager.delete_research_finding.return_value = {
            "success": True,
            "deleted_finding": {"id": "finding_1", "title": "Test Finding"}
        }

        response = research_client.delete("/api/research/findings/finding_1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted_finding" in data
        mock_research_manager.delete_research_finding.assert_called_with("test_user", "finding_1")

    @patch('api.research.get_or_create_user_id')
    def test_delete_research_finding_not_found(self, mock_get_user, research_client, mock_research_manager):
        """Test deletion of non-existent finding."""
        mock_get_user.return_value = "test_user"
        mock_research_manager.delete_research_finding.return_value = {
            "success": False,
            "error": "Finding not found"
        }

        response = research_client.delete("/api/research/findings/nonexistent")
        
        assert response.status_code == 404
        assert "Finding not found" in response.json()["detail"]

    @patch('api.research.get_or_create_user_id')
    def test_delete_all_topic_findings_success(self, mock_get_user, research_client, mock_research_manager):
        """Test successful deletion of all findings for a topic."""
        mock_get_user.return_value = "test_user"
        mock_research_manager.delete_all_topic_findings.return_value = {
            "success": True,
            "topic_name": "AI Research",
            "findings_deleted": 3
        }

        response = research_client.delete("/api/research/findings/topic/AI Research")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["topic_name"] == "AI Research"
        assert data["findings_deleted"] == 3


class TestResearchEngineStatusEndpoints:
    """Test research engine status and control endpoints."""

    def test_get_research_engine_status_enabled(self, research_client):
        """Test getting research engine status when enabled."""
        # Mock the app state
        with patch.object(research_client.app.state, 'autonomous_researcher') as mock_researcher:
            mock_researcher.get_status.return_value = {
                "enabled": True,
                "running": True,
                "last_run": "2024-01-01T12:00:00Z"
            }

            response = research_client.get("/api/research/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
            assert data["running"] is True

    def test_get_research_engine_status_not_initialized(self, research_client):
        """Test getting status when research engine is not initialized."""
        # Ensure autonomous_researcher is not set
        if hasattr(research_client.app.state, 'autonomous_researcher'):
            delattr(research_client.app.state, 'autonomous_researcher')

        response = research_client.get("/api/research/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["running"] is False
        assert "not initialized" in data["error"]


class TestDebugEndpoints:
    """Test debug endpoints for research system."""

    def test_get_debug_active_topics(self, research_client, mock_profile_manager, mock_research_manager):
        """Test getting debug information about active topics."""
        mock_profile_manager.list_users.return_value = ["user1", "user2"]
        mock_research_manager.get_active_research_topics.side_effect = [
            [{"topic_name": "AI Research", "description": "AI developments", "research_count": 5}],
            []  # user2 has no active topics
        ]

        response = research_client.get("/api/research/debug/active-topics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 2
        assert data["users_with_active_topics"] == 1
        assert data["total_active_topics"] == 1
        assert len(data["user_breakdown"]) == 1

    def test_get_config_override(self, research_client):
        """Test getting the config override."""
        response = research_client.get("/api/research/debug/config-override")
        
        assert response.status_code == 200
        assert "override" in response.json()

    def test_clear_config_override(self, research_client):
        """Test clearing the config override."""
        response = research_client.post("/api/research/debug/clear-override")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMotivationConfigUpdate:
    """Test MotivationConfigUpdate model."""

    def test_motivation_config_model_creation(self):
        """Test creating MotivationConfigUpdate with all fields."""
        config = MotivationConfigUpdate(
            threshold=0.8,
            boredom_rate=0.1,
            curiosity_decay=0.05,
            tiredness_decay=0.02,
            satisfaction_decay=0.03
        )
        
        assert config.threshold == 0.8
        assert config.boredom_rate == 0.1
        assert config.curiosity_decay == 0.05
        assert config.tiredness_decay == 0.02
        assert config.satisfaction_decay == 0.03

    def test_motivation_config_model_partial(self):
        """Test creating MotivationConfigUpdate with partial fields."""
        config = MotivationConfigUpdate(threshold=0.9)
        
        assert config.threshold == 0.9
        assert config.boredom_rate is None
        assert config.curiosity_decay is None
        assert config.tiredness_decay is None
        assert config.satisfaction_decay is None

    def test_motivation_config_model_empty(self):
        """Test creating MotivationConfigUpdate with no fields."""
        config = MotivationConfigUpdate()
        
        assert config.threshold is None
        assert config.boredom_rate is None
        assert config.curiosity_decay is None
        assert config.tiredness_decay is None
        assert config.satisfaction_decay is None 