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
    Uses singleton pattern to prevent multiple instantiations and duplicate log messages.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Implement singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the Zep manager (only runs once due to singleton pattern)."""
        if self._initialized:
            return
            
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
        
        self._initialized = True
    
    def is_enabled(self) -> bool:
        """Check if Zep is enabled and properly configured."""
        return self.enabled and self.client is not None
    
    async def create_user(self, user_id: str, display_name: str = None) -> bool:
        """
        Create a user in Zep.
        
        Args:
            user_id: The ID of the user (e.g., "happy-cat-42")
            display_name: Optional display name, will generate from user_id if not provided
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        try:
            # Parse display name or generate from user_id
            first_name, last_name = self._parse_user_name(user_id, display_name)
            
            # Check if user already exists
            try:
                await self.client.user.get(user_id)
                logger.debug(f"User {user_id} already exists in Zep")
                return True
            except Exception:
                # User doesn't exist, create them
                pass
            
            # Create user
            user = await self.client.user.add(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                metadata={"created_by": "researcher-prototype"}
            )
            
            logger.info(f"Created ZEP user: {user_id} ({first_name} {last_name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create ZEP user {user_id}: {str(e)}")
            return False
    
    async def create_session(self, session_id: str, user_id: str) -> bool:
        """
        Create a session in Zep.
        
        Args:
            session_id: The session ID
            user_id: The user ID that owns this session
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        try:
            # Check if session already exists
            try:
                await self.client.memory.get(session_id)
                logger.debug(f"Session {session_id} already exists in Zep")
                return True
            except Exception:
                # Session doesn't exist, create it
                pass
            
            # Try to create session - this will fail if user doesn't exist
            # so we'll create the user first if needed
            await self.create_user(user_id)
            
            # Create session
            session = await self.client.memory.add_session(
                session_id=session_id,
                user_id=user_id,
                metadata={"created_by": "researcher-prototype"}
            )
            
            logger.info(f"Created ZEP session: {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create ZEP session {session_id}: {str(e)}")
            return False
    
    def _parse_user_name(self, user_id: str, display_name: str = None) -> tuple[str, str]:
        """
        Parse first and last name from user_id or display_name.
        
        Args:
            user_id: The user ID (e.g., "happy-cat-42")
            display_name: Optional display name (e.g., "Happy Cat 42")
            
        Returns:
            Tuple of (first_name, last_name)
        """
        if display_name:
            # Split display name into parts
            parts = display_name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = " ".join(parts[1:])
            else:
                first_name = display_name
                last_name = ""
        else:
            # Parse from user_id (adjective-noun-number)
            if len(user_id.split('-')) == 3 and not user_id.startswith('user-'):
                parts = user_id.split('-')
                adjective = parts[0].capitalize()
                noun = parts[1].capitalize()
                number = parts[2]
                first_name = adjective
                last_name = f"{noun} {number}"
            else:
                # Fallback for non-standard user IDs
                first_name = "User"
                last_name = user_id[-6:] if len(user_id) > 6 else user_id
        
        logger.info(f"🏷️  Parsed name for user {user_id}: '{first_name} {last_name}' (from {'display_name' if display_name else 'user_id'})")
        return first_name, last_name

    async def store_conversation_turn(
        self, 
        user_id: str, 
        user_message: str, 
        ai_response: str,
        session_id: str
    ) -> bool:
        """
        Store a conversation turn (user message + AI response) in Zep.
        
        Args:
            user_id: The ID of the user
            user_message: The user's message content
            ai_response: The AI's response content
            session_id: The session ID (must be provided)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.debug("Zep is not enabled, skipping storage")
            return False
        
        if not session_id:
            logger.error("Session ID is required for storing conversation turn")
            return False
        
        try:
            # Add user message
            user_success = await self.add_message(session_id, user_message, "user")
            if not user_success:
                return False
            
            # Add assistant response
            assistant_success = await self.add_message(session_id, ai_response, "assistant")
            if not assistant_success:
                return False
            
            logger.debug(f"Stored conversation turn for user {user_id} in session {session_id}")
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
            # Memory retrieval currently uses session_id as the key, but it does
            # retrieve larger memory context.
            # TODO: Compare with use of zep.graph.search() on nodes and edges.
            memory = await self.client.memory.get(session_id=session_id)
            return memory.context if memory else None
            
        except Exception as e:
            # Log but don't error - this could be because session doesn't exist yet
            # which is normal for new sessions
            logger.debug(f"No memory context found for session {session_id}: {str(e)}")
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
            search_results = await self.client.graph.search(
                user_id=user_id, 
                query=query, 
                limit=limit
            )
            
            # Filter for edges and extract facts
            facts = []
            if search_results:
                for item in search_results:
                    if hasattr(item, 'source_node_uuid') and hasattr(item, 'target_node_uuid'):
                        # This looks like an edge
                        if hasattr(item, 'fact') and item.fact:
                            facts.append(item.fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search user facts in Zep: {str(e)}")
            return []

    async def add_message(self, session_id: str, content: str, role_type: str = "system") -> bool:
        """
        Add a single message to a session.
        
        Args:
            session_id: The session ID
            content: The message content
            role_type: The role type (system, user, assistant)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        try:
            message = Message(
                role_type=role_type,
                content=content
            )
            
            await self.client.memory.add(
                session_id=session_id,
                messages=[message]
            )
            
            logger.debug(f"Added {role_type} message to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {str(e)}")
            return False 