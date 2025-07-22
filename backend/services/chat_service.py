from logging_config import get_logger
from nodes.topic_extractor_node import topic_extractor_node
from dependencies import research_manager

logger = get_logger(__name__)


async def extract_and_store_topics_async(state: dict, user_id: str, session_id: str, conversation_context: str):
    """Background function to extract and store topic suggestions."""
    try:
        logger.info(f"🔍 Background: Starting topic extraction for session {session_id}")

        # Create a clean state for topic extraction that includes useful context
        # but avoids overwhelming information that could confuse the LLM
        clean_state = {
            "messages": state.get("messages", []),
            "user_id": user_id,
            "session_id": session_id,
            "model": state.get("model", "gpt-4o-mini"),
            "module_results": {},
            "workflow_context": {},
            # Include memory context but the prompt will ensure it's used appropriately
            "memory_context": state.get("memory_context")
        }
        
        logger.debug(f"🔍 Background: Using clean state with {len(clean_state['messages'])} messages")
        
        # Debug: Log what's in the original state that might be causing issues
        original_keys = list(state.keys())
        logger.debug(f"🔍 Background: Original state keys: {original_keys}")
        
        if "memory_context" in state:
            memory_preview = str(state["memory_context"])[:200] + "..." if state["memory_context"] else "None"
            logger.info(f"🔍 Background: Memory context in original state: {memory_preview}")
        else:
            logger.info("🔍 Background: No memory_context key in original state")
        
        # Debug: Log the messages we're using for topic extraction
        for i, msg in enumerate(clean_state["messages"][-3:]):  # Last 3 messages
            if hasattr(msg, 'content'):
                content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                logger.debug(f"🔍 Background: Clean message {i}: {msg.__class__.__name__}: {content}")
        
        # Debug: Log if memory context is being passed to topic extraction
        if clean_state.get("memory_context"):
            logger.info(f"🔍 Background: Passing memory context to topic extraction: {str(clean_state['memory_context'])[:100]}...")
        else:
            logger.info("🔍 Background: No memory context being passed to topic extraction")

        # Run topic extraction on the clean conversation state
        updated_state = topic_extractor_node(clean_state)

        # Check if topic extraction was successful
        topic_results = updated_state.get("module_results", {}).get("topic_extractor", {})

        if topic_results.get("success", False):
            raw_topics = topic_results.get("result", [])

            if raw_topics:
                success = research_manager.store_topic_suggestions(
                    user_id=user_id,
                    session_id=session_id,
                    topics=raw_topics,
                    conversation_context=conversation_context,
                )

                if success:
                    logger.info(
                        f"🔍 Background: Stored {len(raw_topics)} topic suggestions for user {user_id}, session {session_id}"
                    )
                else:
                    logger.error(
                        f"🔍 Background: Failed to store topic suggestions for user {user_id}, session {session_id}"
                    )
            else:
                logger.info(f"🔍 Background: No topics extracted for session {session_id}")
        else:
            logger.warning(
                f"🔍 Background: Topic extraction failed for session {session_id}: {topic_results.get('message', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(
            f"🔍 Background: Error in topic extraction for session {session_id}: {str(e)}",
            exc_info=True,
        )
