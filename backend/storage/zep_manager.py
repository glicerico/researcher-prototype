"""Zep Memory Manager using the v3 Python SDK."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import config
from logging_config import get_logger

logger = get_logger(__name__)

try:  # pragma: no cover - the SDK may not be installed in CI
    from zep_python.client import AsyncZepClient as ZepClient
except Exception:  # pragma: no cover
    try:
        from zep_python import AsyncZepClient as ZepClient  # type: ignore
    except Exception:
        ZepClient = None  # type: ignore


class ZepManager:
    """Simple wrapper around the Zep v3 client.

    The manager is implemented as a singleton to avoid multiple client
    instances being created.  All Zep operations are optional – when the
    service is disabled or the SDK isn't available the methods become no-ops
    and simply return ``False``/``None``.
    """

    _instance: "ZepManager" | None = None
    _initialized = False

    def __new__(cls) -> "ZepManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self.enabled = config.ZEP_ENABLED
        self.client = None

        if self.enabled and config.ZEP_API_KEY and ZepClient:
            try:
                base_url = getattr(config, "ZEP_API_URL", None)
                if base_url:
                    self.client = ZepClient(api_key=config.ZEP_API_KEY, base_url=base_url)
                else:
                    self.client = ZepClient(api_key=config.ZEP_API_KEY)
                logger.info("Zep client initialized successfully")
            except Exception as exc:  # pragma: no cover - network/SDK issues
                logger.error(f"Failed to initialize Zep client: {exc}")
                self.enabled = False
        else:
            logger.info("Zep is disabled or API key not provided")

        self._initialized = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def is_enabled(self) -> bool:
        return self.enabled and self.client is not None

    def _parse_user_name(self, user_id: str, display_name: str | None = None) -> tuple[str, str]:
        """Parse a friendly first/last name from a user identifier."""

        if display_name:
            parts = display_name.split()
            if len(parts) >= 2:
                return parts[0], " ".join(parts[1:])
            return display_name, ""

        if len(user_id.split("-")) == 3 and not user_id.startswith("user-"):
            adjective, noun, number = user_id.split("-")
            return adjective.capitalize(), f"{noun.capitalize()} {number}"

        first_name = "User"
        last_name = user_id[-6:] if len(user_id) > 6 else user_id
        logger.info(
            f"🏷️  Parsed name for user {user_id}: '{first_name} {last_name}'"
        )
        return first_name, last_name

    # ------------------------------------------------------------------
    # User & thread management
    # ------------------------------------------------------------------
    async def create_user(self, user_id: str, display_name: str | None = None) -> bool:
        if not self.is_enabled():
            return False

        try:
            user_api = getattr(self.client, "user", None)
            if user_api is None:
                return False

            try:
                await user_api.get(user_id)
                return True
            except Exception:
                pass

            first_name, last_name = self._parse_user_name(user_id, display_name)
            await user_api.add(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                metadata={"created_by": "researcher-prototype"},
            )
            logger.info(f"Created Zep user: {user_id} ({first_name} {last_name})")
            return True
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to create ZEP user {user_id}: {exc}")
            return False

    async def create_thread(self, thread_id: str, user_id: str) -> bool:
        """Create a thread in Zep."""

        if not self.is_enabled():
            return False

        try:
            thread_api = getattr(self.client, "thread", None)
            if thread_api is None:
                return False

            try:
                await thread_api.get(thread_id)
                logger.debug(f"Thread {thread_id} already exists in Zep")
                return True
            except Exception:
                pass

            await self.create_user(user_id)
            await thread_api.add(
                thread_id=thread_id,
                user_id=user_id,
                metadata={"created_by": "researcher-prototype"},
            )
            logger.info(f"Created ZEP thread: {thread_id} for user {user_id}")
            return True
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to create ZEP thread {thread_id}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    async def add_messages(
        self, thread_id: str, messages: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Add messages to a thread and return the context block."""

        if not self.is_enabled():
            return None

        try:
            thread_api = getattr(self.client, "thread", None)
            if thread_api is None:
                return None

            result = await thread_api.add_messages(
                thread_id=thread_id, messages=messages, return_context=True
            )

            context = None
            if isinstance(result, dict):
                context = result.get("context")
            else:
                context = getattr(result, "context", None)
                if context is None:
                    memory = getattr(result, "memory", None)
                    if memory is not None:
                        context = getattr(memory, "context", None)

            logger.debug(f"Added {len(messages)} messages to thread {thread_id}")
            return context
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to add messages to thread {thread_id}: {exc}")
            return None

    async def store_conversation_turn(
        self,
        user_id: str,
        user_message: str,
        ai_response: str,
        thread_id: str,
    ) -> bool:
        """Store a conversation turn (user + assistant message)."""

        if not self.is_enabled():
            logger.debug("Zep is not enabled, skipping storage")
            return False
        if not thread_id:
            logger.error("Thread ID is required for storing conversation turn")
            return False

        try:
            messages = [
                {"role": "user", "content": user_message, "name": user_id},
                {
                    "role": "assistant",
                    "content": ai_response,
                    "name": "assistant",
                },
            ]
            await self.add_messages(thread_id, messages)
            logger.debug(
                f"Stored conversation turn for user {user_id} in thread {thread_id}"
            )
            return True
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to store conversation in Zep: {exc}")
            return False

    # ------------------------------------------------------------------
    # Graph search helpers
    # ------------------------------------------------------------------
    async def search_user_facts(
        self, user_id: str, query: str, limit: int = 5
    ) -> List[str]:
        if not self.is_enabled():
            return []

        try:
            graph_api = getattr(self.client, "graph", None)
            if graph_api is None:
                return []

            results = await graph_api.search(user_id=user_id, query=query, limit=limit)
            facts: List[str] = []
            if results:
                for item in results:
                    fact = getattr(item, "fact", None)
                    if fact:
                        facts.append(fact)
            return facts
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to search user facts in Zep: {exc}")
            return []

    async def get_nodes_by_user_id(
        self, user_id: str, cursor: Optional[str] = None, limit: int = 100
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        if not self.is_enabled():
            return [], None

        try:
            graph_api = getattr(self.client, "graph", None)
            nodes_api = getattr(graph_api, "nodes", None) if graph_api else None
            if nodes_api is None:
                return [], None

            nodes = await nodes_api.list(
                user_id=user_id, cursor=cursor or "", limit=limit
            )

            transformed: List[Dict[str, Any]] = []
            for node in nodes:
                transformed.append(
                    {
                        "uuid": getattr(node, "uuid", getattr(node, "uuid_", "")),
                        "name": getattr(node, "name", ""),
                        "summary": getattr(node, "summary", ""),
                        "labels": getattr(node, "labels", []) or [],
                        "created_at": getattr(node, "created_at", ""),
                        "updated_at": "",
                        "attributes": getattr(node, "attributes", {}) or {},
                    }
                )

            next_cursor = (
                transformed[-1]["uuid"]
                if transformed and len(transformed) == limit
                else None
            )
            return transformed, next_cursor
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to get nodes for user {user_id}: {exc}")
            return [], None

    async def get_edges_by_user_id(
        self, user_id: str, cursor: Optional[str] = None, limit: int = 100
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        if not self.is_enabled():
            return [], None

        try:
            graph_api = getattr(self.client, "graph", None)
            edges_api = getattr(graph_api, "edges", None) if graph_api else None
            if edges_api is None:
                return [], None

            edges = await edges_api.list(
                user_id=user_id, cursor=cursor or "", limit=limit
            )

            transformed: List[Dict[str, Any]] = []
            for edge in edges:
                transformed.append(
                    {
                        "uuid": getattr(edge, "uuid", getattr(edge, "uuid_", "")),
                        "source_node_uuid": getattr(edge, "source_node_uuid", ""),
                        "target_node_uuid": getattr(edge, "target_node_uuid", ""),
                        "type": "",
                        "name": getattr(edge, "name", ""),
                        "fact": getattr(edge, "fact", ""),
                        "episodes": getattr(edge, "episodes", []) or [],
                        "created_at": getattr(edge, "created_at", ""),
                        "updated_at": "",
                        "valid_at": getattr(edge, "valid_at", None),
                        "metadata": getattr(edge, "metadata", {}) or {},
                    }
                )

            next_cursor = (
                transformed[-1]["uuid"]
                if transformed and len(transformed) == limit
                else None
            )
            return transformed, next_cursor
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to get edges for user {user_id}: {exc}")
            return [], None

    async def get_all_nodes_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        all_nodes: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            nodes, cursor = await self.get_nodes_by_user_id(user_id, cursor, limit=100)
            all_nodes.extend(nodes)
            if cursor is None or not nodes:
                break
        logger.debug(f"Retrieved {len(all_nodes)} nodes for user {user_id}")
        return all_nodes

    async def get_all_edges_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        all_edges: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            edges, cursor = await self.get_edges_by_user_id(user_id, cursor, limit=100)
            all_edges.extend(edges)
            if cursor is None or not edges:
                break
        logger.debug(f"Retrieved {len(all_edges)} edges for user {user_id}")
        return all_edges

    # ------------------------------------------------------------------
    # Graph triplet helper
    # ------------------------------------------------------------------
    def create_triplets(
        self, edges: List[Dict[str, Any]], nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        connected_node_ids = set()
        edge_triplets = []
        for edge in edges:
            source_node = None
            target_node = None
            for node in nodes:
                if node["uuid"] == edge["source_node_uuid"]:
                    source_node = node
                if node["uuid"] == edge["target_node_uuid"]:
                    target_node = node
            if source_node and target_node:
                connected_node_ids.add(source_node["uuid"])
                connected_node_ids.add(target_node["uuid"])
                triplet = {
                    "sourceNode": source_node,
                    "edge": edge,
                    "targetNode": target_node,
                }
                edge_triplets.append(triplet)

        isolated_nodes = [
            node for node in nodes if node["uuid"] not in connected_node_ids
        ]
        isolated_triplets = []
        for node in isolated_nodes:
            virtual_edge = {
                "uuid": f"isolated-node-{node['uuid']}",
                "source_node_uuid": node["uuid"],
                "target_node_uuid": node["uuid"],
                "type": "_isolated_node_",
                "name": "",
                "created_at": node["created_at"],
                "updated_at": node.get("updated_at", ""),
            }

            triplet = {
                "sourceNode": node,
                "edge": virtual_edge,
                "targetNode": node,
            }
            isolated_triplets.append(triplet)

        all_triplets = edge_triplets + isolated_triplets
        logger.debug(
            f"Created {len(all_triplets)} triplets ({len(edge_triplets)} from edges, {len(isolated_triplets)} from isolated nodes)"
        )
        return all_triplets

