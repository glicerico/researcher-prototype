"""
Search results reviewer node: filters source results by relevance before integration.
"""

from nodes.base import (
    ChatState,
    logger,
    SystemMessage,
    ChatOpenAI,
    config,
    get_current_datetime_str,
    queue_status,
)
from prompts import SEARCH_RESULTS_REVIEWER_PROMPT
from config import SEARCH_RESULTS_LIMIT


async def search_results_reviewer_node(state: ChatState) -> ChatState:
    """Review and filter each source's content for relevance to the query before integration."""
    logger.info("🧹 Results Reviewer: Filtering source outputs for relevance")
    queue_status(state.get("thread_id"), "Reviewing results for relevance...")

    current_time = get_current_datetime_str()
    llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.1,
        max_tokens=600,
        api_key=config.OPENAI_API_KEY,
    )

    # Determine the query for relevance judgement
    query = state.get("workflow_context", {}).get("refined_search_query") or ""
    if not query:
        # Fall back to last user message if available
        messages = state.get("messages", [])
        if messages:
            try:
                query = messages[-1].content
            except Exception:
                query = ""

    # Apply to known sources only
    source_names = {
        "search": "Web Search",
        "academic_search": "Academic Papers",
        "social_search": "Hacker News",
        "medical_search": "PubMed",
    }

    for key, source_human_name in source_names.items():
        module_data = state.get("module_results", {}).get(key)
        if not module_data or not module_data.get("success"):
            continue

        original_content = module_data.get("content", "").strip()
        if not original_content:
            continue

        # Build prompt and invoke LLM reviewer
        prompt = SEARCH_RESULTS_REVIEWER_PROMPT.format(
            current_time=current_time,
            source_name=source_human_name,
            query=query,
            original_content=original_content,
            max_items=SEARCH_RESULTS_LIMIT,
        )

        messages = [SystemMessage(content=prompt)]

        try:
            response = llm.invoke(messages)
            filtered = response.content.strip()

            if filtered and filtered.lower() != "no highly relevant items found.":
                # Replace content with filtered content, keep raw_results unchanged
                state["module_results"][key]["content"] = filtered
                state["module_results"][key]["filtered_by_reviewer"] = True
                logger.info(f"🧹 Results Reviewer: ✅ Filtered content for {source_human_name}")
            else:
                # Mark as empty/no relevant items; integrator will skip if no content
                state["module_results"][key]["content"] = ""
                state["module_results"][key]["filtered_by_reviewer"] = True
                state["module_results"][key]["no_relevant_items"] = True
                logger.info(f"🧹 Results Reviewer: ⚠️ No highly relevant items for {source_human_name}")
        except Exception as e:
            logger.error(f"🧹 Results Reviewer: Error reviewing {source_human_name}: {str(e)}")

    return state


