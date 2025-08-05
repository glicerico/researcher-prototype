import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import tempfile

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.storage_manager import StorageManager
from storage.profile_manager import ProfileManager
from storage.zep_manager import ZepManager


class TestStorageManager:
    """Test StorageManager functionality."""

    def test_storage_manager_init(self):
        """Test StorageManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            assert str(storage.base_dir) == temp_dir
            assert os.path.exists(temp_dir)

    def test_load_json_file_not_exists(self):
        """Test JSON loading when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            result = storage.read("nonexistent.json")
            
            assert result == {}

    def test_save_json_error_handling(self):
        """Test JSON saving error handling with permission issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            test_data = {"key": "value"}
            
            # Mock the write operation to fail
            with patch('storage.storage_manager.shutil.move', side_effect=PermissionError("Permission denied")):
                result = storage.write("test.json", test_data)
                assert result is False

    def test_file_operations_real(self):
        """Test actual file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            test_data = {"key": "value", "number": 123}
            
            # Test write
            success = storage.write("test.json", test_data)
            assert success is True
            
            # Test read
            result = storage.read("test.json")
            assert result == test_data

    def test_append_operation(self):
        """Test append operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            
            # Test append to non-existent file
            success = storage.append("test.json", "items", "item1")
            assert success is True
            
            # Read and verify
            result = storage.read("test.json")
            assert result == {"items": ["item1"]}
            
            # Test append to existing file
            success = storage.append("test.json", "items", "item2")
            assert success is True
            
            result = storage.read("test.json")
            assert result == {"items": ["item1", "item2"]}

    def test_delete_operation(self):
        """Test delete operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            test_data = {"key": "value"}
            
            # Create file
            storage.write("test.json", test_data)
            
            # Delete file
            success = storage.delete("test.json")
            assert success is True
            
            # Verify file is gone
            result = storage.read("test.json")
            assert result == {}

    def test_list_files_operation(self):
        """Test list files operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            
            # Create some test files
            storage.write("file1.json", {"test": 1})
            storage.write("file2.json", {"test": 2})
            
            # List files
            files = storage.list_files(".")
            assert "file1.json" in files
            assert "file2.json" in files


class TestProfileManager:
    """Test ProfileManager functionality."""

    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock StorageManager for testing."""
        return MagicMock()

    def test_profile_manager_init(self, mock_storage_manager):
        """Test ProfileManager initialization."""
        pm = ProfileManager(mock_storage_manager)
        assert pm.storage == mock_storage_manager

    def test_create_user_new_user(self, mock_storage_manager):
        """Test creating a new user profile."""
        mock_storage_manager.write.return_value = True
        
        pm = ProfileManager(mock_storage_manager)
        # Mock the user_exists method
        with patch.object(pm, 'user_exists', return_value=False):
            user_id = pm.create_user()
        
        assert user_id != ""  # Should return a valid user ID
        mock_storage_manager.write.assert_called_once()

    def test_get_user_profile_exists(self, mock_storage_manager):
        """Test getting existing user profile."""
        profile_data = {
            "user_id": "test_user",
            "personality": {"style": "helpful", "tone": "friendly"}
        }
        mock_storage_manager.read.return_value = profile_data
        
        pm = ProfileManager(mock_storage_manager)
        profile = pm.get_user("test_user")
        
        assert profile == profile_data

    def test_get_user_profile_not_exists(self, mock_storage_manager):
        """Test getting non-existent user profile."""
        mock_storage_manager.read.return_value = {}
        
        pm = ProfileManager(mock_storage_manager)
        profile = pm.get_user("nonexistent_user")
        
        assert profile == {}

    def test_update_user_profile(self, mock_storage_manager):
        """Test updating user profile."""
        existing_profile = {
            "user_id": "test_user",
            "personality": {"style": "helpful", "tone": "friendly"}
        }
        mock_storage_manager.read.return_value = existing_profile
        mock_storage_manager.write.return_value = True
        
        pm = ProfileManager(mock_storage_manager)
        updates = {"personality": {"style": "professional", "tone": "formal"}}
        
        success = pm.update_user("test_user", updates)
        
        assert success is True
        mock_storage_manager.write.assert_called_once()

    def test_update_user_profile_nonexistent(self, mock_storage_manager):
        """Test updating non-existent user profile."""
        mock_storage_manager.read.return_value = {}
        
        pm = ProfileManager(mock_storage_manager)
        updates = {"personality": {"style": "professional"}}
        
        success = pm.update_user("nonexistent_user", updates)
        
        assert success is False
        mock_storage_manager.write.assert_not_called()

    def test_user_exists_with_real_file_operations(self):
        """Test user_exists with real file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            # Test non-existent user
            assert pm.user_exists("nonexistent_user") is False
            
            # Create a user and test existence
            user_id = pm.create_user()
            assert pm.user_exists(user_id) is True

    def test_profile_manager_integration(self):
        """Test profile manager with real storage integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            # Create user
            user_id = pm.create_user(metadata={"test": "data"})
            assert user_id != ""
            
            # Get user
            profile = pm.get_user(user_id)
            assert profile["user_id"] == user_id
            assert profile["metadata"]["test"] == "data"
            
            # Update user
            success = pm.update_user(user_id, {"metadata": {"updated": True}})
            assert success is True
            
            # Verify update
            updated_profile = pm.get_user(user_id)
            assert updated_profile["metadata"]["updated"] is True

    def test_list_users_with_real_storage(self):
        """Test listing users with real storage operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            pm = ProfileManager(storage)
            
            # Create multiple users
            user1 = pm.create_user()
            user2 = pm.create_user()
            
            # List users
            users = pm.list_users()
            assert user1 in users
            assert user2 in users
            assert len(users) >= 2


class TestZepManager:
    """Test ZepManager chunking functionality."""
    
    def test_smart_chunk_content_small_message(self):
        """Test chunking with small message that doesn't need splitting."""
        zm = ZepManager()
        content = "This is a small message that fits in one chunk."
        chunks = zm._smart_chunk_content(content)
        
        assert len(chunks) == 1
        assert chunks[0] == content
    
    def test_smart_chunk_content_large_message(self):
        """Test chunking with large message that needs splitting."""
        zm = ZepManager()
        
        # Create a message larger than 2300 chars
        paragraph = "This is a test paragraph with multiple sentences. It contains enough text to test the chunking logic properly. "
        large_content = paragraph * 25  # ~2750 characters
        
        chunks = zm._smart_chunk_content(large_content)
        
        # Should be split into multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be under the limit
        for chunk in chunks:
            assert len(chunk) <= 2300
        
        # All chunks combined should equal original content (roughly)
        combined_length = sum(len(chunk) for chunk in chunks)
        # Allow for some variation due to splitting and spacing
        assert abs(combined_length - len(large_content.strip())) < 100
    
    def test_smart_chunk_content_preserves_sentences(self):
        """Test that chunking preserves sentence boundaries."""
        zm = ZepManager()
        
        sentences = [
            "First sentence is here.",
            "Second sentence follows immediately.",  
            "Third sentence completes the thought."
        ]
        content = " ".join(sentences)
        
        chunks = zm._smart_chunk_content(content, max_chunk_size=50)  # Force splitting
        
        # Should split but preserve complete sentences
        combined = " ".join(chunks).replace("  ", " ")  # Normalize spaces
        assert "First sentence is here." in combined
        assert "Second sentence follows immediately." in combined
        assert "Third sentence completes the thought." in combined
    
    def test_split_by_sentences(self):
        """Test sentence splitting functionality."""
        zm = ZepManager()
        
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        sentences = zm._split_by_sentences(text)
        
        assert len(sentences) == 4
        assert "First sentence." in sentences[0]
        assert "Second sentence!" in sentences[1]  
        assert "Third sentence?" in sentences[2]
        assert "Fourth sentence." in sentences[3]
    
    def test_hard_split(self):
        """Test hard character splitting as fallback."""
        zm = ZepManager()
        
        text = "a" * 100  # 100 character string
        chunks = zm._hard_split(text, 30)
        
        assert len(chunks) == 4  # 30, 30, 30, 10
        assert len(chunks[0]) == 30
        assert len(chunks[1]) == 30
        assert len(chunks[2]) == 30
        assert len(chunks[3]) == 10 