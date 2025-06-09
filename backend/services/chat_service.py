from logging_config import get_logger
from nodes.topic_extractor_node import topic_extractor_node
from dependencies import user_manager

logger = get_logger(__name__)


async def extract_and_store_topics_async(state: dict, user_id: str, session_id: str, conversation_context: str):
    """Background function to extract and store topic suggestions."""
    try:
        logger.info(f"🔍 Background: Starting topic extraction for session {session_id}")

        # Run topic extraction on the conversation state
        updated_state = topic_extractor_node(state)

        # Check if topic extraction was successful
        topic_results = updated_state.get("module_results", {}).get("topic_extractor", {})

        if topic_results.get("success", False):
            raw_topics = topic_results.get("result", [])

            if raw_topics:
                success = user_manager.store_topic_suggestions(
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
