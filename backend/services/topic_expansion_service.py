import asyncio
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.logging_config import get_logger
import config
from storage.zep_manager import ZepManager
from storage.research_manager import ResearchManager

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
        """Generate topic expansion candidates using Zep graph search.

        Phase 1 (debug): no persistence.
        """
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

        candidates: List[ExpansionCandidate] = []

        # Transform nodes
        for n in nodes_res:
            name = n.get("name") or (n.get("labels", [])[:1] or [None])[0]
            if not name:
                continue
            candidates.append(
                ExpansionCandidate(
                    name=name,
                    source="zep_node",
                    similarity=n.get("similarity"),
                    rationale="related KG node",
                )
            )

        # Transform edges
        for e in edges_res:
            name = e.get("fact") or e.get("name")
            if not name:
                continue
            candidates.append(
                ExpansionCandidate(
                    name=name,
                    source="zep_edge",
                    similarity=e.get("similarity"),
                    rationale="related KG fact",
                )
            )

        # Dedupe against self and existing topics
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

        seen: set = set()
        deduped: List[ExpansionCandidate] = []
        for c in candidates:
            key = norm_name(c.name)
            if key in seen or key in existing_norms:
                continue
            seen.add(key)
            deduped.append(c)

        # Filter by similarity threshold when present
        min_sim = config.EXPANSION_MIN_SIMILARITY
        filtered: List[ExpansionCandidate] = []
        for c in deduped:
            if c.similarity is not None and c.similarity < min_sim:
                continue
            filtered.append(c)

        # Sort: similarity desc, None last; tie-break by source preference nodes > edges
        def sort_key(c: ExpansionCandidate):
            sim_key = c.similarity if c.similarity is not None else -1.0
            src_pref = 1 if c.source == "zep_node" else 0
            return (sim_key, src_pref)

        filtered.sort(key=sort_key, reverse=True)

        logger.info(
            f"🧩 Generated {len(filtered)} expansion candidates from Zep (query='{query}')"
        )
        return filtered

