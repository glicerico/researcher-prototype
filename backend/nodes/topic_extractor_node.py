"""
Topic extractor node that analyzes conversations to identify research-worthy topics.
"""
from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ChatOpenAI,
    config,
    get_current_datetime_str,
    TOPIC_EXTRACTOR_SYSTEM_PROMPT,
    TopicSuggestions,
    research_manager
)
from typing import List, Dict, Any


def topic_extractor_node(state: ChatState) -> ChatState:
    """Extract research-worthy topics from the conversation."""
    logger.info("🔍 Topic Extractor: Analyzing conversation for research topics")
    
    current_time_str = get_current_datetime_str()
    
    # Use configuration parameters
    topic_model = config.TOPIC_EXTRACTION_MODEL
    min_confidence = config.TOPIC_MIN_CONFIDENCE
    max_suggestions = config.TOPIC_MAX_SUGGESTIONS
    temperature = config.TOPIC_EXTRACTION_TEMPERATURE
    max_tokens = config.TOPIC_EXTRACTION_MAX_TOKENS
    
    # Get conversation messages for analysis
    messages = state.get("messages", [])
    user_id = state.get("user_id")
    
    if len(messages) < 2:  # Need at least one user message and one AI response
        logger.debug("🔍 Topic Extractor: Insufficient conversation history for topic extraction")
        state["module_results"]["topic_extractor"] = {
            "success": False,
            "result": [],
            "message": "Insufficient conversation history"
        }
        return state
    
    # Log conversation length for debugging
    logger.info(f"🔍 Topic Extractor: Analyzing conversation with {len(messages)} messages")
    
    # Get existing topics for this user to avoid duplicates
    existing_topics_section = ""
    if user_id:
        try:
            all_existing_topics = research_manager.get_all_topic_suggestions(user_id)
            if all_existing_topics:
                # Create a formatted list of existing topics
                topic_list = []
                for session_id, topics in all_existing_topics.items():
                    for topic in topics:
                        topic_name = topic.get("topic_name", "Unknown")
                        description = topic.get("description", "")
                        confidence = topic.get("confidence_score", 0)
                        topic_list.append(f"• {topic_name} (confidence: {confidence:.2f}) - {description}")
                
                if topic_list:
                    existing_topics_list = "\n".join(topic_list[:20])  # Limit to top 20 to avoid huge prompts
                    existing_topics_section = f"EXISTING RESEARCH TOPICS:\nThe user is already tracking the following research topics:\n\n{existing_topics_list}\n\nAvoid suggesting topics that are too similar to these. Instead, look for complementary research areas or more specific sub-topics that would add value to their research portfolio."
                    logger.debug(f"🔍 Topic Extractor: Including {len(topic_list)} existing topics in context")
                else:
                    existing_topics_section = ""
            else:
                existing_topics_section = ""
                logger.debug("🔍 Topic Extractor: No existing topics found for user")
        except Exception as e:
            logger.warning(f"🔍 Topic Extractor: Error retrieving existing topics: {str(e)}")
            existing_topics_section = ""
    else:
        existing_topics_section = ""
        logger.debug("🔍 Topic Extractor: No user_id available for existing topics lookup")
    
    # Create system message with formatted prompt including existing topics
    system_message_content = TOPIC_EXTRACTOR_SYSTEM_PROMPT.format(
        current_time=current_time_str,
        existing_topics_section=existing_topics_section,
        min_confidence=min_confidence,
        max_suggestions=max_suggestions
    )
    
    # Initialize the model for topic extraction
    llm = ChatOpenAI(
        model=topic_model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=config.OPENAI_API_KEY
    )
    
    # Create structured output model
    structured_extractor = llm.with_structured_output(TopicSuggestions)
    
    # Prepare messages for the LLM
    messages_for_llm = [SystemMessage(content=system_message_content)]
    messages_for_llm.extend(messages)
    
    try:
        logger.debug(f"Sending {len(messages_for_llm)} messages to Topic Extractor")
        
        # Get structured response from LLM
        topic_suggestions = structured_extractor.invoke(messages_for_llm)
        
        # Convert Pydantic models to dictionaries for storage
        valid_topics = []
        for topic in topic_suggestions.topics:
            # Filter by confidence threshold
            if topic.confidence_score >= min_confidence:
                valid_topics.append({
                    "name": topic.name,
                    "description": topic.description,
                    "confidence_score": topic.confidence_score
                })
        
        # Sort by confidence score (highest first)
        valid_topics.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        # Store in module_results following the existing pattern
        state["module_results"]["topic_extractor"] = {
            "success": True,
            "result": valid_topics,
            "message": f"Extracted {len(valid_topics)} research-worthy topics"
        }
        
        if valid_topics:
            topic_names = [t["name"] for t in valid_topics]
            logger.info(f"🔍 Topic Extractor: Extracted {len(valid_topics)} topics: {', '.join(topic_names)}")
        else:
            logger.info("🔍 Topic Extractor: No research-worthy topics identified above confidence threshold")
            
    except Exception as e:
        logger.error(f"Error in topic_extractor_node: {str(e)}", exc_info=True)
        state["module_results"]["topic_extractor"] = {
            "success": False,
            "result": [],
            "message": f"Error during topic extraction: {str(e)}"
        }
    
    return state 