"""
Research query generator node for creating optimized research queries for autonomous research.
Phase 1: adds motivation-mediated explore vs. exploit and KG-based expansion using Zep.
"""
from datetime import datetime
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from nodes.base import (
    ChatState,
    logger,
    config,
    get_current_datetime_str,
    zep_manager,
)
from prompts import RESEARCH_QUERY_GENERATION_PROMPT




async def research_query_generator_node(state: ChatState) -> ChatState:
    """Generate an optimized research query based on topic metadata with optional KG expansion."""
    logger.info("🔍 Research Query Generator: Creating optimized research query")

    # Get research metadata
    wc = state.get("workflow_context", {})
    research_metadata = wc.get("research_metadata", {})
    topic_name = research_metadata.get("topic_name", "Unknown Topic")
    topic_description = research_metadata.get("topic_description", "")

    # Get research context from workflow_context
    research_context = wc.get("research_context", {})
    last_researched = research_context.get("last_researched")
    motivation_snapshot = research_context.get("motivation_snapshot", {})

    # Get expansion decision from motivation system
    research_metadata = wc.get("research_metadata", {})
    motivation_system = research_metadata.get("motivation_system")
    
    mode = "exploit"  # Default to exploit (stay on topic)
    
    if motivation_system and hasattr(motivation_system, 'should_expand_topic'):
        try:
            should_expand = motivation_system.should_expand_topic(topic_name)
            mode = "explore" if should_expand else "exploit"
            logger.info(f"🔍 Research Query Generator: Motivation system recommends {mode} for '{topic_name}'")
        except Exception as e:
            logger.warning(f"🔍 Research Query Generator: Could not check expansion from motivation system: {e}")
            mode = "exploit"
    else:
        logger.warning("🔍 Research Query Generator: Motivation system not available, defaulting to exploit mode")

    # Optionally fetch KG neighbors when exploring
    selected_neighbor = None
    kg_candidates = []
    if mode == "explore":
        try:
            user_id = research_context.get("user_id") or state.get("user_id")
            if user_id:
                kg_candidates = await zep_manager.get_related_topics(user_id, topic_name, limit=5)
            if kg_candidates:
                selected_neighbor = kg_candidates[0]
            else:
                mode = "exploit"  # fallback if no neighbors
        except Exception as e:
            logger.warning(f"🔍 Research Query Generator: KG neighbor lookup failed, falling back to exploit: {e}")
            mode = "exploit"

    # Format last research time
    if last_researched:
        last_research_time = datetime.fromtimestamp(last_researched).strftime("%Y-%m-%d")
    else:
        last_research_time = "Never"

    # Adjust topic description when exploring to direct the generator
    effective_topic_description = topic_description
    if mode == "explore" and selected_neighbor:
        rel = selected_neighbor.get("relation", "related_to")
        nbr = selected_neighbor.get("label", "(unknown)")
        effective_topic_description = (
            f"Explore a closely related topic discovered in the knowledge graph: '{nbr}' "
            f"(relation: {rel}) while maintaining relevance to the seed topic. "
            f"Focus on recent intersections and updates."
        )

    logger.info(
        f"🔍 Research Query Generator: Generating query for '{topic_name}' (mode: {mode}, last researched: {last_research_time})"
    )

    try:
        # Create the prompt for research query generation
        prompt = RESEARCH_QUERY_GENERATION_PROMPT.format(
            current_time=get_current_datetime_str(),
            topic_name=topic_name,
            topic_description=effective_topic_description,
            last_research_time=last_research_time,
        )

        # Initialize the LLM for query generation
        llm = ChatOpenAI(
            model=config.RESEARCH_MODEL,
            temperature=0.3,
            max_tokens=150,
            api_key=config.OPENAI_API_KEY,
        )

        # Generate the research query
        messages = [SystemMessage(content=prompt)]
        response = llm.invoke(messages)
        research_query = (response.content or "").strip()

        if not research_query:
            # Fallback to a simple query
            if mode == "explore" and selected_neighbor:
                research_query = (
                    f"Recent developments at the intersection of {topic_name} and {selected_neighbor.get('label', '')}"
                )
            else:
                research_query = f"Recent developments and new information about {topic_name}"
            logger.warning("🔍 Research Query Generator: Empty LLM response, using fallback query")

        # Store the generated query and decision in workflow context
        wc["refined_search_query"] = research_query
        wc["kg_candidates"] = kg_candidates
        rationale = {
            "mode": mode,
            "decision_source": "motivation_system_saturation" if motivation_system else "fallback",
            "selected_neighbor": selected_neighbor,
            "motivation": {
                "boredom": motivation_snapshot.get("boredom"),
                "curiosity": motivation_snapshot.get("curiosity"),
                "tiredness": motivation_snapshot.get("tiredness"),
                "satisfaction": motivation_snapshot.get("satisfaction"),
                "impetus": motivation_snapshot.get("impetus"),
            },
        }
        wc["expansion_decision"] = rationale
        state["workflow_context"] = wc

        # Update the synthetic messages with the generated query
        if state.get("messages") and len(state["messages"]) > 1:
            # Update the human message with the generated query
            state["messages"][-1].content = research_query

        logger.info(f"🔍 Research Query Generator: ✅ Generated query: '{research_query[:100]}...'")

        # Mark the query generation as successful with rationale
        state["module_results"]["research_query_generator"] = {
            "success": True,
            "query": research_query,
            "topic_name": topic_name,
            "expansion_decision": rationale,
        }

    except Exception as e:
        error_message = f"Error generating research query: {str(e)}"
        logger.error(f"🔍 Research Query Generator: ❌ {error_message}")

        # Fallback to a simple query
        fallback_query = f"Recent developments and new information about {topic_name}"
        state["workflow_context"]["refined_search_query"] = fallback_query

        # Update the synthetic messages with the fallback query
        if state.get("messages") and len(state["messages"]) > 1:
            state["messages"][-1].content = fallback_query

        state["module_results"]["research_query_generator"] = {
            "success": False,
            "error": error_message,
            "fallback_query": fallback_query,
        }

    return state
