"""
Research quality assessor node for evaluating the quality of research findings.
"""
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from nodes.base import (
    ChatState, 
    logger, 
    config,
    get_current_datetime_str,
    ResearchQualityAssessment
)
from prompts import RESEARCH_FINDINGS_QUALITY_ASSESSMENT_PROMPT


def research_quality_assessor_node(state: ChatState) -> ChatState:
    """Assess the quality of research findings and provide scores."""
    logger.info("🎯 Research Quality Assessor: Evaluating research findings quality")
    
    # Get search results from previous nodes
    search_results = state.get("module_results", {}).get("search", {})
    
    if not search_results.get("success", False):
        logger.error("🎯 Research Quality Assessor: No successful search results to assess")
        state["module_results"]["research_quality_assessor"] = {
            "success": False,
            "error": "No search results available for quality assessment"
        }
        return state
    
    # Get research metadata and search details
    research_metadata = state.get("workflow_context", {}).get("research_metadata", {})
    topic_name = research_metadata.get("topic_name", "Unknown Topic")
    research_query = search_results.get("query_used", "")
    research_results_content = search_results.get("result", "")
    
    if not research_results_content:
        logger.error("🎯 Research Quality Assessor: Empty search results content")
        state["module_results"]["research_quality_assessor"] = {
            "success": False,
            "error": "Empty search results content"
        }
        return state
    
    logger.info(f"🎯 Research Quality Assessor: Assessing quality for topic '{topic_name}'")
    
    try:
        # Create the quality assessment prompt
        prompt = RESEARCH_FINDINGS_QUALITY_ASSESSMENT_PROMPT.format(
            current_time=get_current_datetime_str(),
            topic_name=topic_name,
            research_query=research_query,
            research_results=research_results_content[:2000]  # Limit length
        )
        
        # Initialize the LLM for quality assessment with structured output
        llm = ChatOpenAI(
            model=config.RESEARCH_MODEL,
            temperature=0.1,  # Low temperature for consistent assessment
            max_tokens=800,
            api_key=config.OPENAI_API_KEY
        )
        
        # Create structured output model
        structured_llm = llm.with_structured_output(ResearchQualityAssessment)
        
        # Get quality assessment
        messages = [SystemMessage(content=prompt)]
        assessment_result = structured_llm.invoke(messages)
        
        overall_quality = assessment_result.overall_quality_score
        logger.info(f"🎯 Research Quality Assessor: Quality assessment completed - Overall score: {overall_quality:.2f}")
        
        # Store the assessment results
        state["module_results"]["research_quality_assessor"] = {
            "success": True,
            "quality_assessment": assessment_result.model_dump(),
            "overall_quality_score": overall_quality,
            "topic_name": topic_name
        }
        
    except Exception as e:
        error_message = f"Error in quality assessment: {str(e)}"
        logger.error(f"🎯 Research Quality Assessor: {error_message}")
        
        # Provide a fallback assessment using the Pydantic model
        fallback_assessment = ResearchQualityAssessment(
            overall_quality_score=0.5,
            recency_score=0.5,
            relevance_score=0.5,
            depth_score=0.5,
            credibility_score=0.5,
            novelty_score=0.5,
            key_insights=["Unable to assess insights due to error"],
            source_urls=[],
            findings_summary="Quality assessment failed due to error"
        )
        
        state["module_results"]["research_quality_assessor"] = {
            "success": False,
            "error": error_message,
            "fallback_assessment": fallback_assessment.model_dump(),
            "overall_quality_score": 0.5
        }
    
    return state 