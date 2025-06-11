import pytest
from unittest.mock import MagicMock, patch, call
import tempfile
import time
import uuid

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.research_manager import ResearchManager
from storage.storage_manager import StorageManager
from storage.profile_manager import ProfileManager


@pytest.fixture
def mock_storage_manager():
    """Create a mock StorageManager for testing."""
    return MagicMock()


@pytest.fixture
def mock_profile_manager():
    """Create a mock ProfileManager for testing."""
    return MagicMock()


@pytest.fixture
def research_manager(mock_storage_manager, mock_profile_manager):
    """Create a ResearchManager with mocked dependencies."""
    return ResearchManager(mock_storage_manager, mock_profile_manager)


@pytest.fixture
def real_research_manager():
    """Create a ResearchManager with real storage for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)
        profile_manager = ProfileManager(storage)
        yield ResearchManager(storage, profile_manager)


@pytest.fixture
def sample_topics():
    """Sample topic data for testing."""
    return [
        {
            "name": "AI Research", 
            "description": "Latest developments in artificial intelligence",
            "confidence_score": 0.9
        },
        {
            "name": "Climate Change",
            "description": "Environmental impact and solutions", 
            "confidence_score": 0.8
        }
    ]


@pytest.fixture
def sample_finding():
    """Sample research finding for testing."""
    return {
        "title": "Recent AI Breakthrough",
        "summary": "New neural network architecture shows promising results",
        "url": "https://example.com/ai-breakthrough",
        "research_time": time.time(),
        "quality_score": 0.85,
        "source": "Tech Journal"
    }


class TestResearchManagerInitialization:
    """Test ResearchManager initialization and basic functionality."""

    def test_init(self, mock_storage_manager, mock_profile_manager):
        """Test ResearchManager initialization."""
        rm = ResearchManager(mock_storage_manager, mock_profile_manager)
        
        assert rm.storage == mock_storage_manager
        assert rm.profile_manager == mock_profile_manager
        assert isinstance(rm._user_locks, dict)
        assert rm._locks_lock is not None

    def test_get_user_lock(self, research_manager):
        """Test user-specific lock creation."""
        lock1 = research_manager._get_user_lock("user1")
        lock2 = research_manager._get_user_lock("user1")  # Same user
        lock3 = research_manager._get_user_lock("user2")  # Different user
        
        assert lock1 is lock2  # Same lock for same user
        assert lock1 is not lock3  # Different lock for different user

    def test_get_user_path(self, research_manager):
        """Test user path generation."""
        path = research_manager._get_user_path("test_user")
        assert path == "users/test_user"

    def test_get_topics_path(self, research_manager):
        """Test topics file path generation."""
        path = research_manager._get_topics_path("test_user")
        assert path == "users/test_user/topics.json"

    def test_get_research_findings_path(self, research_manager):
        """Test research findings file path generation."""
        path = research_manager._get_research_findings_path("test_user")
        assert path == "users/test_user/research_findings.json"


class TestTopicSuggestions:
    """Test topic suggestion storage and retrieval."""

    def test_store_topic_suggestions_success(self, research_manager, sample_topics):
        """Test successful storing of topic suggestions."""
        research_manager.storage.read.return_value = {
            "sessions": {},
            "metadata": {"total_topics": 0, "active_research_topics": 0, "last_cleanup": time.time()}
        }
        research_manager.storage.write.return_value = True
        
        with patch.object(research_manager, 'migrate_topics_from_profile') as mock_migrate:
            result = research_manager.store_topic_suggestions("user1", "session1", sample_topics, "test context")
        
        assert result is True
        mock_migrate.assert_called_once_with("user1")
        research_manager.storage.write.assert_called_once()
        
        # Verify the write call structure
        write_call = research_manager.storage.write.call_args
        assert write_call[0][0] == "users/user1/topics.json"  # Path
        topics_data = write_call[0][1]  # Data
        assert "sessions" in topics_data
        assert "session1" in topics_data["sessions"]
        assert len(topics_data["sessions"]["session1"]) == 2

    def test_store_topic_suggestions_empty_topics(self, research_manager):
        """Test storing empty topic list returns True without operations."""
        result = research_manager.store_topic_suggestions("user1", "session1", [], "context")
        
        assert result is True
        research_manager.storage.read.assert_not_called()
        research_manager.storage.write.assert_not_called()

    def test_store_topic_suggestions_duplicate_prevention(self, research_manager, sample_topics):
        """Test that duplicate topic names are prevented."""
        existing_data = {
            "sessions": {
                "session1": [
                    {
                        "topic_id": "existing-id",
                        "topic_name": "AI Research",  # Duplicate name
                        "description": "Existing description",
                        "confidence_score": 0.7,
                        "suggested_at": time.time() - 100,
                        "conversation_context": "old context",
                        "is_active_research": False,
                        "research_count": 0
                    }
                ]
            },
            "metadata": {"total_topics": 1, "active_research_topics": 0, "last_cleanup": time.time()}
        }
        
        research_manager.storage.read.return_value = existing_data
        research_manager.storage.write.return_value = True
        
        with patch.object(research_manager, 'migrate_topics_from_profile'):
            result = research_manager.store_topic_suggestions("user1", "session1", sample_topics, "new context")
        
        assert result is True
        
        # Verify only non-duplicate topic was added
        write_call = research_manager.storage.write.call_args[0][1]
        session_topics = write_call["sessions"]["session1"]
        topic_names = [t["topic_name"] for t in session_topics]
        
        assert "AI Research" in topic_names  # Original remains
        assert "Climate Change" in topic_names  # New unique topic added
        assert len(session_topics) == 2  # Only 2 topics total (original + 1 new)

    def test_store_topic_suggestions_exception_handling(self, research_manager, sample_topics):
        """Test exception handling in store_topic_suggestions."""
        research_manager.storage.read.side_effect = Exception("Storage error")
        
        result = research_manager.store_topic_suggestions("user1", "session1", sample_topics)
        
        assert result is False

    def test_get_topic_suggestions_success(self, research_manager):
        """Test successful retrieval of topic suggestions."""
        mock_data = {
            "sessions": {
                "session1": [{"topic_name": "Test Topic", "description": "Test"}]
            }
        }
        research_manager.storage.read.return_value = mock_data
        
        with patch.object(research_manager, 'migrate_topics_from_profile'):
            result = research_manager.get_topic_suggestions("user1", "session1")
        
        assert result == [{"topic_name": "Test Topic", "description": "Test"}]

    def test_get_topic_suggestions_no_session(self, research_manager):
        """Test getting topic suggestions for non-existent session."""
        research_manager.storage.read.return_value = {"sessions": {}}
        
        with patch.object(research_manager, 'migrate_topics_from_profile'):
            result = research_manager.get_topic_suggestions("user1", "nonexistent")
        
        assert result == []

    def test_get_all_topic_suggestions_success(self, research_manager):
        """Test getting all topic suggestions across sessions."""
        mock_data = {
            "sessions": {
                "session1": [{"topic_name": "Topic 1"}],
                "session2": [{"topic_name": "Topic 2"}]
            }
        }
        research_manager.storage.read.return_value = mock_data
        
        with patch.object(research_manager, 'migrate_topics_from_profile'):
            result = research_manager.get_all_topic_suggestions("user1")
        
        assert result == mock_data["sessions"]

    def test_get_all_topic_suggestions_exception(self, research_manager):
        """Test exception handling in get_all_topic_suggestions."""
        research_manager.storage.read.side_effect = Exception("Storage error")
        
        result = research_manager.get_all_topic_suggestions("user1")
        
        assert result == {}


class TestTopicManagement:
    """Test topic data management methods."""

    def test_get_user_topics_existing_data(self, research_manager):
        """Test getting existing user topics."""
        mock_data = {"sessions": {"test": []}, "metadata": {"total_topics": 1}}
        research_manager.storage.read.return_value = mock_data
        
        result = research_manager.get_user_topics("user1")
        
        assert result == mock_data
        research_manager.storage.read.assert_called_with("users/user1/topics.json")

    def test_get_user_topics_no_data(self, research_manager):
        """Test getting user topics when no data exists."""
        research_manager.storage.read.return_value = {}
        
        result = research_manager.get_user_topics("user1")
        
        expected = {
            "sessions": {},
            "metadata": {"total_topics": 0, "active_research_topics": 0, "last_cleanup": time.time()}
        }
        assert result["sessions"] == expected["sessions"]
        assert result["metadata"]["total_topics"] == expected["metadata"]["total_topics"]
        assert result["metadata"]["active_research_topics"] == expected["metadata"]["active_research_topics"]

    def test_save_user_topics(self, research_manager):
        """Test saving user topics."""
        topics_data = {"sessions": {}, "metadata": {}}
        research_manager.storage.write.return_value = True
        
        result = research_manager.save_user_topics("user1", topics_data)
        
        assert result is True
        research_manager.storage.write.assert_called_with("users/user1/topics.json", topics_data)

    def test_get_active_research_topics(self, research_manager):
        """Test getting active research topics."""
        mock_data = {
            "sessions": {
                "session1": [
                    {"topic_name": "Active Topic", "is_active_research": True, "research_count": 5},
                    {"topic_name": "Inactive Topic", "is_active_research": False, "research_count": 0}
                ]
            }
        }
        
        with patch.object(research_manager, 'get_user_topics', return_value=mock_data):
            result = research_manager.get_active_research_topics("user1")
        
        assert len(result) == 1
        assert result[0]["topic_name"] == "Active Topic"
        assert result[0]["is_active_research"] is True


class TestResearchFindings:
    """Test research findings storage and management."""

    def test_store_research_finding_success(self, research_manager, sample_finding):
        """Test successful storing of research finding."""
        research_manager.storage.read.return_value = {
            "metadata": {"last_cleanup": time.time(), "total_findings": 0, "topics_count": 0}
        }
        research_manager.storage.write.return_value = True
        
        result = research_manager.store_research_finding("user1", "AI Research", sample_finding)
        
        assert result is True
        research_manager.storage.write.assert_called_once()
        
        # Verify the finding was properly formatted
        write_call = research_manager.storage.write.call_args[0][1]
        assert "AI Research" in write_call
        stored_finding = write_call["AI Research"][0]
        assert "finding_id" in stored_finding
        assert stored_finding["read"] is False
        assert stored_finding["title"] == sample_finding["title"]

    def test_store_research_finding_new_topic(self, research_manager, sample_finding):
        """Test storing finding for new topic increases topic count."""
        research_manager.storage.read.return_value = {
            "metadata": {"last_cleanup": time.time(), "total_findings": 0, "topics_count": 0}
        }
        research_manager.storage.write.return_value = True
        
        research_manager.store_research_finding("user1", "New Topic", sample_finding)
        
        write_call = research_manager.storage.write.call_args[0][1]
        assert write_call["metadata"]["topics_count"] == 1
        assert write_call["metadata"]["total_findings"] == 1

    def test_store_research_finding_exception(self, research_manager, sample_finding):
        """Test exception handling in store_research_finding."""
        research_manager.storage.read.side_effect = Exception("Storage error")
        
        result = research_manager.store_research_finding("user1", "AI Research", sample_finding)
        
        assert result is False

    def test_mark_finding_as_read_success(self, research_manager):
        """Test successfully marking finding as read."""
        findings_data = {
            "AI Research": [
                {
                    "finding_id": "test_finding_123",
                    "title": "Test Finding",
                    "read": False
                }
            ],
            "metadata": {"total_findings": 1}
        }
        research_manager.storage.read.return_value = findings_data
        research_manager.storage.write.return_value = True
        
        result = research_manager.mark_finding_as_read("user1", "test_finding_123")
        
        assert result is True
        research_manager.storage.write.assert_called_once()
        
        # Verify finding was marked as read
        write_call = research_manager.storage.write.call_args[0][1]
        assert write_call["AI Research"][0]["read"] is True

    def test_mark_finding_as_read_not_found(self, research_manager):
        """Test marking non-existent finding as read."""
        research_manager.storage.read.return_value = {
            "metadata": {"total_findings": 0}
        }
        
        result = research_manager.mark_finding_as_read("user1", "nonexistent_finding")
        
        assert result is False

    def test_mark_finding_as_read_no_data(self, research_manager):
        """Test marking finding as read when no data exists."""
        research_manager.storage.read.return_value = {}
        
        result = research_manager.mark_finding_as_read("user1", "test_finding")
        
        assert result is False

    def test_get_research_findings_for_api_all(self, research_manager):
        """Test getting all research findings for API."""
        mock_findings = {
            "AI Research": [
                {"finding_id": "1", "title": "Finding 1", "read": False, "research_time": 1000},
                {"finding_id": "2", "title": "Finding 2", "read": True, "research_time": 2000}
            ],
            "Climate": [
                {"finding_id": "3", "title": "Finding 3", "read": False, "research_time": 1500}
            ]
        }
        
        with patch.object(research_manager, 'get_research_findings', return_value=mock_findings):
            result = research_manager.get_research_findings_for_api("user1")
        
        assert len(result) == 3
        # Check sorting by research_time (newest first)
        assert result[0]["finding_id"] == "2"  # research_time 2000
        assert result[1]["finding_id"] == "3"  # research_time 1500  
        assert result[2]["finding_id"] == "1"  # research_time 1000
        
        # Check topic_name was added
        for finding in result:
            assert "topic_name" in finding

    def test_get_research_findings_for_api_unread_only(self, research_manager):
        """Test getting only unread findings for API."""
        mock_findings = {
            "AI Research": [
                {"finding_id": "1", "title": "Finding 1", "read": False, "research_time": 1000},
                {"finding_id": "2", "title": "Finding 2", "read": True, "research_time": 2000}
            ]
        }
        
        with patch.object(research_manager, 'get_research_findings', return_value=mock_findings):
            result = research_manager.get_research_findings_for_api("user1", unread_only=True)
        
        assert len(result) == 1
        assert result[0]["finding_id"] == "1"
        assert result[0]["read"] is False

    def test_delete_research_finding_success(self, research_manager):
        """Test successful deletion of research finding."""
        findings_data = {
            "AI Research": [
                {"finding_id": "test_finding_123", "title": "Test Finding"},
                {"finding_id": "other_finding", "title": "Other Finding"}
            ],
            "metadata": {"total_findings": 2, "topics_count": 1}
        }
        research_manager.storage.read.return_value = findings_data
        research_manager.storage.write.return_value = True
        
        result = research_manager.delete_research_finding("user1", "test_finding_123")
        
        assert result["success"] is True
        assert result["deleted_finding"]["finding_id"] == "test_finding_123"
        assert result["deleted_finding"]["topic_name"] == "AI Research"
        
        # Verify finding was removed
        write_call = research_manager.storage.write.call_args[0][1]
        remaining_findings = write_call["AI Research"]
        assert len(remaining_findings) == 1
        assert remaining_findings[0]["finding_id"] == "other_finding"

    def test_delete_research_finding_not_found(self, research_manager):
        """Test deleting non-existent finding."""
        research_manager.storage.read.return_value = {
            "metadata": {"total_findings": 0}
        }
        
        result = research_manager.delete_research_finding("user1", "nonexistent")
        
        assert result["success"] is False
        assert "not found" in result["error"]
        assert result["deleted_finding"] is None


class TestIntegrationTests:
    """Integration tests with real storage."""

    def test_full_topic_workflow(self, real_research_manager, sample_topics):
        """Test complete topic suggestion workflow with real storage."""
        rm = real_research_manager
        user_id = "integration_test_user"
        session_id = "test_session"
        
        # Store topics
        success = rm.store_topic_suggestions(user_id, session_id, sample_topics, "test context")
        assert success is True
        
        # Retrieve topics
        topics = rm.get_topic_suggestions(user_id, session_id)
        assert len(topics) == 2
        assert any(t["topic_name"] == "AI Research" for t in topics)
        assert any(t["topic_name"] == "Climate Change" for t in topics)
        
        # Get all topics
        all_topics = rm.get_all_topic_suggestions(user_id)
        assert session_id in all_topics
        assert len(all_topics[session_id]) == 2

    def test_full_research_findings_workflow(self, real_research_manager, sample_finding):
        """Test complete research findings workflow with real storage."""
        rm = real_research_manager
        user_id = "integration_test_user"
        topic_name = "AI Research"
        
        # Store finding
        success = rm.store_research_finding(user_id, topic_name, sample_finding)
        assert success is True
        
        # Get findings for API
        findings = rm.get_research_findings_for_api(user_id)
        assert len(findings) == 1
        assert findings[0]["topic_name"] == topic_name
        assert findings[0]["title"] == sample_finding["title"]
        assert findings[0]["read"] is False
        
        # Mark as read
        finding_id = findings[0]["finding_id"]
        success = rm.mark_finding_as_read(user_id, finding_id)
        assert success is True
        
        # Verify it's marked as read
        updated_findings = rm.get_research_findings_for_api(user_id)
        assert updated_findings[0]["read"] is True
        
        # Test unread_only filter
        unread_findings = rm.get_research_findings_for_api(user_id, unread_only=True)
        assert len(unread_findings) == 0
        
        # Delete finding
        result = rm.delete_research_finding(user_id, finding_id)
        assert result["success"] is True
        
        # Verify deletion
        final_findings = rm.get_research_findings_for_api(user_id)
        assert len(final_findings) == 0 