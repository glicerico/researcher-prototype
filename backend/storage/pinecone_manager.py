"""
Pinecone Manager for long-term memory storage.
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Union
from pinecone import Pinecone

# Import the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

# Import configuration
import config

class PineconeManager:
    """
    Pinecone manager for handling long-term memory storage.
    """
    
    def __init__(self):
        """Initialize the Pinecone manager"""
        api_key = config.PINECONE_API_KEY
        if not api_key:
            logger.warning("PINECONE_API_KEY not found in configuration. Pinecone storage will not be available.")
            self.pc = None
            self.index = None
        else:
            self.pc = Pinecone(api_key=api_key)
            
            # Get the index host
            index_host = config.PINECONE_INDEX_HOST
            if not index_host:
                logger.warning("PINECONE_INDEX_HOST not found in configuration. Pinecone storage will not be available.")
                self.index = None
            else:
                try:
                    self.index = self.pc.Index(host=index_host)
                    logger.info("Pinecone index connected successfully.")
                except Exception as e:
                    logger.error(f"Failed to connect to Pinecone index: {e}")
                    self.index = None
    
    def is_available(self) -> bool:
        """Check if Pinecone storage is available."""
        return self.pc is not None and self.index is not None
    
    def store_messages(self, user_id: str, messages: List[Dict[str, Any]]) -> bool:
        """
        Store messages in Pinecone.
        
        Args:
            user_id: The ID of the user
            messages: List of messages to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Pinecone storage not available. Messages not stored.")
            return False
        
        if not messages:
            return True
        
        try:
            # Prepare records for Pinecone
            records = []
            
            for message in messages:
                # Skip system messages
                if message.get("role") == "system":
                    continue
                    
                # Generate a unique ID for this message
                message_id = str(uuid.uuid4())
                
                # Convert message to a record format
                record = {
                    "_id": message_id,
                    "text": message.get("content", ""),  # This will be embedded by Pinecone
                    "user_id": user_id,
                    "role": message.get("role", ""),
                    "timestamp": message.get("timestamp", time.time()),
                    "conversation_id": message.get("metadata", {}).get("conversation_id", ""),
                }
                
                records.append(record)
            
            # Skip if no records to store after filtering out system messages
            if not records:
                logger.info(f"No non-system messages to store for user {user_id}")
                return True
                
            # Namespace is the user_id to keep messages separate by user
            namespace = f"user-{user_id}"
            
            # Upsert records to Pinecone
            self.index.upsert_records(namespace, records)
            logger.info(f"Stored {len(records)} messages in Pinecone for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store messages in Pinecone: {e}")
            return False 