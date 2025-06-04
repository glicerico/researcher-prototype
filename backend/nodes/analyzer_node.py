"""
Analyzer node for processing complex analytical tasks.
"""
from nodes.base import (
    ChatState, 
    logger,
    HumanMessage
)
from utils import get_last_user_message


def analyzer_node(state: ChatState) -> ChatState:
    """Analyzer module that processes data-related queries."""
    logger.info("🧩 Analyzer: Processing analysis request")
    
    # Get analysis task (either refined or original)
    refined_task = state.get("workflow_context", {}).get("refined_analysis_task")
    original_user_query = get_last_user_message(state.get("messages", []))
    
    task_to_analyze = refined_task or original_user_query

    if not task_to_analyze:
        state["module_results"]["analyzer"] = {"success": False, "error": "No task found for analyzer."}
        return state
        
    # Log the task to analyze
    display_task = task_to_analyze[:75] + "..." if len(task_to_analyze) > 75 else task_to_analyze
    logger.info(f"🧩 Analyzer: Analyzing: \"{display_task}\"")

    logger.info(f"🧩 Analyzer node processing task (simulated): {task_to_analyze[:200]}...")
    
    analysis_response = f"Based on the task related to '{task_to_analyze}', I have performed a simulated analysis. [This is a simulated analysis response based on the (refined) task description]"
    
    # Log the analysis result
    display_result = analysis_response[:75] + "..." if len(analysis_response) > 75 else analysis_response
    logger.info(f"🧩 Analyzer: Analysis result: \"{display_result}\"")

    # Store the result
    state["module_results"]["analyzer"] = {
        "success": True, 
        "result": analysis_response, 
        "task_processed": task_to_analyze
    }
    
    return state 