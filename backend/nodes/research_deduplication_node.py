"""
Research deduplication node for checking if findings are duplicates of existing research.
"""
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from nodes.base import (
    ChatState, 
    logger, 
    config,
    user_manager,
    get_current_datetime_str,
    ResearchDeduplicationResult
)
from prompts import RESEARCH_FINDINGS_DEDUPLICATION_PROMPT


def research_deduplication_node(state: ChatState) -> ChatState:
    """Check if research findings are duplicates of existing findings."""
    logger.info("🔄 Research Deduplication: Checking for duplicate findings")
    
    # Get quality assessment results
    quality_results = state.get("module_results", {}).get("research_quality_assessor", {})
    
    if not quality_results.get("success", False):
        logger.error("🔄 Research Deduplication: No quality assessment results available")
        state["module_results"]["research_deduplication"] = {
            "success": False,
            "error": "No quality assessment results available",
            "is_duplicate": False
        }
        return state
    
    # Get search results and research metadata
    search_results = state.get("module_results", {}).get("search", {})
    research_metadata = state.get("workflow_context", {}).get("research_metadata", {})
    topic_name = research_metadata.get("topic_name", "Unknown Topic")
    user_id = research_metadata.get("user_id", "unknown")
    
    if not search_results.get("success", False):
        logger.error("🔄 Research Deduplication: No search results available")
        state["module_results"]["research_deduplication"] = {
            "success": False,
            "error": "No search results available",
            "is_duplicate": False
        }
        return state
    
    new_findings = search_results.get("result", "")
    
    try:
        # Get existing research findings for this topic and user
        existing_findings = user_manager.get_research_findings(user_id, topic_name)
        
        if not existing_findings or topic_name not in existing_findings:
            logger.info(f"🔄 Research Deduplication: No existing findings for topic '{topic_name}' - not a duplicate")
            state["module_results"]["research_deduplication"] = {
                "success": True,
                "is_duplicate": False,
                "reason": "No existing findings for comparison",
                "topic_name": topic_name
            }
            return state
        
        topic_findings = existing_findings[topic_name]
        
        if not topic_findings:
            logger.info(f"🔄 Research Deduplication: Empty existing findings for topic '{topic_name}' - not a duplicate")
            state["module_results"]["research_deduplication"] = {
                "success": True,
                "is_duplicate": False,
                "reason": "Empty existing findings list",
                "topic_name": topic_name
            }
            return state
        
        # Get recent findings for comparison (last 3)
        recent_findings = sorted(
            topic_findings, 
            key=lambda x: x.get("research_time", 0), 
            reverse=True
        )[:3]
        
        # Prepare existing findings text for comparison
        existing_text = "\n\n".join([
            f"Finding {i+1}:\n{finding.get('findings_summary', finding.get('findings_content', ''))}"
            for i, finding in enumerate(recent_findings)
        ])
        
        logger.info(f"🔄 Research Deduplication: Comparing against {len(recent_findings)} recent findings")
        
        # Create deduplication prompt
        prompt = RESEARCH_FINDINGS_DEDUPLICATION_PROMPT.format(
            current_time=get_current_datetime_str(),
            existing_findings=existing_text[:1500],  # Limit length
            new_findings=new_findings[:1500]  # Limit length
        )
        
        # Initialize the LLM for deduplication check with structured output
        llm = ChatOpenAI(
            model=config.RESEARCH_MODEL,
            temperature=0.1,  # Low temperature for consistent assessment
            max_tokens=300,
            api_key=config.OPENAI_API_KEY
        )
        
        # Create structured output model
        structured_llm = llm.with_structured_output(ResearchDeduplicationResult)
        
        # Get deduplication assessment
        messages = [SystemMessage(content=prompt)]
        dedup_result = structured_llm.invoke(messages)
        
        is_duplicate = dedup_result.is_duplicate
        similarity_score = dedup_result.similarity_score
        
        logger.info(f"🔄 Research Deduplication: Analysis complete - Duplicate: {is_duplicate}, Similarity: {similarity_score:.2f}")
        
        # Store the deduplication results
        state["module_results"]["research_deduplication"] = {
            "success": True,
            "is_duplicate": is_duplicate,
            "similarity_score": similarity_score,
            "unique_aspects": dedup_result.unique_aspects,
            "recommendation": dedup_result.recommendation,
            "topic_name": topic_name,
            "compared_against": len(recent_findings)
        }
        
    except Exception as e:
        error_message = f"Error in deduplication check: {str(e)}"
        logger.error(f"🔄 Research Deduplication: {error_message}")
        
        # Default to not duplicate on error with a fallback result
        fallback_result = ResearchDeduplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            unique_aspects=["Error occurred during comparison"],
            recommendation="keep"
        )
        
        state["module_results"]["research_deduplication"] = {
            "success": False,
            "error": error_message,
            "is_duplicate": False,  # Default to keeping findings if error occurs
            "fallback_reason": "Error occurred - defaulting to not duplicate",
            "fallback_result": fallback_result.model_dump()
        }
    
    return state 