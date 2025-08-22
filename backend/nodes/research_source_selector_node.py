"""
Research source selector node for autonomous research workflow.
Determines which sources are most relevant for a research topic.
"""
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from nodes.base import ChatState, logger, config
from llm_models import MultiSourceAnalysis
from prompts import RESEARCH_SOURCE_SELECTION_PROMPT


async def research_source_selector_node(state: ChatState) -> ChatState:
    """
    Select appropriate sources for autonomous research based on topic characteristics.
    
    Unlike the chat multi-source analyzer, this focuses on research-specific source selection:
    - Academic sources for scientific/technical topics
    - Medical sources for health-related topics  
    - Web sources for current events/technology
    - Social sources for community/trend analysis
    """
    logger.info("🔬 Research Source Selector: Analyzing topic for source selection")
    
    # Get research metadata
    research_metadata = state.get("workflow_context", {}).get("research_metadata", {})
    topic_name = research_metadata.get("topic_name", "Unknown Topic")
    topic_description = research_metadata.get("topic_description", "")
    research_query = state.get("workflow_context", {}).get("refined_search_query", topic_name)
    
    logger.info(f"🔬 Research Source Selector: Selecting sources for '{topic_name}'")
    
    try:
        # Create the source selection prompt
        prompt = RESEARCH_SOURCE_SELECTION_PROMPT.format(
            topic_name=topic_name,
            topic_description=topic_description,
            research_query=research_query
        )
        
        # Initialize LLM for source selection
        llm = ChatOpenAI(
            model=config.CHAT_MODEL,
            temperature=0.1,
            max_tokens=300,
            api_key=config.OPENAI_API_KEY
        )
        
        # Get structured source selection
        messages = [SystemMessage(content=prompt)]
        structured_llm = llm.with_structured_output(MultiSourceAnalysis)
        analysis = structured_llm.invoke(messages)
        
        # Validate and process source selection
        valid_sources = ["search", "academic_search", "social_search", "medical_search"]
        selected_sources = []
        
        for source in analysis.sources:
            if source in valid_sources:
                selected_sources.append(source)
        
        # Ensure we have at least one source, prefer academic for research
        if not selected_sources:
            if "academic" in topic_name.lower() or "research" in topic_name.lower():
                selected_sources = ["academic_search", "search"]
            else:
                selected_sources = ["search", "academic_search"]
            logger.warning(f"🔬 Research Source Selector: No valid sources selected, using fallback: {selected_sources}")
        
        # Limit to maximum 3 sources for research efficiency
        selected_sources = selected_sources[:3]
        
        # Store results (both in workflow_context and top-level for downstream components)
        state["workflow_context"]["selected_sources"] = selected_sources
        state["selected_sources"] = selected_sources
        state["intent"] = "search"  # Research always uses search intent
        
        # Store source selection analysis
        state["workflow_context"]["source_selection_analysis"] = {
            "intent": analysis.intent,
            "sources": selected_sources,
            "reasoning": f"Research-focused source selection for {topic_name}"
        }
        
        state["module_results"]["research_source_selector"] = {
            "success": True,
            "selected_sources": selected_sources,
            "topic_name": topic_name
        }
        
        logger.info(f"🔬 Research Source Selector: ✅ Selected sources: {selected_sources}")
        
    except Exception as e:
        error_message = f"Error selecting research sources: {str(e)}"
        logger.error(f"🔬 Research Source Selector: ❌ {error_message}")
        
        # Fallback to balanced source selection
        fallback_sources = ["search", "academic_search"]
        state["workflow_context"]["selected_sources"] = fallback_sources
        state["intent"] = "search"
        
        state["module_results"]["research_source_selector"] = {
            "success": False,
            "error": error_message,
            "fallback_sources": fallback_sources
        }
        
        logger.info(f"🔬 Research Source Selector: Using fallback sources: {fallback_sources}")
    
    return state
