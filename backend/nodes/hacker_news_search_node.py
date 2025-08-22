"""
Hacker News search node for social and community tech discussions.
Uses Algolia Hacker News Search API (free) for full-text search and ranking.
"""

import asyncio
from typing import Dict, Any, List
import requests
from datetime import datetime
from nodes.base_api_search_node import BaseAPISearchNode
from nodes.base import ChatState, logger

# Fixed result key for this search source
RESULT_KEY = "social_search"


class HackerNewsSearchNode(BaseAPISearchNode):
    """Search node for Hacker News discussions and threads."""

    def __init__(self):
        super().__init__("Hacker News")
        self.search_url = "https://hn.algolia.com/api/v1/search"

    def validate_config(self) -> bool:
        """No API key required for HN Algolia endpoint."""
        return True

    async def search(self, query: str, limit: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search Hacker News for stories and comments related to the query.

        Args:
            query: Search query
            limit: Max number of results (default 20)

        Returns:
            Dict with search results
        """
        try:
            params = {
                "query": query,
                "tags": "(story,comment)",
                "hitsPerPage": min(max(limit, 1), 50),
                "typoTolerance": "min",
                "restrictSearchableAttributes": "title,comment_text,url"
            }

            response = requests.get(self.search_url, params=params, timeout=20)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HN API error {response.status_code}: {response.text}",
                    "results": [],
                    "total_count": 0,
                }

            data = response.json()
            hits = data.get("hits", [])

            results: List[Dict[str, Any]] = []
            for h in hits:
                is_comment = h.get("_tags", []) and "comment" in h.get("_tags", [])
                created_at = h.get("created_at")
                try:
                    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%Y-%m-%d") if created_at else "Unknown date"
                except Exception:
                    created_date = "Unknown date"

                results.append({
                    "type": "comment" if is_comment else "story",
                    "title": h.get("title") or h.get("story_title") or "",
                    "text": h.get("comment_text") or "",
                    "points": h.get("points", 0),
                    "num_comments": h.get("num_comments", 0),
                    "author": h.get("author", "unknown"),
                    "created": created_date,
                    "url": h.get("url") or h.get("story_url") or (f"https://news.ycombinator.com/item?id={h.get('objectID')}"),
                })

            return {
                "success": True,
                "results": results,
                "total_count": len(results),
                "metadata": {
                    "query_used": query,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Hacker News API request timed out",
                "results": [],
                "total_count": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching Hacker News: {str(e)}",
                "results": [],
                "total_count": 0
            }

    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format Hacker News results for LLM context."""
        items = raw_results.get("results", [])
        if not items:
            return "No relevant discussions found on Hacker News."

        lines: List[str] = []
        lines.append(f"HACKER NEWS DISCUSSIONS ({min(len(items), 10)} items shown):\n")

        for i, item in enumerate(items[:10], 1):
            title = item.get("title", "(no title)")
            author = item.get("author", "unknown")
            created = item.get("created", "unknown")
            points = item.get("points", 0)
            num_comments = item.get("num_comments", 0)
            url = item.get("url", "")
            itype = item.get("type", "story")
            text = item.get("text", "")

            lines.append(f"{i}. [{itype}] {title}")
            lines.append(f"   by {author} • {created} • ⬆️ {points} • 💬 {num_comments}")
            if itype == "comment" and text:
                preview = text.strip()
                preview = (preview[:200] + "...") if len(preview) > 200 else preview
                lines.append(f"   Comment: {preview}")
            if url:
                lines.append(f"   🔗 {url}")
            lines.append("")

        if len(items) > 10:
            lines.append(f"... and {len(items) - 10} more items available")

        return "\n".join(lines)


# Create the node function
hacker_news_search_node_instance = HackerNewsSearchNode()

async def hacker_news_search_node(state: ChatState) -> ChatState:
    """Hacker News search node entry point with social query optimization."""
    # Check if there's a social-optimized query from the search optimizer
    social_query = state.get("workflow_context", {}).get("social_search_query")
    
    if social_query:
        # Use the LLM-optimized social query
        logger.info(f"🔍 Hacker News: Using LLM-optimized social query: '{social_query}'")
        # Temporarily store the social query as the refined query for the base class
        original_refined_query = state.get("workflow_context", {}).get("refined_search_query")
        state["workflow_context"]["refined_search_query"] = social_query
        
        # Execute search with social query
        result_state = await hacker_news_search_node_instance.execute_search_node(state, RESULT_KEY)
        
        # Restore the original refined query
        if original_refined_query:
            state["workflow_context"]["refined_search_query"] = original_refined_query
        
        return result_state
    else:
        # Fall back to standard refined query
        logger.info("🔍 Hacker News: No social query available, using standard refined query")
        return await hacker_news_search_node_instance.execute_search_node(state, RESULT_KEY)


