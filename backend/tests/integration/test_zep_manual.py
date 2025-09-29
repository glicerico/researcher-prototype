#!/usr/bin/env python3
"""
Manual Zep Integration Test

This script allows manual testing of Zep knowledge graph search functionality.
It can be used to test real Zep queries against actual user data to debug
topic expansion issues.

Usage examples:
  python backend/tests/integration/test_zep_manual.py --user fine-calf-52 --query "Alzheimer treatments"
  python backend/tests/integration/test_zep_manual.py --user guest --query "machine learning" --scope nodes
  python backend/tests/integration/test_zep_manual.py --user test-user --query "AI" --limit 20 --verbose

Requirements:
- ZEP_ENABLED=true in .env
- Valid ZEP_API_KEY in .env
- User must exist in Zep with conversation data
"""

import os
import sys
import json
import argparse
import asyncio
from typing import Optional

def _ensure_backend_on_path() -> None:
    """Ensure the backend directory is on the Python path."""
    # Get the backend directory (parent of parent of this file)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

_ensure_backend_on_path()

from dotenv import load_dotenv
load_dotenv()

from storage.zep_manager import ZepManager
from zep_cloud.client import AsyncZep
from services.logging_config import get_logger

logger = get_logger(__name__)


async def test_zep_search(
    user_id: str,
    query: str,
    scope: str = "both",
    limit: int = 10,
    reranker: str = "cross_encoder",
    verbose: bool = False,
    use_direct: bool = False,
    center_node_uuid: Optional[str] = None,
) -> None:
    """Test Zep knowledge graph search for a specific user and query."""
    
    print("=" * 80)
    print("ZEP KNOWLEDGE GRAPH SEARCH TEST")
    print("=" * 80)
    print(f"User ID: {user_id}")
    print(f"Query: '{query}'")
    print(f"Scope: {scope}")
    print(f"Limit: {limit}")
    print(f"Reranker: {reranker}")
    print()

    # Initialize Zep manager
    zep = ZepManager()
    
    if not zep.is_enabled():
        print("❌ ERROR: Zep is not enabled or not properly configured")
        print("   Check ZEP_ENABLED=true and ZEP_API_KEY in .env file")
        return

    print("✅ Zep client initialized successfully")
    print()

    try:
        # Test user existence/creation
        print("🔍 Checking/creating user in Zep...")
        user_created = await zep.create_user(user_id)
        if user_created:
            print(f"✅ User {user_id} exists in Zep")
        else:
            print(f"❌ Failed to create/verify user {user_id}")
            return
        print()

        # First, get all nodes and edges for the user (sanity check)
        print("🔍 Getting ALL nodes for user (sanity check)...")
        all_nodes = await zep.get_all_nodes_by_user_id(user_id)
        print(f"📊 User has {len(all_nodes)} total nodes in knowledge graph")
        
        if all_nodes and verbose:
            print("\n📋 ALL NODES (first 10):")
            for i, node in enumerate(all_nodes[:10], 1):
                name = node.get("name", "unnamed")
                labels = node.get("labels", [])
                uuid = node.get("uuid", "no-uuid")
                print(f"  {i}. {name}")
                if labels:
                    print(f"     Labels: {labels}")
                if verbose:
                    print(f"     UUID: {uuid}")
                print()
        
        print("🔍 Getting ALL edges for user (sanity check)...")
        all_edges = await zep.get_all_edges_by_user_id(user_id)
        print(f"📊 User has {len(all_edges)} total edges in knowledge graph")
        
        if all_edges and verbose:
            print("\n📋 ALL EDGES (first 10):")
            for i, edge in enumerate(all_edges[:10], 1):
                fact = edge.get("fact", "no-fact")
                name = edge.get("name", "unnamed")
                uuid = edge.get("uuid", "no-uuid")
                display_name = fact if fact != "no-fact" else name
                print(f"  {i}. {display_name}")
                if verbose:
                    print(f"     UUID: {uuid}")
                print()
        
        print()

        # Now perform targeted searches based on scope
        nodes = []
        edges = []

        if use_direct:
            print("🔎 Using direct Zep v3 graph.search API (unified search)...")
            client = AsyncZep(api_key=os.getenv("ZEP_API_KEY"))
            # v3 unified search (no scope/reranker). Returns mixed results.
            results = await client.graph.search(
                query=query,
                user_id=user_id,
                limit=limit,
                center_node_uuid=center_node_uuid if center_node_uuid else None,
            )

            print(f"🔬 Raw v3 API response type: {type(results)}")
            
            # Handle GraphSearchResults object - it's iterable with tuple pairs like ('edges', [EntityEdge, ...])
            edge_results = []
            node_results = []
            episode_results = []
            
            if results:
                if verbose:
                    print("🔬 Raw API response structure:")
                    for i, item in enumerate(results):
                        print(f"  Item {i+1}: {item}")
                    print()
                
                for result_type, result_items in results:
                    if result_type == 'edges' and result_items:
                        edge_results.extend(result_items)
                    elif result_type == 'nodes' and result_items:
                        node_results.extend(result_items)
                    elif result_type == 'episodes' and result_items:
                        episode_results.extend(result_items)
            
            print(f"🔬 Extracted results: {len(node_results)} nodes, {len(edge_results)} edges, {len(episode_results)} episodes")

            # Process nodes
            for node_item in node_results:
                name = getattr(node_item, 'name', None)
                labels = getattr(node_item, 'labels', []) or []
                uuid_val = getattr(node_item, 'uuid_', None) or getattr(node_item, 'uuid', None)
                similarity = getattr(node_item, 'score', None)
                
                nodes.append(
                    {
                        "name": name,
                        "labels": labels if isinstance(labels, list) else [],
                        "uuid": uuid_val,
                        "similarity": similarity,
                    }
                )

            # Process edges
            for edge_item in edge_results:
                fact = getattr(edge_item, 'fact', None)
                name = getattr(edge_item, 'name', None)
                source_uuid = getattr(edge_item, 'source_node_uuid', None)
                target_uuid = getattr(edge_item, 'target_node_uuid', None)
                uuid_val = getattr(edge_item, 'uuid_', None) or getattr(edge_item, 'uuid', None)
                similarity = getattr(edge_item, 'score', None)
                
                edges.append(
                    {
                        "fact": fact,
                        "name": fact or name,
                        "source_node_uuid": source_uuid,
                        "target_node_uuid": target_uuid,
                        "uuid": uuid_val,
                        "similarity": similarity,
                    }
                )

            # Respect requested scope for printing
            if scope in ["both", "nodes"]:
                print("🔍 Searching NODES (direct)...")
                print(f"📊 Found {len(nodes)} nodes")
                if nodes:
                    print("\n📋 NODE RESULTS:")
                    for i, node in enumerate(nodes, 1):
                        name = node.get("name", "unnamed")
                        labels = node.get("labels", [])
                        similarity = node.get("similarity")
                        uuid = node.get("uuid", "no-uuid")
                        print(f"  {i}. {name}")
                        if labels:
                            print(f"     Labels: {labels}")
                        if similarity is not None:
                            print(f"     Similarity: {similarity:.3f}")
                        if verbose:
                            print(f"     UUID: {uuid}")
                            print(f"     Raw: {json.dumps(node, indent=6)}")
                        print()
                else:
                    print("   No nodes found")
                print()

            if scope in ["both", "edges"]:
                print("🔍 Searching EDGES (direct)...")
                print(f"📊 Found {len(edges)} edges")
                if edges:
                    print("\n📋 EDGE RESULTS:")
                    for i, edge in enumerate(edges, 1):
                        fact = edge.get("fact", "no-fact")
                        name = edge.get("name", "unnamed")
                        similarity = edge.get("similarity")
                        source_uuid = edge.get("source_node_uuid", "no-source")
                        target_uuid = edge.get("target_node_uuid", "no-target")
                        uuid = edge.get("uuid", "no-uuid")
                        display_name = fact if fact != "no-fact" else name
                        print(f"  {i}. {display_name}")
                        if similarity is not None:
                            print(f"     Similarity: {similarity:.3f}")
                        if verbose:
                            print(f"     Source: {source_uuid}")
                            print(f"     Target: {target_uuid}")
                            print(f"     UUID: {uuid}")
                            print(f"     Raw: {json.dumps(edge, indent=6)}")
                        print()
                else:
                    print("   No edges found")
                print()
        else:
            # Legacy path via ZepManager (uses scope/reranker)
            if scope in ["both", "nodes"]:
                print("🔍 Searching NODES...")
                nodes = await zep.search_graph(
                    user_id=user_id,
                    query=query,
                    scope="nodes",
                    reranker=reranker,
                    limit=limit
                )
                print(f"📊 Found {len(nodes)} nodes")
                if nodes:
                    print("\n📋 NODE RESULTS:")
                    for i, node in enumerate(nodes, 1):
                        name = node.get("name", "unnamed")
                        labels = node.get("labels", [])
                        similarity = node.get("similarity")
                        uuid = node.get("uuid", "no-uuid")
                        print(f"  {i}. {name}")
                        if labels:
                            print(f"     Labels: {labels}")
                        if similarity is not None:
                            print(f"     Similarity: {similarity:.3f}")
                        if verbose:
                            print(f"     UUID: {uuid}")
                            print(f"     Raw: {json.dumps(node, indent=6)}")
                        print()
                else:
                    print("   No nodes found")
                print()

            if scope in ["both", "edges"]:
                print("🔍 Searching EDGES...")
                edges = await zep.search_graph(
                    user_id=user_id,
                    query=query,
                    scope="edges",
                    reranker=reranker,
                    limit=limit
                )
                print(f"📊 Found {len(edges)} edges")
                if edges:
                    print("\n📋 EDGE RESULTS:")
                    for i, edge in enumerate(edges, 1):
                        fact = edge.get("fact", "no-fact")
                        name = edge.get("name", "unnamed")
                        similarity = edge.get("similarity")
                        source_uuid = edge.get("source_node_uuid", "no-source")
                        target_uuid = edge.get("target_node_uuid", "no-target")
                        uuid = edge.get("uuid", "no-uuid")
                        display_name = fact if fact != "no-fact" else name
                        print(f"  {i}. {display_name}")
                        if similarity is not None:
                            print(f"     Similarity: {similarity:.3f}")
                        if verbose:
                            print(f"     Source: {source_uuid}")
                            print(f"     Target: {target_uuid}")
                            print(f"     UUID: {uuid}")
                            print(f"     Raw: {json.dumps(edge, indent=6)}")
                        print()
                else:
                    print("   No edges found")
                print()

        # Summary
        total_results = 0
        if scope in ["both", "nodes"]:
            total_results += len(nodes)
        if scope in ["both", "edges"]:
            total_results += len(edges)

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        # Overall graph data status
        total_graph_data = len(all_nodes) + len(all_edges)
        if total_graph_data > 0:
            print(f"✅ User has {total_graph_data} total items in knowledge graph:")
            print(f"   - {len(all_nodes)} nodes")
            print(f"   - {len(all_edges)} edges")
            print()
        
        # Search results
        if total_results == 0:
            if total_graph_data > 0:
                print(f"⚠️  No search results for query '{query}', but user HAS graph data")
                print("\nPossible reasons:")
                print("1. Query doesn't match any node names or edge facts")
                print("2. Search similarity threshold too high")
                print("3. Reranker not finding relevant matches")
                print("4. Graph search API issue")
                print("\nSuggestions:")
                print("- Try different queries (check node names above)")
                print("- Try broader, simpler terms")
                print("- Check if node names contain the query term")
                print("- Try different reranker settings")
            else:
                print("❌ No results found AND no graph data exists")
                print("\nPossible reasons:")
                print("1. User has no conversation data stored in Zep")
                print("2. Knowledge graph hasn't been processed yet (can take time)")
                print("3. User ID doesn't exist or has no associated data")
                print("\nSuggestions:")
                print("- Have conversations with the system as this user")
                print("- Wait for Zep to process and extract knowledge graph data")
                print("- Check if conversations are being stored to Zep")
        else:
            print(f"✅ Found {total_results} search results from {total_graph_data} total graph items")
            if scope in ["both", "nodes"]:
                print(f"   - {len(nodes)} matching nodes")
            if scope in ["both", "edges"]:
                print(f"   - {len(edges)} matching edges")

    except Exception as e:
        print(f"❌ ERROR during Zep search: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()


async def test_conversation_storage(user_id: str, verbose: bool = False) -> None:
    """Test storing a conversation and checking if it creates graph data."""
    
    print("=" * 80)
    print("ZEP CONVERSATION STORAGE TEST")
    print("=" * 80)
    print(f"User ID: {user_id}")
    print()

    zep = ZepManager()
    
    if not zep.is_enabled():
        print("❌ ERROR: Zep is not enabled")
        return

    try:
        # Store test conversation
        print("💾 Storing test conversation...")
        success = await zep.store_conversation_turn(
            user_id=user_id,
            user_message="I'm interested in learning about artificial intelligence and machine learning algorithms",
            ai_response="Artificial intelligence (AI) is a broad field that includes machine learning, deep learning, neural networks, and natural language processing. Machine learning algorithms like decision trees, random forests, and support vector machines are fundamental to AI systems.",
            thread_id=f"test-thread-{user_id}"
        )
        
        if success:
            print("✅ Conversation stored successfully")
            
            # Wait a moment
            print("⏳ Waiting 3 seconds for potential processing...")
            await asyncio.sleep(3)
            
            # Test immediate search
            print("🔍 Testing immediate search...")
            nodes = await zep.search_graph(user_id, "artificial intelligence", scope="nodes", limit=5)
            edges = await zep.search_graph(user_id, "machine learning", scope="edges", limit=5)
            
            print(f"📊 Immediate results: {len(nodes)} nodes, {len(edges)} edges")
            
            if nodes or edges:
                print("✅ Knowledge graph data found immediately!")
            else:
                print("⚠️  No immediate graph data (normal - processing takes time)")
                
        else:
            print("❌ Failed to store conversation")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()


async def list_all_user_data(user_id: str, verbose: bool = False) -> None:
    """List all nodes and edges for a user."""
    
    print("=" * 80)
    print("ZEP USER DATA LISTING")
    print("=" * 80)
    print(f"User ID: {user_id}")
    print()

    zep = ZepManager()
    
    if not zep.is_enabled():
        print("❌ ERROR: Zep is not enabled")
        return

    try:
        # Check user exists
        print("🔍 Checking user in Zep...")
        user_created = await zep.create_user(user_id)
        if not user_created:
            print(f"❌ Failed to verify user {user_id}")
            return
        print(f"✅ User {user_id} exists in Zep")
        print()

        # Get all nodes
        print("🔍 Fetching ALL nodes...")
        all_nodes = await zep.get_all_nodes_by_user_id(user_id)
        print(f"📊 Found {len(all_nodes)} total nodes")
        
        if all_nodes:
            print("\n📋 ALL NODES:")
            for i, node in enumerate(all_nodes, 1):
                name = node.get("name", "unnamed")
                labels = node.get("labels", [])
                summary = node.get("summary", "")
                uuid = node.get("uuid", "no-uuid")
                created_at = node.get("created_at", "")
                
                print(f"  {i}. {name}")
                if labels:
                    print(f"     Labels: {labels}")
                if summary:
                    print(f"     Summary: {summary}")
                if verbose:
                    print(f"     UUID: {uuid}")
                    print(f"     Created: {created_at}")
                    print(f"     Raw: {json.dumps(node, indent=6)}")
                print()
        else:
            print("   No nodes found")
        
        # Get all edges
        print("🔍 Fetching ALL edges...")
        all_edges = await zep.get_all_edges_by_user_id(user_id)
        print(f"📊 Found {len(all_edges)} total edges")
        
        if all_edges:
            print("\n📋 ALL EDGES:")
            for i, edge in enumerate(all_edges, 1):
                fact = edge.get("fact", "no-fact")
                name = edge.get("name", "unnamed")
                source_uuid = edge.get("source_node_uuid", "no-source")
                target_uuid = edge.get("target_node_uuid", "no-target")
                uuid = edge.get("uuid", "no-uuid")
                created_at = edge.get("created_at", "")
                
                display_name = fact if fact != "no-fact" else name
                print(f"  {i}. {display_name}")
                if verbose:
                    print(f"     Source: {source_uuid}")
                    print(f"     Target: {target_uuid}")
                    print(f"     UUID: {uuid}")
                    print(f"     Created: {created_at}")
                    print(f"     Raw: {json.dumps(edge, indent=6)}")
                print()
        else:
            print("   No edges found")
        
        # Summary
        print("=" * 80)
        print("USER DATA SUMMARY")
        print("=" * 80)
        total_items = len(all_nodes) + len(all_edges)
        if total_items > 0:
            print(f"✅ User has {total_items} total knowledge graph items:")
            print(f"   - {len(all_nodes)} nodes (entities)")
            print(f"   - {len(all_edges)} edges (relationships)")
            print("\nThis means:")
            print("✅ User has conversation data in Zep")
            print("✅ Knowledge graph has been processed")
            print("✅ Topic expansion should be able to find related concepts")
            print("\nIf search queries return 0 results, the issue is:")
            print("- Query doesn't match node names or edge facts")
            print("- Search API parameters (reranker, similarity threshold)")
            print("- Possible bug in search implementation")
        else:
            print("❌ User has no knowledge graph data")
            print("\nThis explains why topic expansion fails:")
            print("- No entities or relationships to find")
            print("- Need conversations to build knowledge graph")
            print("- May need to wait for Zep processing")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Manual Zep Integration Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--user", "-u",
        required=True,
        help="User ID to test (e.g., fine-calf-52, guest, test-user)"
    )
    
    parser.add_argument(
        "--query", "-q",
        help="Search query to test"
    )
    
    parser.add_argument(
        "--scope", "-s",
        choices=["nodes", "edges", "both"],
        default="both",
        help="Search scope (default: both)"
    )
    
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)"
    )
    
    parser.add_argument(
        "--reranker", "-r",
        default="cross_encoder",
        help="Reranker to use (default: cross_encoder)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including raw JSON"
    )
    
    parser.add_argument(
        "--store-test-conversation",
        action="store_true",
        help="Store a test conversation and check for graph data"
    )
    
    parser.add_argument(
        "--list-all-nodes",
        action="store_true",
        help="List all nodes for the user (no search query needed)"
    )

    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct Zep v3 graph.search API (unified results) instead of ZepManager"
    )
    parser.add_argument(
        "--center-node",
        help="Optional center node UUID to rerank results by graph distance",
        default=None,
    )

    args = parser.parse_args()

    async def run_tests():
        if args.store_test_conversation:
            await test_conversation_storage(args.user, args.verbose)
            print()
        
        if args.list_all_nodes:
            await list_all_user_data(args.user, args.verbose)
            print()
        
        if args.query:
            await test_zep_search(
                user_id=args.user,
                query=args.query,
                scope=args.scope,
                limit=args.limit,
                reranker=args.reranker,
                verbose=args.verbose,
                use_direct=args.direct,
                center_node_uuid=args.center_node,
            )
        elif not args.store_test_conversation and not args.list_all_nodes:
            print("❌ ERROR: Either --query, --store-test-conversation, or --list-all-nodes is required")
            parser.print_help()

    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
