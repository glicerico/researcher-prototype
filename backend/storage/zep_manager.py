"""
Zep Memory Manager for storing chat interactions in knowledge graph.
"""

import uuid
from typing import Optional, List, Dict, Any
from zep_cloud.client import AsyncZep
from zep_cloud import Message

# Import the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

import config

class ZepManager:
    """
    Simple Zep manager for storing user messages and AI responses in knowledge graph.
    """
    
    def __init__(self):
        """Initialize the Zep manager."""
        self.enabled = config.ZEP_ENABLED
        self.client = None
        
        if self.enabled and config.ZEP_API_KEY:
            try:
                self.client = AsyncZep(api_key=config.ZEP_API_KEY)
                logger.info("Zep client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Zep client: {str(e)}")
                self.enabled = False
        else:
            logger.info("Zep is disabled or API key not provided")
    
    def is_enabled(self) -> bool:
        """Check if Zep is enabled and properly configured."""
        return self.enabled and self.client is not None
    
    async def store_conversation_turn(
        self, 
        user_id: str, 
        user_message: str, 
        ai_response: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Store a conversation turn (user message + AI response) in Zep.
        
        Args:
            user_id: The ID of the user
            user_message: The user's message content
            ai_response: The AI's response content
            session_id: Optional session ID, will generate one if not provided
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.debug("Zep is not enabled, skipping storage")
            return False
        
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Create messages for Zep
            messages = [
                Message(
                    role_type="user",
                    role="User",
                    content=user_message
                ),
                Message(
                    role_type="assistant", 
                    content=ai_response
                )
            ]
            
            # Store in Zep
            await self.client.memory.add(
                session_id=session_id,
                messages=messages
            )
            
            logger.debug(f"Successfully stored conversation turn for user {user_id} in session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store conversation in Zep: {str(e)}")
            return False
    
    async def get_memory_context(self, session_id: str) -> Optional[str]:
        """
        Get memory context for a session.
        
        Args:
            session_id: The session ID to get context for
            
        Returns:
            Memory context string or None if not available
        """
        if not self.is_enabled():
            return None
        
        try:
            memory = await self.client.memory.get(session_id=session_id)
            return memory.context if memory else None
            
        except Exception as e:
            logger.error(f"Failed to get memory context from Zep: {str(e)}")
            return None
    
    async def search_user_facts(self, user_id: str, query: str, limit: int = 5) -> List[str]:
        """
        Search for facts related to a user.
        
        Args:
            user_id: The user ID to search for
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of facts matching the query
        """
        if not self.is_enabled():
            return []
        
        try:
            edges = await self.client.graph.search(
                user_id=user_id, 
                text=query, 
                limit=limit, 
                search_scope="edges"
            )
            return [edge.fact for edge in edges if edge.fact]
            
        except Exception as e:
            logger.error(f"Failed to search user facts in Zep: {str(e)}")
            return [] 