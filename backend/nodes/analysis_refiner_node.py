"""
Analysis refiner node for transforming user requests into structured analysis tasks.
"""

from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ChatOpenAI,
    AnalysisTask,
    ANALYSIS_REFINER_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
)
from utils import get_last_user_message


def analysis_task_refiner_node(state: ChatState) -> ChatState:
    """Refines the user's request into a detailed task for the analysis engine, considering conversation context."""
    logger.info("🧩 Analysis Refiner: Refining user request into analysis task")
    queue_status(state.get("session_id"), "Refining analysis task...")
    logger.debug("Analysis Task Refiner node refining task with context")
    current_time_str = get_current_datetime_str()
    raw_messages = state.get("messages", [])
    last_user_message_content = get_last_user_message(raw_messages)

    if not last_user_message_content:
        logger.warning("No user message found in analysis_task_refiner_node. Cannot refine.")
        state["workflow_context"]["refined_analysis_task"] = ""
        return state

    # Log the user message being refined
    display_msg = (
        last_user_message_content[:75] + "..." if len(last_user_message_content) > 75 else last_user_message_content
    )
    logger.info(f'🧩 Analysis Refiner: Refining task: "{display_msg}"')

    # Create system message with analysis refiner instructions
    memory_context = state.get("memory_context")
    memory_context_section = ""
    if memory_context:
        memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
        logger.debug("🧩 Analysis Refiner: Including memory context in task refinement")
    else:
        logger.debug("🧩 Analysis Refiner: No memory context available")

    system_message = SystemMessage(
        content=ANALYSIS_REFINER_SYSTEM_PROMPT.format(
            current_time=current_time_str, memory_context_section=memory_context_section
        )
    )

    # Use the messages directly (they are already langchain core message types)
    history_messages = state.get("messages", [])

    # Build the complete message list for the refiner
    context_messages_for_llm = [system_message] + history_messages

    if not history_messages:
        logger.warning("No messages in context for analysis_task_refiner. Using raw last user message.")
        state["workflow_context"]["refined_analysis_task"] = last_user_message_content
        return state

    # Initialize the optimizer LLM
    optimizer_llm = ChatOpenAI(
        model=config.ROUTER_MODEL, temperature=0.0, max_tokens=300, api_key=config.OPENAI_API_KEY
    )

    # Create structured output model
    structured_refiner = optimizer_llm.with_structured_output(AnalysisTask)

    try:
        # Invoke the structured refiner
        analysis_task = structured_refiner.invoke(context_messages_for_llm)

        # Combine the structured fields into a comprehensive task description
        refined_task = f"""ANALYSIS OBJECTIVE: {analysis_task.objective}
        
REQUIRED DATA: {analysis_task.required_data}

PROPOSED APPROACH: {analysis_task.proposed_approach}

EXPECTED OUTPUT: {analysis_task.expected_output}
        """

        # Log the refined task
        display_refined = refined_task[:75] + "..." if len(refined_task) > 75 else refined_task
        logger.info(f'🧩 Analysis Refiner: Produced refined task: "{display_refined}"')

        # Store both the formatted task and the structured object
        state["workflow_context"]["refined_analysis_task"] = refined_task
        state["workflow_context"]["analysis_task_structure"] = {
            "objective": analysis_task.objective,
            "required_data": analysis_task.required_data,
            "proposed_approach": analysis_task.proposed_approach,
            "expected_output": analysis_task.expected_output,
        }
        logger.info(f"Refined analysis task with context: {refined_task}")

    except Exception as e:
        logger.error(
            f"Error in analysis_task_refiner_node (with context): {str(e)}. Using original request as fallback."
        )
        state["workflow_context"]["refined_analysis_task"] = last_user_message_content

    return state
