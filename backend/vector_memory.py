import uuid
import time
from typing import List, Dict, Any
try:
    from pinecone import Pinecone
except Exception:  # pragma: no cover - optional dependency
    Pinecone = None
from logging_config import get_logger
import config

logger = get_logger(__name__)


class VectorMemory:
    """Simple wrapper around a Pinecone index for long-term memory."""

    def __init__(self):
        api_key = config.PINECONE_API_KEY
        host = config.PINECONE_HOST
        if not api_key or not host or Pinecone is None:
            self.index = None
            logger.warning(
                "Pinecone not available or configuration missing; vector memory disabled"
            )
            return
        try:
            pc = Pinecone(api_key=api_key)
            self.index = pc.Index(host=host)
            logger.info("Vector memory initialized with Pinecone")
        except Exception as exc:
            self.index = None
            logger.error(f"Failed to initialize Pinecone index: {exc}")

    def _upsert_records(self, namespace: str, records: List[Dict[str, Any]]) -> None:
        if not self.index or not records:
            return
        try:
            self.index.upsert_records(namespace, records)
        except Exception as exc:
            logger.error(f"Failed to upsert records to Pinecone: {exc}")

    def store_message(self, user_id: str, conversation_id: str, message: Dict[str, Any]) -> None:
        record = {
            "_id": str(uuid.uuid4()),
            "chunk_text": message.get("content", ""),
            "category": "message",
            "role": message.get("role"),
            "conversation_id": conversation_id,
            "timestamp": message.get("timestamp", time.time()),
        }
        self._upsert_records(user_id, [record])

    def store_search_result(self, user_id: str, conversation_id: str, text: str) -> None:
        record = {
            "_id": str(uuid.uuid4()),
            "chunk_text": text,
            "category": "search",
            "conversation_id": conversation_id,
            "timestamp": time.time(),
        }
        self._upsert_records(user_id, [record])

    def store_analysis_result(self, user_id: str, conversation_id: str, text: str) -> None:
        record = {
            "_id": str(uuid.uuid4()),
            "chunk_text": text,
            "category": "analysis",
            "conversation_id": conversation_id,
            "timestamp": time.time(),
        }
        self._upsert_records(user_id, [record])

    def search(self, user_id: str, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        if not self.index:
            return []
        if top_k is None:
            top_k = config.PINECONE_TOP_K
        try:
            results = self.index.search(
                namespace=user_id,
                query={"inputs": {"text": query}, "top_k": top_k},
                fields=["category", "chunk_text", "role", "conversation_id", "timestamp"],
            )
            return results.get("result", {}).get("hits", [])
        except Exception as exc:
            logger.error(f"Pinecone search failed: {exc}")
            return []
