"""
Reddit search node for social media and community discussions.
Uses Reddit API with OAuth for authenticated access.
"""

import asyncio
from typing import Dict, Any, List
import requests
from datetime import datetime, timedelta
from nodes.base_api_search_node import BaseAPISearchNode
from nodes.base import ChatState, logger, config


class RedditSearchNode(BaseAPISearchNode):
    """Search node for Reddit discussions and community insights."""
    
    def __init__(self):
        super().__init__("Reddit")
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        self._access_token = None
        self._token_expires = None
    
    def validate_config(self) -> bool:
        """Check if Reddit API credentials are configured."""
        return all([
            getattr(config, 'REDDIT_CLIENT_ID', None),
            getattr(config, 'REDDIT_CLIENT_SECRET', None),
            getattr(config, 'REDDIT_USER_AGENT', None)
        ])
    
    async def _get_access_token(self) -> str:
        """Get OAuth access token for Reddit API."""
        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return self._access_token
        
        try:
            # Prepare authentication
            auth = requests.auth.HTTPBasicAuth(
                config.REDDIT_CLIENT_ID, 
                config.REDDIT_CLIENT_SECRET
            )
            
            data = {
                'grant_type': 'client_credentials',
                # Request minimal read scope
                'scope': 'read'
            }
            
            headers = {
                'User-Agent': config.REDDIT_USER_AGENT
            }
            
            # Get access token
            response = requests.post(
                self.auth_url,
                auth=auth,
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 3600)
                self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 min buffer
                return self._access_token
            else:
                logger.error(f"Reddit OAuth failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Reddit access token: {str(e)}")
            return None
    
    async def search(self, query: str, limit: int = 25, subreddit: str = None, **kwargs) -> Dict[str, Any]:
        """
        Search Reddit for posts and discussions.
        
        Args:
            query: Search query
            limit: Maximum number of results (default 25, max 100)
            subreddit: Specific subreddit to search (optional)
            
        Returns:
            Dict with search results
        """
        access_token = await self._get_access_token()
        if not access_token:
            return {
                "success": False,
                "error": "Failed to authenticate with Reddit API",
                "results": [],
                "total_count": 0
            }
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': config.REDDIT_USER_AGENT
            }
            
            # Determine search endpoint
            if subreddit:
                search_url = f"{self.base_url}/r/{subreddit}/search"
            else:
                search_url = f"{self.base_url}/search"
            
            # Prepare search parameters
            params = {
                'q': query,
                'limit': min(limit, 100),
                'sort': 'relevance',
                'type': 'link',
                'restrict_sr': 'true' if subreddit else 'false'
            }
            

            
            # Make API request
            response = requests.get(
                search_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                
                # Extract post data
                results = []
                for post in posts:
                    post_data = post.get("data", {})
                    results.append({
                        "title": post_data.get("title", ""),
                        "selftext": post_data.get("selftext", ""),
                        "subreddit": post_data.get("subreddit", ""),
                        "author": post_data.get("author", ""),
                        "score": post_data.get("score", 0),
                        "num_comments": post_data.get("num_comments", 0),
                        "created_utc": post_data.get("created_utc", 0),
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "domain": post_data.get("domain", ""),
                        "is_self": post_data.get("is_self", False)
                    })
                
                return {
                    "success": True,
                    "results": results,
                    "total_count": len(results),
                    "metadata": {
                        "query_used": query,
                        "subreddit_searched": subreddit,
                        "sort_method": params['sort'],
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Reddit API error {response.status_code}: {response.text}",
                    "results": [],
                    "total_count": 0
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Reddit API request timed out",
                "results": [],
                "total_count": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching Reddit: {str(e)}",
                "results": [],
                "total_count": 0
            }
    
    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format Reddit results into readable text."""
        posts = raw_results.get("results", [])
        total_count = raw_results.get("total_count", 0)
        
        if not posts:
            return "No relevant discussions found on Reddit."
        
        formatted_output = []
        formatted_output.append(f"REDDIT COMMUNITY DISCUSSIONS ({len(posts)} posts shown):\n")
        
        for i, post in enumerate(posts[:8], 1):  # Limit to top 8 for readability
            title = post.get("title", "No title")
            subreddit = post.get("subreddit", "unknown")
            author = post.get("author", "unknown")
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)
            selftext = post.get("selftext", "")
            url = post.get("url", "")
            is_self = post.get("is_self", False)
            
            # Convert timestamp
            created_utc = post.get("created_utc", 0)
            if created_utc:
                try:
                    created_date = datetime.fromtimestamp(created_utc).strftime("%Y-%m-%d")
                except:
                    created_date = "Unknown date"
            else:
                created_date = "Unknown date"
            
            formatted_output.append(f"{i}. **{title}**")
            formatted_output.append(f"   r/{subreddit} • u/{author} • {created_date}")
            formatted_output.append(f"   ⬆️ {score} points • 💬 {num_comments} comments")
            
            # Include post content if it's a self-post and has content
            if is_self and selftext and len(selftext.strip()) > 20:
                content_preview = selftext.strip()[:200] + "..." if len(selftext.strip()) > 200 else selftext.strip()
                formatted_output.append(f"   Content: {content_preview}")
            
            formatted_output.append(f"   🔗 {url}")
            formatted_output.append("")  # Empty line between posts
        
        if len(posts) > 8:
            formatted_output.append(f"... and {len(posts) - 8} more discussions available")
        
        return "\n".join(formatted_output)
    
    def _determine_relevant_subreddits(self, query: str) -> List[str]:
        """Determine relevant subreddits based on query content."""
        query_lower = query.lower()
        
        # Map keywords to relevant subreddits
        subreddit_mapping = {
            "stocks": ["investing", "SecurityAnalysis", "stocks"],
            "investing": ["investing", "SecurityAnalysis", "personalfinance"],
            "crypto": ["CryptoCurrency", "Bitcoin", "ethereum"],
            "programming": ["programming", "learnprogramming", "webdev"],
            "ai": ["MachineLearning", "artificial", "singularity"],
            "science": ["science", "Physics", "biology"],
            "technology": ["technology", "gadgets", "TechNewsToday"],
            "gaming": ["gaming", "Games", "pcgaming"],
            "health": ["Health", "medical", "AskDocs"],
            "fitness": ["fitness", "bodybuilding", "loseit"],
        }
        
        relevant_subreddits = []
        for keyword, subreddits in subreddit_mapping.items():
            if keyword in query_lower:
                relevant_subreddits.extend(subreddits)
        
        return relevant_subreddits[:3]  # Return top 3 matches


# Create the search node function
reddit_search_node_instance = RedditSearchNode()

async def reddit_search_node(state: ChatState) -> ChatState:
    """Reddit search node entry point."""
    return await reddit_search_node_instance.execute_search_node(state)