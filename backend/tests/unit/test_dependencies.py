"""Tests for dependency injection functions."""

import pytest
from unittest.mock import Mock
from dependencies import (
    get_or_create_user_id,
    get_existing_user_id,
    ensure_guest_user_exists,
    generate_display_name_from_user_id,
    GUEST_USER_ID,
    GUEST_DISPLAY_NAME,
    profile_manager
)


class TestGuestUserSystem:
    """Test the guest user system functionality."""
    
    def test_ensure_guest_user_exists(self):
        """Test that ensure_guest_user_exists creates the guest user."""
        # Guest user should exist after calling ensure_guest_user_exists
        ensure_guest_user_exists()
        assert profile_manager.user_exists(GUEST_USER_ID)
        
        # Verify guest user data
        guest_data = profile_manager.get_user(GUEST_USER_ID)
        assert guest_data is not None
        assert guest_data["user_id"] == GUEST_USER_ID
        assert guest_data["metadata"]["display_name"] == GUEST_DISPLAY_NAME
        assert guest_data["metadata"]["is_guest"] is True
        assert guest_data["created_at"] == 0  # System default
    
    def test_get_or_create_user_id_no_header(self):
        """Test that get_or_create_user_id returns guest user when no header provided."""
        result = get_or_create_user_id(None)
        assert result == GUEST_USER_ID
    
    def test_get_or_create_user_id_invalid_user(self):
        """Test that get_or_create_user_id returns guest user for invalid user."""
        result = get_or_create_user_id("non-existent-user")
        assert result == GUEST_USER_ID
    
    def test_get_or_create_user_id_valid_user(self):
        """Test that get_or_create_user_id returns valid user when provided."""
        # Create a test user first
        test_user_id = profile_manager.create_user({"display_name": "Test User"})
        
        # Should return the test user when valid
        result = get_or_create_user_id(test_user_id)
        assert result == test_user_id
        
        # Clean up
        profile_manager.delete_user(test_user_id)
    
    def test_get_existing_user_id_valid_user(self):
        """Test get_existing_user_id with valid user."""
        result = get_existing_user_id(GUEST_USER_ID)
        assert result == GUEST_USER_ID
    
    def test_get_existing_user_id_invalid_user(self):
        """Test get_existing_user_id with invalid user."""
        result = get_existing_user_id("non-existent-user")
        assert result is None
    
    def test_get_existing_user_id_no_header(self):
        """Test get_existing_user_id with no header."""
        result = get_existing_user_id(None)
        assert result is None
    
    def test_generate_display_name_guest_user(self):
        """Test that generate_display_name_from_user_id handles guest user specially."""
        result = generate_display_name_from_user_id(GUEST_USER_ID)
        assert result == GUEST_DISPLAY_NAME
    
    def test_generate_display_name_friendly_format(self):
        """Test display name generation for friendly format IDs."""
        result = generate_display_name_from_user_id("happy-cat-42")
        assert result == "Happy Cat 42"
    
    def test_generate_display_name_fallback(self):
        """Test display name generation fallback."""
        result = generate_display_name_from_user_id("test123456")
        assert result == "User 123456" 