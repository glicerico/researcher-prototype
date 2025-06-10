import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import tempfile

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.storage_manager import StorageManager
from storage.profile_manager import ProfileManager


class TestStorageManager:
    """Test StorageManager functionality."""

    def test_storage_manager_init(self):
        """Test StorageManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            assert storage.base_dir == temp_dir
            assert os.path.exists(temp_dir)

    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    @patch('os.path.exists')
    def test_load_json_success(self, mock_exists, mock_file):
        """Test successful JSON loading."""
        mock_exists.return_value = True
        
        storage = StorageManager("/test/dir")
        result = storage.load_json("test.json")
        
        assert result == {"test": "data"}
        mock_file.assert_called_once_with("/test/dir/test.json", 'r')

    @patch('os.path.exists')
    def test_load_json_file_not_exists(self, mock_exists):
        """Test JSON loading when file doesn't exist."""
        mock_exists.return_value = False
        
        storage = StorageManager("/test/dir")
        result = storage.load_json("nonexistent.json")
        
        assert result == {}

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_save_json_success(self, mock_makedirs, mock_file):
        """Test successful JSON saving."""
        storage = StorageManager("/test/dir")
        test_data = {"key": "value"}
        
        storage.save_json("test.json", test_data)
        
        mock_makedirs.assert_called_once_with("/test/dir", exist_ok=True)
        mock_file.assert_called_once_with("/test/dir/test.json", 'w')
        mock_file().write.assert_called()

    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('os.makedirs')
    def test_save_json_error_handling(self, mock_makedirs, mock_file):
        """Test JSON saving error handling."""
        storage = StorageManager("/test/dir")
        test_data = {"key": "value"}
        
        # Should not raise exception
        storage.save_json("test.json", test_data)

    @patch('os.path.exists')
    def test_file_exists(self, mock_exists):
        """Test file_exists method."""
        mock_exists.return_value = True
        
        storage = StorageManager("/test/dir")
        result = storage.file_exists("test.json")
        
        assert result is True
        mock_exists.assert_called_once_with("/test/dir/test.json")

    @patch('os.makedirs')
    def test_ensure_directory(self, mock_makedirs):
        """Test ensure_directory method."""
        storage = StorageManager("/test/dir")
        storage.ensure_directory("subdir")
        
        mock_makedirs.assert_called_once_with("/test/dir/subdir", exist_ok=True)


class TestProfileManager:
    """Test ProfileManager functionality."""

    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock StorageManager for testing."""
        return MagicMock()

    def test_profile_manager_init(self, mock_storage_manager):
        """Test ProfileManager initialization."""
        pm = ProfileManager(mock_storage_manager)
        assert pm.storage_manager == mock_storage_manager

    def test_create_user_profile_new_user(self, mock_storage_manager):
        """Test creating a new user profile."""
        mock_storage_manager.load_json.return_value = {}
        
        pm = ProfileManager(mock_storage_manager)
        user_id = pm.create_user_profile("test_user")
        
        assert user_id == "test_user"
        mock_storage_manager.save_json.assert_called()

    def test_create_user_profile_existing_user(self, mock_storage_manager):
        """Test creating profile for existing user."""
        mock_storage_manager.load_json.return_value = {
            "user_id": "test_user",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        pm = ProfileManager(mock_storage_manager)
        user_id = pm.create_user_profile("test_user")
        
        assert user_id == "test_user"
        # Should not save again for existing user
        mock_storage_manager.save_json.assert_not_called()

    def test_get_user_profile_exists(self, mock_storage_manager):
        """Test getting existing user profile."""
        profile_data = {
            "user_id": "test_user",
            "preferences": {"theme": "dark"}
        }
        mock_storage_manager.load_json.return_value = profile_data
        
        pm = ProfileManager(mock_storage_manager)
        profile = pm.get_user_profile("test_user")
        
        assert profile == profile_data

    def test_get_user_profile_not_exists(self, mock_storage_manager):
        """Test getting non-existent user profile."""
        mock_storage_manager.load_json.return_value = {}
        
        pm = ProfileManager(mock_storage_manager)
        profile = pm.get_user_profile("nonexistent_user")
        
        assert profile == {}

    def test_update_user_profile(self, mock_storage_manager):
        """Test updating user profile."""
        existing_profile = {
            "user_id": "test_user",
            "preferences": {"theme": "light"}
        }
        mock_storage_manager.load_json.return_value = existing_profile
        
        pm = ProfileManager(mock_storage_manager)
        updates = {"preferences": {"theme": "dark", "language": "en"}}
        
        success = pm.update_user_profile("test_user", updates)
        
        assert success is True
        mock_storage_manager.save_json.assert_called()

    def test_update_user_profile_nonexistent(self, mock_storage_manager):
        """Test updating non-existent user profile."""
        mock_storage_manager.load_json.return_value = {}
        
        pm = ProfileManager(mock_storage_manager)
        updates = {"preferences": {"theme": "dark"}}
        
        success = pm.update_user_profile("nonexistent_user", updates)
        
        assert success is False
        mock_storage_manager.save_json.assert_not_called()

    @patch('os.listdir')
    def test_list_users(self, mock_listdir, mock_storage_manager):
        """Test listing all users."""
        mock_listdir.return_value = [
            "user1_profile.json",
            "user2_profile.json", 
            "other_file.txt",
            "user3_profile.json"
        ]
        
        pm = ProfileManager(mock_storage_manager)
        users = pm.list_users()
        
        expected_users = ["user1", "user2", "user3"]
        assert set(users) == set(expected_users)

    @patch('os.path.exists')
    def test_user_exists_true(self, mock_exists, mock_storage_manager):
        """Test checking if user exists - positive case."""
        mock_exists.return_value = True
        
        pm = ProfileManager(mock_storage_manager)
        exists = pm.user_exists("test_user")
        
        assert exists is True

    @patch('os.path.exists')
    def test_user_exists_false(self, mock_exists, mock_storage_manager):
        """Test checking if user exists - negative case."""
        mock_exists.return_value = False
        
        pm = ProfileManager(mock_storage_manager)
        exists = pm.user_exists("nonexistent_user")
        
        assert exists is False 