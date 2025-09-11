import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from services.logging_config import get_logger
import config
from storage.zep_manager import ZepManager
from storage.research_manager import ResearchManager
from prompts import ADJACENT_TOPIC_SELECTOR_PROMPT
from llm_models import ExpansionSelection

logger = get_logger(__name__)


@dataclass
class ExpansionCandidate:
    name: str
    source: str  # 'zep_node' | 'zep_edge'
    similarity: Optional[float] = None
    rationale: Optional[str] = None  # e.g., 'related KG node' | 'related KG fact'


class TopicExpansionService:
    def __init__(self, zep_manager: ZepManager, research_manager: ResearchManager) -> None:
        self.zep = zep_manager
        self.research = research_manager

    async def generate_candidates(self, user_id: str, root_topic: Dict[str, Any]) -> List[ExpansionCandidate]:
        """Generate topic expansion candidates using Zep graph search (+ optional LLM selection)."""
        # Build short query
        topic_name = (root_topic.get("topic_name") or "").strip()
        description = (root_topic.get("description") or "").strip()

        base = topic_name
        if description:
            # Append a compact descriptor; keep total <= 120 chars
            extra = f" — {description}"
            combined = (base + extra)[:120]
        else:
            combined = base[:120]

        query = combined.strip()
        if not query:
            logger.debug("Empty root topic; no expansion candidates generated")
            return []

        logger.info(f"🔎 Expansion query for user {user_id}: '{query}'")

        # Concurrent Zep searches
        reranker = config.ZEP_SEARCH_RERANKER
        limit = config.ZEP_SEARCH_LIMIT

        nodes_task = self.zep.search_graph(user_id, query, scope="nodes", reranker=reranker, limit=limit)
        edges_task = self.zep.search_graph(user_id, query, scope="edges", reranker=reranker, limit=limit)

        nodes_res, edges_res = await asyncio.gather(nodes_task, edges_task)

        logger.debug(
            f"Zep search returned {len(nodes_res)} nodes and {len(edges_res)} edges for expansion"
        )

        # Phase 1 normalization (used for fallback too)
        def zep_to_candidates(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[ExpansionCandidate]:
            out: List[ExpansionCandidate] = []
            for n in nodes:
                nm = n.get("name") or (n.get("labels", [])[:1] or [None])[0]
                if not nm:
                    continue
                out.append(
                    ExpansionCandidate(
                        name=nm,
                        source="zep_node",
                        similarity=n.get("similarity"),
                        rationale="related KG node",
                    )
                )
            for e in edges:
                nm = e.get("fact") or e.get("name")
                if not nm:
                    continue
                out.append(
                    ExpansionCandidate(
                        name=nm,
                        source="zep_edge",
                        similarity=e.get("similarity"),
                        rationale="related KG fact",
                    )
                )
            return out

        candidates: List[ExpansionCandidate] = []

        # Dedupe helpers
        def norm_name(s: str) -> str:
            s2 = s.casefold()
            s2 = re.sub(r"[\s\-_:,.;/\\]+", "", s2)
            s2 = re.sub(r"[\(\)\[\]\{\}\'\"]", "", s2)
            return s2

        # Gather existing topic names (prefer all topics; fallback to active topics)
        try:
            topics_data = self.research.get_user_topics(user_id)
            existing_names: List[str] = []
            for session_topics in topics_data.get("sessions", {}).values():
                for t in session_topics:
                    n = t.get("topic_name")
                    if n:
                        existing_names.append(n)
        except Exception:
            actives = self.research.get_active_research_topics(user_id)
            existing_names = [t.get("topic_name") for t in actives if t.get("topic_name")]

        existing_norms = {norm_name(n) for n in existing_names}

        # Pre-LLM compact context
        top_k = min(10, len(nodes_res))
        nodes_ctx = [
            {"name": n.get("name"), "labels": n.get("labels", []), "similarity": n.get("similarity")}
            for n in nodes_res[:top_k]
            if n.get("name")
        ]
        edges_ctx = [
            {"name": (e.get("fact") or e.get("name")), "similarity": e.get("similarity")}
            for e in edges_res[:top_k]
            if (e.get("fact") or e.get("name"))
        ]

        def phase1_flow() -> List[ExpansionCandidate]:
            base = zep_to_candidates(nodes_res, edges_res)
            seen_local: set = set()
            deduped_local: List[ExpansionCandidate] = []
            for c in base:
                key = norm_name(c.name)
                if key in seen_local or key in existing_norms:
                    continue
                seen_local.add(key)
                deduped_local.append(c)

            min_sim = config.EXPANSION_MIN_SIMILARITY
            filtered_local: List[ExpansionCandidate] = []
            for c in deduped_local:
                if c.similarity is not None and c.similarity < min_sim:
                    continue
                filtered_local.append(c)

            def sort_key(c: ExpansionCandidate):
                sim_key = c.similarity if c.similarity is not None else -1.0
                src_pref = 2 if c.source == "zep_node" else 1  # nodes before edges
                return (sim_key, src_pref, c.name)

            filtered_local.sort(key=sort_key, reverse=True)

            logger.info(
                f"🧩 Generated {len(filtered_local)} expansion candidates from Zep (query='{query}')"
            )
            return filtered_local

        # If LLM disabled, return Phase 1 behavior
        if not getattr(config, "EXPANSION_LLM_ENABLED", True):
            return phase1_flow()

        # Build LLM prompt
        try:
            current_time = ""  # keep concise
            prompt = ADJACENT_TOPIC_SELECTOR_PROMPT.format(
                current_time=current_time,
                root_topic_name=topic_name,
                root_topic_description=description[:120] if description else "",
                current_topics=json.dumps(sorted(list(set(existing_names)))[:20], ensure_ascii=False),
                zep_nodes=json.dumps(nodes_ctx, ensure_ascii=False),
                zep_edges=json.dumps(edges_ctx, ensure_ascii=False),
                suggestion_limit=int(getattr(config, "EXPANSION_LLM_SUGGESTION_LIMIT", 6)),
            )

            llm = ChatOpenAI(
                model=getattr(config, "EXPANSION_LLM_MODEL", config.DEFAULT_MODEL),
                temperature=float(getattr(config, "EXPANSION_LLM_TEMPERATURE", 0.2)),
                max_tokens=int(getattr(config, "EXPANSION_LLM_MAX_TOKENS", 800)),
                api_key=getattr(config, "OPENAI_API_KEY", None),
            )
            structured = llm.with_structured_output(ExpansionSelection)
            messages = [SystemMessage(content=prompt)]
            selection: ExpansionSelection = structured.invoke(messages)

            accepted = selection.accepted or []
            rejected = selection.rejected or []
            if rejected:
                logger.debug(
                    "LLM rejected items: "
                    + ", ".join([f"{r.name}: {r.reason}" for r in rejected if r and getattr(r, "name", None)])
                )

            final: List[ExpansionCandidate] = []
            min_sim = config.EXPANSION_MIN_SIMILARITY
            seen_final: set = set()

            async def validate_llm_item(name: str) -> Optional[float]:
                # Validate via Zep (nodes preferred); take best similarity if any
                res = await self.zep.search_graph(user_id, name, scope="nodes", reranker=config.ZEP_SEARCH_RERANKER, limit=3)
                if not res:
                    return None
                best = max([r for r in res if r.get("similarity") is not None], key=lambda x: x.get("similarity"), default=None)
                return best.get("similarity") if best else None

            # Validate LLM-accepted items
            for item in accepted:
                try:
                    nm = item.name.strip()
                except Exception:
                    continue
                key = norm_name(nm)
                if key in seen_final or key in existing_norms:
                    continue
                src = (item.source or "llm").lower()
                sim = getattr(item, "similarity_if_available", None)
                if src == "llm":
                    try:
                        sim = await validate_llm_item(nm)
                    except Exception as e:
                        logger.debug(f"LLM-only validation error for '{nm}': {str(e)}")
                        sim = None
                    # Drop if no similarity or below threshold
                    if sim is None or (isinstance(sim, (int, float)) and sim < min_sim):
                        continue
                else:
                    # Zep-derived; if similarity provided and below threshold, drop
                    if sim is not None and sim < min_sim:
                        continue
                seen_final.add(key)
                final.append(
                    ExpansionCandidate(name=nm, source=src if src in ("zep_node", "zep_edge", "llm") else "llm", similarity=sim, rationale=getattr(item, "rationale", None))
                )

            # Fallback to Phase 1 if nothing accepted
            if not final:
                logger.warning("Expansion LLM returned no usable items; falling back to Zep-only.")
                return phase1_flow()

            # Sort as specified: similarity desc; Zep items before LLM; deterministic by name
            def sort_key(c: ExpansionCandidate):
                sim_key = c.similarity if c.similarity is not None else -1.0
                src_pref = 2 if c.source.startswith("zep_") else 1
                return (sim_key, src_pref, c.name)

            final.sort(key=sort_key, reverse=True)
            logger.info(
                f"🧩 Expansion LLM accepted={len(final)} (from nodes={len(nodes_ctx)} edges={len(edges_ctx)}); returning ranked list"
            )
            return final

        except Exception as e:
            logger.warning(f"Expansion LLM failed or invalid JSON; fallback to Zep-only. Error: {str(e)}")
            return phase1_flow()
