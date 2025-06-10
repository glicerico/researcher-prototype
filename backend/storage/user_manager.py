"""
UserManager orchestrates profile and research managers for backward compatibility.
"""

from .storage_manager import StorageManager
from .profile_manager import ProfileManager
from .research_manager import ResearchManager


class UserManager:
    """Facade for profile and research operations."""

    def __init__(self, storage_manager: StorageManager):
        self.profile = ProfileManager(storage_manager)
        self.research = ResearchManager(storage_manager, self.profile)

    def __getattr__(self, name):
        if hasattr(self.profile, name):
            return getattr(self.profile, name)
        if hasattr(self.research, name):
            return getattr(self.research, name)
        raise AttributeError(name)
