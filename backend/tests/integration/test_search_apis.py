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

from services.search_services import OpenAlexSearchService, PubMedSearchService, HackerNewsSearchService  # noqa: E402


async def run_openalex(query: str, limit: int) -> None:
    service = OpenAlexSearchService()
    print("\n=== OpenAlex ===")
    print(f"Query: {query} | Limit: {limit}")
    
    try:
        print("Calling service._search_openalex()...")
        result = await service._search_openalex(query=query, limit=limit)
        print(f"Search completed. Success: {result.get('success')}")
        
        if result.get('success'):
            results = result.get('results', [])
            print(f"Number of results: {len(results)}")
            
            # Check for None items in results
            none_count = sum(1 for item in results if item is None)
            if none_count > 0:
                print(f"WARNING: Found {none_count} None items in results!")
            
            print("\nRaw JSON:")
            print(json.dumps(result, indent=2)[:20000])  # truncate extremely long outputs
            
            print("\nTesting _format_results()...")
            formatted = service._format_results(result)
            print("Format completed successfully")
            print("\nFormatted:")
            print(formatted)
        else:
            print(f"Search failed: {result.get('error')}")
            
    except Exception as e:
        import traceback
        print(f"Exception occurred: {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())


async def run_pubmed(query: str, limit: int) -> None:
    service = PubMedSearchService()
    print("\n=== PubMed ===")
    print(f"Query: {query} | Limit: {limit}")
    # PubMed service uses a different interface, create a mock state
    mock_state = {"messages": [{"content": query, "role": "user"}]}
    result = await service.search(mock_state)
    print("\nRaw JSON:")
    print(json.dumps(result, indent=2)[:20000])
    print("\nFormatted:")
    print(result.get("content", "No content"))


async def run_hn(query: str, limit: int) -> None:
    service = HackerNewsSearchService()
    print("\n=== Hacker News ===")
    print(f"Query: {query} | Limit: {limit}")
    # Hacker News service uses a different interface, create a mock state  
    mock_state = {"messages": [{"content": query, "role": "user"}]}
    result = await service.search(mock_state)
    print("\nRaw JSON:")
    print(json.dumps(result, indent=2)[:20000])
    print("\nFormatted:")
    print(result.get("content", "No content"))


async def test_problematic_queries() -> None:
    """Test queries that have been failing in the app."""
    print("\n=== Testing Problematic Queries ===")
    
    problematic_queries = [
        "hurricane forecasting techniques",
        "open problems number theory", 
        "Sendov's Conjecture advances",
        "Sendov's Conjecture polynomial dynamics",
        "sphere packing problem advances five dimensions"
    ]
    
    for query in problematic_queries:
        print(f"\n--- Testing: {query} ---")
        await run_openalex(query, 5)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test external search APIs via node search methods")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run all search APIs")
    group.add_argument("--openalex", action="store_true", help="Run OpenAlex only")
    group.add_argument("--pubmed", action="store_true", help="Run PubMed only")
    group.add_argument("--hn", action="store_true", help="Run Hacker News only")
    group.add_argument("--test-problems", action="store_true", help="Test problematic queries that fail in app")

    parser.add_argument("--query", type=str, default="artificial intelligence research trends", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results to request")

    args = parser.parse_args()

    if args.test_problems:
        await test_problematic_queries()
    elif args.all or args.openalex:
        await run_openalex(args.query, args.limit)
    if args.all or args.pubmed:
        await run_pubmed(args.query, args.limit)
    if args.all or args.hn:
        await run_hn(args.query, args.limit)


if __name__ == "__main__":
    asyncio.run(main())


