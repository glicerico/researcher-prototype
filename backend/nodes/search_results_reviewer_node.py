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
from llm_models import RelevanceSelection


async def search_results_reviewer_node(state: ChatState) -> ChatState:
    """Review and filter each source's content for relevance to the query before integration."""
    logger.info("🧹 Results Reviewer: Filtering source outputs for relevance")
    logger.info("🧹 Results Reviewer: Skipping 'search' (Perplexity) - single comprehensive result with citations")
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

    # Apply to known sources only (skip "search" as Perplexity returns single comprehensive result)
    source_names = {
        "academic_search": "Academic Papers",
        "social_search": "Hacker News", 
        "medical_search": "PubMed",
    }

    for key, source_human_name in source_names.items():
        module_data = state.get("module_results", {}).get(key)
        if not module_data or not module_data.get("success"):
            continue

        original_content = module_data.get("content", "").strip()
        raw_results = module_data.get("raw_results", {})
        items = raw_results.get("results")

        # Skip processing if no results to review
        if items is None:
            if not original_content:
                logger.info(f"🧹 Results Reviewer: Skipping {source_human_name} - no content to review")
                continue
        elif len(items) == 0:
            logger.info(f"🧹 Results Reviewer: Skipping {source_human_name} - no results to review")
            continue
        
        # If we don't have structured items, fall back to content-based filtering
        if items is None:
            prompt = SEARCH_RESULTS_REVIEWER_PROMPT.format(
                current_time=current_time,
                source_name=source_human_name,
                query=query,
                enumerated_items=original_content,
                max_items=SEARCH_RESULTS_LIMIT,
            )
            messages = [SystemMessage(content=prompt)]
            try:
                # Fall back to text response (legacy). We keep prior behavior for safety.
                response = llm.invoke(messages)
                filtered = response.content.strip()
                if filtered and filtered.lower() != "no highly relevant items found.":
                    state["module_results"][key]["content"] = filtered
                    state["module_results"][key]["filtered_by_reviewer"] = True
                    logger.info(f"🧹 Results Reviewer: ✅ Filtered content for {source_human_name} (fallback mode)")
                else:
                    state["module_results"][key]["content"] = ""
                    state["module_results"][key]["filtered_by_reviewer"] = True
                    state["module_results"][key]["no_relevant_items"] = True
                    logger.info(f"🧹 Results Reviewer: ⚠️ No highly relevant items for {source_human_name} (fallback mode)")
            except Exception as e:
                logger.error(f"🧹 Results Reviewer: Error reviewing {source_human_name}: {str(e)}")
            continue

        # Build enumerated items view for structured selection
        enumerated = []
        for idx, item in enumerate(items):
            try:
                # Create concise line for the item
                title = item.get("title") or item.get("story_title") or item.get("paperTitle") or "(no title)"
                url = item.get("url") or item.get("story_url") or item.get("openAccessPdf", {}).get("url") or ""
                snippet = item.get("text") or item.get("abstract") or ""
                if snippet and len(snippet) > 500:
                    snippet = snippet[:500] + "..."
                parts = [f"[{idx}] {title}"]
                if snippet:
                    parts.append(f" - {snippet}")
                if url:
                    parts.append(f" ({url})")
                enumerated.append("".join(parts))
            except Exception:
                enumerated.append(f"[{idx}] (unreadable item)")

        enumerated_block = "\n".join(enumerated)

        prompt = SEARCH_RESULTS_REVIEWER_PROMPT.format(
            current_time=current_time,
            source_name=source_human_name,
            query=query,
            enumerated_items=enumerated_block,
            max_items=SEARCH_RESULTS_LIMIT,
        )

        messages = [SystemMessage(content=prompt)]

        try:
            structured = llm.with_structured_output(RelevanceSelection).invoke(messages)
            selected = structured.selected_indices or []

            # Keep only selected items; reformat content using existing formatter if available
            if selected:
                filtered_results = [items[i] for i in selected if 0 <= i < len(items)]
                raw_results["results"] = filtered_results
                # Mark and leave formatting to integrator (or existing content remains acceptable)
                state["module_results"][key]["raw_results"] = raw_results
                state["module_results"][key]["selected_indices"] = selected
                state["module_results"][key]["filtered_by_reviewer"] = True
                logger.info(f"🧹 Results Reviewer: ✅ Selected {len(filtered_results)} items for {source_human_name}")
                # If content exists from formatter, we can regenerate via formatter by signaling downstream if needed
                # For simplicity, leave content as-is; integrator uses 'content'.
            else:
                # Clear the raw_results when no items are selected
                raw_results["results"] = []
                state["module_results"][key]["raw_results"] = raw_results
                state["module_results"][key]["content"] = ""
                state["module_results"][key]["filtered_by_reviewer"] = True
                state["module_results"][key]["no_relevant_items"] = True
                logger.info(f"🧹 Results Reviewer: ⚠️ No items selected for {source_human_name}")
        except Exception as e:
            logger.error(f"🧹 Results Reviewer: Error obtaining structured selection for {source_human_name}: {str(e)}")

    return state


