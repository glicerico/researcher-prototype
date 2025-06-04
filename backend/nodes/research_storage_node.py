"""
Research storage node for storing qualified research findings and updating topic metadata.
"""
import time
from typing import Dict, Any
from nodes.base import (
    ChatState, 
    logger, 
    config,
    user_manager
)


def research_storage_node(state: ChatState) -> ChatState:
    """Store research findings if they meet quality criteria and are not duplicates."""
    logger.info("💾 Research Storage: Processing research findings for storage")
    
    # Get results from previous nodes
    search_results = state.get("module_results", {}).get("search", {})
    quality_results = state.get("module_results", {}).get("research_quality_assessor", {})
    dedup_results = state.get("module_results", {}).get("research_deduplication", {})
    research_metadata = state.get("workflow_context", {}).get("research_metadata", {})
    
    # Extract key information
    topic_name = research_metadata.get("topic_name", "Unknown Topic")
    user_id = research_metadata.get("user_id", "unknown")
    research_query = state.get("workflow_context", {}).get("refined_search_query", "")
    
    # Check if we have all required results
    if not search_results.get("success", False):
        logger.error("💾 Research Storage: No successful search results available")
        state["module_results"]["research_storage"] = {
            "success": False,
            "error": "No successful search results available",
            "stored": False
        }
        return state
    
    if not quality_results.get("success", False):
        logger.error("💾 Research Storage: No successful quality assessment available")
        state["module_results"]["research_storage"] = {
            "success": False,
            "error": "No successful quality assessment available",
            "stored": False
        }
        return state
    
    # Get quality score and assessment details
    quality_assessment = quality_results.get("quality_assessment", {})
    overall_quality_score = quality_results.get("overall_quality_score", 0.0)
    
    # Check if quality meets threshold
    quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
    
    if overall_quality_score < quality_threshold:
        logger.info(f"💾 Research Storage: Quality score {overall_quality_score:.2f} below threshold {quality_threshold} - not storing")
        
        # Still update last researched time to avoid immediate retry
        user_manager.update_topic_last_researched(user_id, topic_name)
        
        state["module_results"]["research_storage"] = {
            "success": True,
            "stored": False,
            "reason": "Quality below threshold",
            "quality_score": overall_quality_score,
            "quality_threshold": quality_threshold,
            "topic_updated": True
        }
        return state
    
    # Check for duplicates
    is_duplicate = dedup_results.get("is_duplicate", False)
    
    if is_duplicate:
        logger.info(f"💾 Research Storage: Findings are duplicate - not storing")
        
        # Still update last researched time
        user_manager.update_topic_last_researched(user_id, topic_name)
        
        state["module_results"]["research_storage"] = {
            "success": True,
            "stored": False,
            "reason": "Duplicate findings",
            "similarity_score": dedup_results.get("similarity_score", 0.0),
            "topic_updated": True
        }
        return state
    
    # Prepare finding data for storage
    research_content = search_results.get("result", "")
    current_time = time.time()
    
    finding = {
        "findings_content": research_content,
        "research_time": current_time,
        "quality_score": overall_quality_score,
        "source_urls": quality_assessment.get("source_urls", []),
        "research_query": research_query,
        "key_insights": quality_assessment.get("key_insights", []),
        "findings_summary": quality_assessment.get("findings_summary", "")
    }
    
    try:
        # Store the research finding
        logger.info(f"💾 Research Storage: Storing high-quality finding for topic '{topic_name}' (score: {overall_quality_score:.2f})")
        
        success = user_manager.store_research_finding(user_id, topic_name, finding)
        
        if success:
            # Update last researched time
            user_manager.update_topic_last_researched(user_id, topic_name, current_time)
            
            logger.info(f"💾 Research Storage: Successfully stored research finding for '{topic_name}'")
            
            state["module_results"]["research_storage"] = {
                "success": True,
                "stored": True,
                "finding_id": f"{user_id}_{topic_name}_{int(current_time)}",
                "quality_score": overall_quality_score,
                "insights_count": len(quality_assessment.get("key_insights", [])),
                "content_length": len(research_content),
                "topic_updated": True
            }
            
        else:
            logger.error(f"💾 Research Storage: Failed to store research finding for '{topic_name}'")
            
            state["module_results"]["research_storage"] = {
                "success": False,
                "error": "Failed to store research finding in user profile",
                "stored": False,
                "quality_score": overall_quality_score
            }
            
    except Exception as e:
        error_message = f"Error storing research finding: {str(e)}"
        logger.error(f"💾 Research Storage: {error_message}")
        
        state["module_results"]["research_storage"] = {
            "success": False,
            "error": error_message,
            "stored": False,
            "quality_score": overall_quality_score
        }
    
    return state 