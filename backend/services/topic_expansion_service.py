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
        self.metrics: Dict[str, int] = {
            "expansion_candidates_total": 0,
            "expansion_llm_accepted": 0,
            "expansion_llm_rejected": 0,
            "expansion_fallbacks": 0,
        }

    async def generate_candidates(self, user_id: str, root_topic: Dict[str, Any]) -> List[ExpansionCandidate]:
        """Generate topic expansion candidates using Zep graph search with optional LLM selection and validation."""
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

        # Early check: if Zep is disabled, no expansions can be generated
        if not self.zep or not self.zep.is_enabled():
            logger.info(f"🔎 Expansion skipped for '{topic_name}': Zep is disabled (required for candidate generation and validation)")
            return []

        # Concurrent Zep searches
        reranker = config.ZEP_SEARCH_RERANKER
        limit = config.ZEP_SEARCH_LIMIT

        nodes_task = self.zep.search_graph(user_id, query, scope="nodes", reranker=reranker, limit=limit)
        edges_task = self.zep.search_graph(user_id, query, scope="edges", reranker=reranker, limit=limit)

        nodes_res, edges_res = await asyncio.gather(nodes_task, edges_task)
        self.metrics["expansion_candidates_total"] += (len(nodes_res) + len(edges_res))

        logger.debug(
            f"Zep search returned {len(nodes_res)} nodes and {len(edges_res)} edges for expansion"
        )

        # Convert Zep results to candidate objects
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

        def _rank_zep_candidates() -> List[ExpansionCandidate]:
            """Process Zep results: deduplicate, filter by similarity, and rank by relevance."""
            base = zep_to_candidates(nodes_res, edges_res)
            filtered_local = self._filter_and_dedupe_candidates(base, existing_norms, norm_name)

            logger.info(
                f"🧩 Generated {len(filtered_local)} expansion candidates from Zep (query='{query}')"
            )
            return filtered_local

        # If LLM disabled, use Zep-only ranking
        if not config.EXPANSION_LLM_ENABLED:
            return _rank_zep_candidates()

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
                suggestion_limit=config.EXPANSION_LLM_SUGGESTION_LIMIT,
            )

            llm = ChatOpenAI(
                model=config.EXPANSION_LLM_MODEL,
                temperature=config.EXPANSION_LLM_TEMPERATURE,
                max_tokens=config.EXPANSION_LLM_MAX_TOKENS,
                api_key=config.OPENAI_API_KEY,
            )
            structured = llm.with_structured_output(ExpansionSelection)
            messages = [SystemMessage(content=prompt)]
            # Run the single call with a timeout to avoid blocking
            llm_timeout = config.EXPANSION_LLM_TIMEOUT_SECONDS
            selection: ExpansionSelection = await asyncio.wait_for(
                asyncio.to_thread(structured.invoke, messages),
                timeout=llm_timeout,
            )

            accepted = selection.accepted or []
            rejected = selection.rejected or []
            self.metrics["expansion_llm_accepted"] += len(accepted)
            self.metrics["expansion_llm_rejected"] += len(rejected)
            if rejected:
                logger.debug(
                    "LLM rejected items: "
                    + ", ".join([f"{r.name}: {r.reason}" for r in rejected if r and getattr(r, "name", None)])
                )

            # Validate and consolidate LLM suggestions with Zep data
            final = await self._process_llm_suggestions(user_id, accepted, existing_norms, norm_name)

            # Enforce suggestion limit
            limit_out = config.EXPANSION_LLM_SUGGESTION_LIMIT
            if len(final) > limit_out:
                final = final[:limit_out]

            # Fallback to Zep-only ranking if LLM returned nothing usable
            if not final:
                logger.warning("Expansion LLM returned no usable items; falling back to Zep-only ranking.")
                self.metrics["expansion_fallbacks"] += 1
                return _rank_zep_candidates()

            # Sort candidates by relevance
            final = self._sort_candidates(final)
            logger.info(
                f"🧩 Expansion LLM accepted={len(final)} (from nodes={len(nodes_ctx)} edges={len(edges_ctx)}); returning ranked list"
            )
            return final

        except Exception as e:
            logger.warning(f"Expansion LLM failed or invalid JSON; fallback to Zep-only ranking. Error: {str(e)}")
            self.metrics["expansion_fallbacks"] += 1
            return _rank_zep_candidates()

    async def _process_llm_suggestions(self, user_id: str, accepted: List[Any], existing_norms: set, norm_name) -> List[ExpansionCandidate]:
        """Process and validate LLM suggestions against Zep data."""
        final: List[ExpansionCandidate] = []
        seen_final: set = set()
        min_sim = config.EXPANSION_MIN_SIMILARITY

        async def validate_with_zep(name: str) -> Optional[float]:
            """Validate LLM suggestion via Zep search to get similarity score."""
            try:
                res = await self.zep.search_graph(user_id, name, scope="nodes", reranker=config.ZEP_SEARCH_RERANKER, limit=3)
                if not res:
                    return None
                best = max([r for r in res if r.get("similarity") is not None], key=lambda x: x.get("similarity"), default=None)
                return best.get("similarity") if best else None
            except Exception as e:
                logger.debug(f"Zep validation error for '{name}': {str(e)}")
                return None

        for item in accepted:
            try:
                name = item.name.strip()
            except Exception:
                continue
                
            key = norm_name(name)
            if key in seen_final or key in existing_norms:
                continue

            source = (item.source or "llm").lower()
            similarity = getattr(item, "similarity_if_available", None)
            
            # Validate LLM-only suggestions via Zep
            if source == "llm":
                similarity = await validate_with_zep(name)
                if similarity is None or similarity < min_sim:
                    continue
            elif similarity is not None and similarity < min_sim:
                # Zep-derived item below threshold
                continue

            seen_final.add(key)
            validated_source = source if source in ("zep_node", "zep_edge", "llm") else "llm"
            rationale = getattr(item, "rationale", None)
            
            final.append(ExpansionCandidate(
                name=name, 
                source=validated_source, 
                similarity=similarity, 
                rationale=rationale
            ))

        return self._sort_candidates(final)
    
    def _filter_and_dedupe_candidates(self, candidates: List[ExpansionCandidate], existing_norms: set, norm_name) -> List[ExpansionCandidate]:
        """Deduplicate and filter candidates by similarity threshold."""
        seen: set = set()
        deduped: List[ExpansionCandidate] = []
        
        for candidate in candidates:
            key = norm_name(candidate.name)
            if key in seen or key in existing_norms:
                continue
            seen.add(key)
            deduped.append(candidate)

        # Filter by similarity threshold
        min_sim = config.EXPANSION_MIN_SIMILARITY
        filtered = [c for c in deduped if c.similarity is None or c.similarity >= min_sim]
        
        return self._sort_candidates(filtered)
    
    def _sort_candidates(self, candidates: List[ExpansionCandidate]) -> List[ExpansionCandidate]:
        """Sort candidates by similarity (desc), source preference (Zep before LLM), then name."""
        def sort_key(c: ExpansionCandidate):
            sim_key = c.similarity if c.similarity is not None else -1.0
            src_pref = 2 if c.source.startswith("zep_") else 1
            return (sim_key, src_pref, c.name)

        candidates.sort(key=sort_key, reverse=True)
        return candidates
