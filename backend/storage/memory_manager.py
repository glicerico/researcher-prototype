"""
Memory Manager for handling short-term and long-term memory.
"""

import time
from pinecone import Pinecone
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
import json

# Import the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

import config
from .storage_manager import StorageManager
from .user_manager import UserManager
from .conversation_manager import ConversationManager

class MemoryManager:
    """
    Memory manager for handling short-term and long-term memory.
    Short-term memory (STM) keeps recent messages in-memory.
    Long-term memory (LTM) stores older messages in Pinecone vector database.
    """
    
    def __init__(
        self, 
        storage_manager: StorageManager, 
        user_manager: UserManager,
        conversation_manager: ConversationManager
    ):
        """Initialize the memory manager.
        
        Args:
            storage_manager: The storage manager instance
            user_manager: The user manager instance
            conversation_manager: The conversation manager instance
        """
        self.storage = storage_manager
        self.user_manager = user_manager
        self.conversation_manager = conversation_manager
        self.stm_capacity = config.STM_CAPACITY
        self.pinecone_index_name = config.PINECONE_INDEX_NAME
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        
        # Connect to the index
        self.index = self.pc.Index(self.pinecone_index_name)
        
        # Cache for short-term memory
        # Structure: {conversation_id: List[messages]}
        self.stm_cache = {}
    
    def add_to_memory(
        self, 
        user_id: str, 
        conversation_id: str, 
        content: str, 
        role: str,
        memory_type: str = "message",  # "message", "search", "analysis"
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add content to memory (STM if it has room, otherwise LTM).
        
        Args:
            user_id: The user ID
            conversation_id: The conversation ID
            content: The content to store
            role: The role (user, assistant, system)
            memory_type: Type of memory (message, search, analysis)
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        # Create metadata if not provided
        if metadata is None:
            metadata = {}
        
        # Add standard metadata
        memory_metadata = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "role": role,
            "memory_type": memory_type,
            "timestamp": time.time(),
            **metadata
        }
        
        # Add to STM cache first
        if conversation_id not in self.stm_cache:
            self.stm_cache[conversation_id] = []
        
        # Create memory object
        memory_item = {
            "content": content,
            "metadata": memory_metadata
        }
        
        # Add to STM
        self.stm_cache[conversation_id].append(memory_item)
        
        # Check if STM is over capacity
        if len(self.stm_cache[conversation_id]) > self.stm_capacity:
            # Get oldest message
            oldest_item = self.stm_cache[conversation_id].pop(0)
            
            # Move to LTM
            self._add_to_ltm(oldest_item["content"], oldest_item["metadata"])
        
        return True
    
    def _add_to_ltm(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Add content to long-term memory (Pinecone).
        
        Args:
            content: The content to store
            metadata: The metadata for the content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate a unique ID
            vector_id = str(uuid.uuid4())
            
            # Prepare the record for Pinecone
            # For serverless indices with integrated embeddings via inference API
            record = {
                "id": vector_id,
                "metadata": metadata,
                "text": content  # Provide text directly for embedding generation
            }
            
            # Using upsert_records for the serverless index with integrated embeddings
            self.index.upsert_records(records=[record])
            
            logger.info(f"Added content to LTM: {vector_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding to LTM: {str(e)}")
            return False
    
    def query_ltm(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query long-term memory for relevant content.
        
        Args:
            query: The query text
            user_id: Optional user ID to filter results
            conversation_id: Optional conversation ID to filter results
            top_k: Number of results to return
            memory_type: Optional memory type to filter by
            filter_criteria: Additional filter criteria
            
        Returns:
            List of matching memory items with content and metadata
        """
        try:
            # Build filter based on provided parameters
            filter_dict = {}
            
            if user_id:
                filter_dict["user_id"] = {"$eq": user_id}
                
            if conversation_id:
                filter_dict["conversation_id"] = {"$eq": conversation_id}
                
            if memory_type:
                filter_dict["memory_type"] = {"$eq": memory_type}
                
            # Add any additional filter criteria
            if filter_criteria:
                for key, value in filter_criteria.items():
                    filter_dict[key] = {"$eq": value}
            
            # Use query_text for natural language search with serverless indexes
            # that have integrated embeddings via the inference API
            query_response = self.index.query_text(
                query_text=query,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
            
            # Format results
            results = []
            for match in query_response.matches:
                results.append({
                    "content": match.text,  # In new API, text is directly available
                    "score": match.score,
                    "metadata": match.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying LTM: {str(e)}")
            return []
    
    def get_stm(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get the current short-term memory for a conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            List of memory items in STM
        """
        return self.stm_cache.get(conversation_id, [])
    
    def clear_stm(self, conversation_id: str) -> bool:
        """Clear the short-term memory for a conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.stm_cache:
            del self.stm_cache[conversation_id]
        return True
    
    def add_search_result(self, user_id: str, conversation_id: str, query: str, result: str) -> bool:
        """Add a search result to memory.
        
        Args:
            user_id: The user ID
            conversation_id: The conversation ID
            query: The search query
            result: The search result
            
        Returns:
            True if successful, False otherwise
        """
        metadata = {
            "query": query,
        }
        
        return self.add_to_memory(
            user_id=user_id,
            conversation_id=conversation_id,
            content=result,
            role="system",
            memory_type="search",
            metadata=metadata
        )
    
    def add_analysis_result(self, user_id: str, conversation_id: str, analysis_type: str, result: str) -> bool:
        """Add an analysis result to memory.
        
        Args:
            user_id: The user ID
            conversation_id: The conversation ID
            analysis_type: The type of analysis
            result: The analysis result
            
        Returns:
            True if successful, False otherwise
        """
        metadata = {
            "analysis_type": analysis_type,
        }
        
        return self.add_to_memory(
            user_id=user_id,
            conversation_id=conversation_id,
            content=result,
            role="system",
            memory_type="analysis",
            metadata=metadata
        )
        
    def get_relevant_memories(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        top_k: int = 3,
        include_stm: bool = True
    ) -> List[Dict[str, Any]]:
        """Get relevant memories for a query, combining STM and LTM.
        
        Args:
            query: The query text
            user_id: Optional user ID to filter results
            conversation_id: Optional conversation ID
            top_k: Number of results to return from LTM
            include_stm: Whether to include STM in results
            
        Returns:
            List of relevant memories
        """
        memories = []
        
        # Get relevant memories from LTM
        ltm_results = self.query_ltm(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            top_k=top_k
        )
        
        memories.extend(ltm_results)
        
        # Include STM if requested and conversation_id is provided
        if include_stm and conversation_id and conversation_id in self.stm_cache:
            stm_items = self.stm_cache[conversation_id]
            
            # Mark these as coming from STM
            for item in stm_items:
                item_copy = item.copy()
                if "metadata" not in item_copy:
                    item_copy["metadata"] = {}
                item_copy["metadata"]["source"] = "stm"
                memories.append(item_copy)
        
        return memories 