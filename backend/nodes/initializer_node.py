"""
Initializer node for setting up user and state.
"""

from datetime import datetime
from langchain_core.messages import trim_messages, HumanMessage
from nodes.base import (
    ChatState,
    logger,
    config,
    profile_manager,
    zep_manager,
    queue_status,
)
from dependencies import get_or_create_user_id, GUEST_USER_ID


async def initializer_node(state: ChatState) -> ChatState:
    """Handles user and initial state setup, including session management and memory context retrieval."""
    logger.info("🔄 Initializer: Setting up user state and session")
    queue_status(state.get("session_id"), "Initializing session...")

    # Initialize state objects if they don't exist
    state["workflow_context"] = state.get("workflow_context", {})
    state["module_results"] = state.get("module_results", {})
    state["personality"] = state.get("personality", {"style": "helpful", "tone": "friendly"})

    # Handle user management - use guest user system instead of creating new users
    user_id = state.get("user_id")
    if not user_id or not profile_manager.user_exists(user_id):
        # Use the guest user system instead of creating new users
        user_id = get_or_create_user_id(user_id)
        state["user_id"] = user_id
        if user_id == GUEST_USER_ID:
            logger.info(f"🔄 Initializer: Using guest user: {user_id}")
        else:
            logger.info(f"🔄 Initializer: Using existing user: {user_id}")
    else:
        # Update personality from stored preferences if not explicitly provided
        if not state.get("personality"):
            state["personality"] = profile_manager.get_personality(user_id)

    # Handle session ID generation or retrieval
    session_id = state.get("session_id", None)
    if not session_id:
        # Generate a new session ID for this conversation thread
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        session_id = f"{user_id}-{timestamp}"
        state["session_id"] = session_id
        logger.info(f"🔄 Initializer: Generated new session ID: {session_id}")

        # Create session in ZEP when we generate a new session ID
        if zep_manager.is_enabled():
            try:
                await zep_manager.create_thread(session_id, user_id)

                # Add an empty message to prime the session and trigger context population
                await zep_manager.add_message(session_id, "Session initialized", "system")
                logger.debug(f"🔄 Initializer: Primed ZEP session {session_id} with initialization message")

            except Exception as e:
                logger.warning(f"Failed to create session in ZEP: {str(e)}")
                # Don't fail the request if ZEP session creation fails
    else:
        logger.info(f"🔄 Initializer: Using provided session ID: {session_id}")

    # Retrieve memory context from Zep if available
    memory_context = None
    if zep_manager.is_enabled():
        try:
            logger.info(f"🧠 Initializer: Retrieving memory context for session {session_id}")
            memory_context = await zep_manager.get_memory_context(session_id)

            if memory_context:
                logger.info(f"🧠 Initializer: Retrieved memory context from ZEP.")
                # Store in workflow context for debugging/inspection
                state["workflow_context"]["memory_context_retrieved"] = True
            else:
                logger.info("🧠 Initializer: No memory context found for this session")
                state["workflow_context"]["memory_context_retrieved"] = False

        except Exception as e:
            logger.error(f"🧠 Initializer: Error retrieving memory context: {str(e)}")
            state["workflow_context"]["memory_context_error"] = str(e)
    else:
        logger.info("🧠 Initializer: Zep is not enabled, skipping memory context retrieval")

    # Store memory context in state (will be None if not available)
    state["memory_context"] = memory_context

    # Trim messages to keep only the most recent ones within the configured limit
    messages = state.get("messages", [])
    if messages and len(messages) > config.MAX_MESSAGES_IN_STATE:
        logger.info(f"🔄 Initializer: Trimming messages from {len(messages)} to {config.MAX_MESSAGES_IN_STATE}")

        # Use trim_messages to properly trim while maintaining valid chat history
        trimmed_messages = trim_messages(
            messages,
            max_tokens=config.MAX_MESSAGES_IN_STATE,
            strategy="last",  # Keep the most recent messages
            token_counter=len,  # Use message count instead of token count
            include_system=True,  # Keep system messages if present
            start_on="human",  # Ensure valid chat history starts with human message
            allow_partial=False,  # Don't allow partial messages
        )

        state["messages"] = trimmed_messages
        logger.info(f"🔄 Initializer: Kept {len(state['messages'])} most recent messages")
    else:
        logger.info(f"🔄 Initializer: Processing {len(messages)} messages (within limit)")

    return state
