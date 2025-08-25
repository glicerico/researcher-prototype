"""
Utility script to manually test the external search APIs used by the nodes:
- Semantic Scholar (academic)
- PubMed (medical)
- Hacker News (social)

It uses the same request/response format as implemented by the node classes
by directly invoking their async `search()` methods and `format_results()`
helpers. Results are printed as raw JSON and as formatted text.

Usage examples:
  python backend/tests/integration/test_search_apis.py --all --query "machine learning"
  python backend/tests/integration/test_search_apis.py --semantic-scholar --query "transformers" --limit 5
  python backend/tests/integration/test_search_apis.py --pubmed --query "diabetes treatment" --limit 10
  python backend/tests/integration/test_search_apis.py --hn --query "new iPhone" --limit 5

Optionally, for PubMed set:
  PUBMED_EMAIL
Optionally, for Semantic Scholar set:
  SEMANTIC_SCHOLAR_API_KEY (recommended to avoid 429 rate limits)
"""

import os
import sys
import json
import argparse
import asyncio


def _ensure_backend_on_path() -> None:
    """Ensure the backend directory is on sys.path for module imports."""
    current_file = os.path.abspath(__file__)
    # Now in tests/integration/, so need to go up two levels to reach backend/
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    if backend_dir not in sys.path:
        sys.path.append(backend_dir)


_ensure_backend_on_path()

from nodes.openalex_node import OpenAlexSearchNode  # noqa: E402
from nodes.pubmed_search_node import PubMedSearchNode  # noqa: E402
from nodes.hacker_news_search_node import HackerNewsSearchNode  # noqa: E402


async def run_openalex(query: str, limit: int) -> None:
    node = OpenAlexSearchNode()
    print("\n=== OpenAlex ===")
    print(f"Query: {query} | Limit: {limit}")
    result = await node.search(query=query, limit=limit)
    print("\nRaw JSON:")
    print(json.dumps(result, indent=2)[:20000])  # truncate extremely long outputs
    print("\nFormatted:")
    print(node.format_results(result))


async def run_pubmed(query: str, limit: int) -> None:
    node = PubMedSearchNode()
    print("\n=== PubMed ===")
    print(f"Query: {query} | Limit: {limit}")
    if not node.validate_config():
        print("Config validation failed for PubMed (this API generally works without keys). Proceeding anyway...")
    result = await node.search(query=query, limit=limit)
    print("\nRaw JSON:")
    print(json.dumps(result, indent=2)[:20000])
    print("\nFormatted:")
    print(node.format_results(result))


async def run_hn(query: str, limit: int) -> None:
    node = HackerNewsSearchNode()
    print("\n=== Hacker News ===")
    print(f"Query: {query} | Limit: {limit}")
    result = await node.search(query=query, limit=limit)
    print("\nRaw JSON:")
    print(json.dumps(result, indent=2)[:20000])
    print("\nFormatted:")
    print(node.format_results(result))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test external search APIs via node search methods")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run all search APIs")
    group.add_argument("--openalex", action="store_true", help="Run OpenAlex only")
    group.add_argument("--pubmed", action="store_true", help="Run PubMed only")
    group.add_argument("--hn", action="store_true", help="Run Hacker News only")

    parser.add_argument("--query", type=str, default="artificial intelligence research trends", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results to request")

    args = parser.parse_args()

    if args.all or args.openalex:
        await run_openalex(args.query, args.limit)
    if args.all or args.pubmed:
        await run_pubmed(args.query, args.limit)
    if args.all or args.hn:
        await run_hn(args.query, args.limit)


if __name__ == "__main__":
    asyncio.run(main())


