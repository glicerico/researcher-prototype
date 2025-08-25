"""
Evidence summarizer node that converts reviewer-filtered items into concise summaries with citations.
"""

import asyncio
from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    SystemMessage,
    ChatOpenAI,
    config,
    get_current_datetime_str,
    queue_status,
)
from llm_models import EvidenceSummary
from prompts import EVIDENCE_SUMMARIZER_PROMPT
from utils import get_last_user_message


async def evidence_summarizer_node(state: ChatState) -> ChatState:
    """Convert reviewer-filtered items into concise summaries with proper citations."""
    logger.info("📝 Evidence Summarizer: Creating concise summaries from filtered results")
    queue_status(state.get("thread_id"), "Summarizing evidence...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible

    current_time = get_current_datetime_str()
    llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.1,
    )

    # Get user query for context
    messages = state.get("messages", [])
    query = ""
    if messages:
        try:
            query = get_last_user_message(messages)
        except Exception:
            try:
                query = messages[-1].content
            except Exception:
                query = ""

    # Process each source type that has reviewer-filtered results
    source_names = {
        "academic_search": "Academic Papers",
        "social_search": "Hacker News", 
        "medical_search": "PubMed",
    }

    for key, source_human_name in source_names.items():
        module_data = state.get("module_results", {}).get(key)
        if not module_data or not module_data.get("success"):
            continue

        raw_results = module_data.get("raw_results", {}) or {}
        filtered_items = raw_results.get("results", [])
        
        if not filtered_items or not module_data.get("filtered_by_reviewer"):
            continue

        logger.info(f"📝 Evidence Summarizer: Processing {len(filtered_items)} filtered items from {source_human_name}")

        # Build enumerated items for the LLM
        enumerated_items = []
        for idx, item in enumerate(filtered_items):
            try:
                title = (
                    item.get("title") 
                    or item.get("story_title") 
                    or item.get("paperTitle") 
                    or "(no title)"
                )
                url = (
                    item.get("url") 
                    or item.get("story_url") 
                    or (item.get("openAccessPdf", {}) or {}).get("url")
                    or ""
                )
                snippet = item.get("text") or item.get("abstract") or ""
                if snippet and len(snippet) > 300:
                    snippet = snippet[:300] + "..."
                
                parts = [f"[{idx}] {title}"]
                if snippet:
                    parts.append(f" - {snippet}")
                if url:
                    parts.append(f" (URL: {url})")
                enumerated_items.append("".join(parts))
            except Exception:
                enumerated_items.append(f"[{idx}] (unreadable item)")

        enumerated_block = "\n".join(enumerated_items)

        # Create the summarization prompt
        prompt = EVIDENCE_SUMMARIZER_PROMPT.format(
            current_time=current_time,
            source_name=source_human_name,
            query=query,
            source_name_upper=source_human_name.upper(),
            enumerated_items=enumerated_block,
        )

        messages = [SystemMessage(content=prompt)]

        try:
            structured = llm.with_structured_output(EvidenceSummary).invoke(messages)
            summary_text = structured.summary_text or ""
            
            if summary_text:
                # Store the summary in module results
                state["module_results"][key]["evidence_summary"] = summary_text
                logger.info(f"📝 Evidence Summarizer: ✅ Created summary for {source_human_name}")
            else:
                logger.info(f"📝 Evidence Summarizer: ⚠️ No summary generated for {source_human_name}")
                
        except Exception as e:
            logger.error(f"📝 Evidence Summarizer: Error summarizing {source_human_name}: {str(e)}")

    return state
