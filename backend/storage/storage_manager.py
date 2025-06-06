"""
Storage Manager for handling file-based storage operations.
"""

import os
import json
import time
import shutil
import fcntl
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Import the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

class StorageManager:
    """
    Core storage manager for file-based persistence.
    Handles file I/O operations, caching, and file locking.
    """
    
    def __init__(self, base_dir: str = "./storage"):
        """Initialize the storage manager with the base storage directory."""
        self.base_dir = Path(base_dir)
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        self.cache_timestamps = {}  # Track when items were cached
        
        # Create base directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure that the required directory structure exists."""
        dirs = [
            self.base_dir,
            self.base_dir / "users",
        ]
        
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, path: str) -> Path:
        """Convert a relative path to an absolute path within the storage directory."""
        return self.base_dir / path
    
    def _read_file(self, path: str) -> Dict[str, Any]:
        """Read JSON data from a file with file locking."""
        file_path = self._get_file_path(path)
        
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r') as f:
                # Acquire a shared lock for reading
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    # Release the lock
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error reading file {path}: {str(e)}")
            return {}
    
    def _write_file(self, path: str, data: Dict[str, Any]) -> bool:
        """Write JSON data to a file with file locking."""
        file_path = self._get_file_path(path)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a temporary file for atomic writes
        tmp_path = file_path.with_suffix('.tmp')
        
        try:
            with open(tmp_path, 'w') as f:
                # Acquire an exclusive lock for writing
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                finally:
                    # Release the lock
                    fcntl.flock(f, fcntl.LOCK_UN)
            
            # Rename the temporary file to the target file (atomic operation)
            shutil.move(str(tmp_path), str(file_path))
            
            # Update cache
            self.cache[path] = data
            self.cache_timestamps[path] = time.time()
            
            return True
        except Exception as e:
            logger.error(f"Error writing file {path}: {str(e)}")
            # Clean up temporary file if it exists
            if tmp_path.exists():
                tmp_path.unlink()
            return False
    
    def read(self, path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Read data from storage with optional caching.
        
        Args:
            path: Relative path to the file within the storage directory
            use_cache: Whether to use the cache (default: True)
            
        Returns:
            The data as a dictionary
        """
        # Check cache first if enabled
        if use_cache and path in self.cache:
            # Check if cache is still valid
            cache_time = self.cache_timestamps.get(path, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self.cache[path]
        
        # Read from file
        data = self._read_file(path)
        
        # Update cache
        self.cache[path] = data
        self.cache_timestamps[path] = time.time()
        
        return data
    
    def write(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Write data to storage.
        
        Args:
            path: Relative path to the file within the storage directory
            data: The data to write
            
        Returns:
            True if successful, False otherwise
        """
        return self._write_file(path, data)
    
    def append(self, path: str, key: str, value: Any) -> bool:
        """
        Append a value to a list in the data.
        
        Args:
            path: Relative path to the file
            key: The key for the list to append to
            value: The value to append
            
        Returns:
            True if successful, False otherwise
        """
        data = self.read(path)
        
        if key not in data:
            data[key] = []
        
        if not isinstance(data[key], list):
            data[key] = [data[key]]
        
        data[key].append(value)
        
        return self.write(path, data)
    
    def delete(self, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            path: Relative path to the file
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_file_path(path)
        
        try:
            if file_path.exists():
                file_path.unlink()
            
            # Remove from cache
            if path in self.cache:
                del self.cache[path]
                del self.cache_timestamps[path]
            
            return True
        except Exception as e:
            logger.error(f"Error deleting file {path}: {str(e)}")
            return False
    
    def list_files(self, directory: str) -> List[str]:
        """
        List files in a directory.
        
        Args:
            directory: Relative path to the directory
            
        Returns:
            List of filenames (without directory path)
        """
        dir_path = self._get_file_path(directory)
        
        try:
            if not dir_path.exists() or not dir_path.is_dir():
                return []
            
            # Get only files, not directories
            return [f.name for f in dir_path.iterdir() if f.is_file()]
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {str(e)}")
            return []
    
    def list_directories(self, directory: str) -> List[str]:
        """
        List subdirectories in a directory.
        
        Args:
            directory: Relative path to the directory
            
        Returns:
            List of directory names
        """
        dir_path = self._get_file_path(directory)
        
        try:
            if not dir_path.exists() or not dir_path.is_dir():
                return []
            
            # Get only directories, not files
            return [d.name for d in dir_path.iterdir() if d.is_dir()]
        except Exception as e:
            logger.error(f"Error listing directories in {directory}: {str(e)}")
            return []
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    def backup(self, backup_dir: Optional[str] = None) -> bool:
        """
        Create a backup of the entire storage directory.
        
        Args:
            backup_dir: Directory to store the backup (default: {base_dir}_backup_{timestamp})
            
        Returns:
            True if successful, False otherwise
        """
        if backup_dir is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_dir = f"{self.base_dir}_backup_{timestamp}"
        
        try:
            shutil.copytree(self.base_dir, backup_dir)
            logger.info(f"Created backup at {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False 