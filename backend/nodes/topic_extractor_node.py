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
    
    # Get ACTIVE research topics for this user to provide context for better suggestions
    active_topics_section = ""
    if user_id:
        try:
            all_existing_topics = research_manager.get_all_topic_suggestions(user_id)
            if all_existing_topics:
                # Only include topics that the user has actively chosen to research
                active_topics = []
                for session_id, topics in all_existing_topics.items():
                    for topic in topics:
                        if topic.get("is_active_research", False):  # Only active research topics
                            topic_name = topic.get("topic_name", "Unknown")
                            description = topic.get("description", "")
                            active_topics.append(f"• {topic_name} - {description}")
                
                if active_topics:
                    # Limit to top 5 active research topics to provide context
                    active_topics_list = "\n".join(active_topics[:5])
                    active_topics_section = f"USER'S ACTIVE RESEARCH INTERESTS:\nThe user is currently researching these topics:\n\n{active_topics_list}\n\nUse this to understand the user's research interests, but ONLY suggest new topics that are related to the current conversation."
                    logger.debug(f"🔍 Topic Extractor: Including {len(active_topics)} active research topics for context")
                else:
                    active_topics_section = ""
                    logger.debug("🔍 Topic Extractor: No active research topics found")
            else:
                active_topics_section = ""
                logger.debug("🔍 Topic Extractor: No existing topics found for user")
        except Exception as e:
            logger.warning(f"🔍 Topic Extractor: Error retrieving active research topics: {str(e)}")
            active_topics_section = ""
    else:
        active_topics_section = ""
        logger.debug("🔍 Topic Extractor: No user_id available for active topics lookup")
    
    # Create system message with formatted prompt including active topics and memory context
    memory_context = state.get("memory_context")
    memory_context_section = ""
    if memory_context:
        # Limit memory context to avoid overwhelming the prompt
        memory_preview = memory_context[:1000] + "..." if len(memory_context) > 1000 else memory_context
        memory_context_section = f"CONVERSATION MEMORY (for context only):\n{memory_preview}\n\nUse this to understand the user's interests and conversation style, but focus on the current question."
        logger.debug("🔍 Topic Extractor: Including limited memory context")
    else:
        logger.debug("🔍 Topic Extractor: No memory context available")
    
    # Create the full system prompt
    full_prompt = TOPIC_EXTRACTOR_SYSTEM_PROMPT.format(
        current_time=current_time_str,
        existing_topics_section=active_topics_section,
        min_confidence=min_confidence,
        max_suggestions=max_suggestions
    )
    
    # Add memory context section if available
    if memory_context_section:
        full_prompt = full_prompt + "\n\n" + memory_context_section
    
    system_message_content = full_prompt
    
    # Initialize the model for topic extraction
    llm = ChatOpenAI(
        model=topic_model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=config.OPENAI_API_KEY
    )
    
    # Create structured output model
    structured_extractor = llm.with_structured_output(TopicSuggestions)
    
    # Prepare messages for the LLM - DO NOT include memory context to avoid confusion
    # Topic extraction should focus ONLY on the current conversation content
    messages_for_llm = [SystemMessage(content=system_message_content)]
    
    # Only include the current conversation messages (not memory context)
    # This ensures topic extraction focuses on what's actually being discussed now
    current_messages = state.get("messages", [])
    messages_for_llm.extend(current_messages)
    
    try:
        logger.debug(f"Sending {len(messages_for_llm)} messages to Topic Extractor")
        
        # Log the current conversation content for debugging
        recent_messages = []
        for msg in messages[-3:]:  # Last 3 messages
            if hasattr(msg, 'content'):
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                recent_messages.append(f"{msg.__class__.__name__}: {content}")
        logger.debug(f"🔍 Topic Extractor: Recent conversation context: {'; '.join(recent_messages)}")
        
        # Log the system prompt being used (first 500 chars)
        system_prompt = messages_for_llm[0].content
        logger.info(f"🔍 Topic Extractor: System prompt preview: {system_prompt[:500]}...")
        
        # Log if memory context was included in the prompt
        if "CONVERSATION MEMORY" in system_prompt:
            logger.info("🔍 Topic Extractor: Memory context INCLUDED in system prompt")
        else:
            logger.info("🔍 Topic Extractor: Memory context NOT included in system prompt")
        
        # Log all messages being sent to the LLM
        for i, msg in enumerate(messages_for_llm):
            msg_content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            logger.debug(f"🔍 Topic Extractor: Message {i} ({msg.__class__.__name__}): {msg_content}")
        
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