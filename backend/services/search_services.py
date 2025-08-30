"""
Search service classes for handling different search sources.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime

from nodes.base import logger, config, get_current_datetime_str, PERPLEXITY_SYSTEM_PROMPT
from utils import get_last_user_message


class BaseSearchService(ABC):
    """Base class for all search services."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    async def search(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute search and return results.
        
        Args:
            state: Chat state containing query and context
            
        Returns:
            Dict with search results including success status, results, and metadata
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that required configuration is available."""
        pass
    
    def _get_query(self, state: Dict[str, Any]) -> Optional[str]:
        """Extract search query from state."""
        # Get refined query if available
        refined_query = state.get("workflow_context", {}).get("refined_search_query")
        if refined_query:
            return refined_query
            
        # Fall back to original user query
        original_query = get_last_user_message(state.get("messages", []))
        return original_query
    
    def _log_search_start(self, query: str):
        """Log the start of a search operation."""
        display_msg = query[:75] + "..." if len(query) > 75 else query
        logger.info(f'🔍 {self.source_name}: Searching for: "{display_msg}"')


class PerplexitySearchService(BaseSearchService):
    """Service for Perplexity web search."""
    
    def __init__(self):
        super().__init__("Perplexity")
    
    def validate_config(self) -> bool:
        """Validate Perplexity API configuration."""
        return bool(config.PERPLEXITY_API_KEY)
    
    async def search(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Perplexity search."""
        logger.info(f"🔍 {self.source_name}: Preparing to search")
        
        query = self._get_query(state)
        if not query:
            return {
                "success": False,
                "error": "No query found for search (neither refined nor original).",
                "source": self.source_name
            }
        
        self._log_search_start(query)
        
        if not self.validate_config():
            return {
                "success": False,
                "error": "Perplexity API key not configured.",
                "source": self.source_name
            }
        
        try:
            # Get personalization context
            user_id = state.get("user_id")
            source_preferences = self._get_source_preferences(user_id)
            content_preferences = self._get_content_preferences(user_id)
            
            # Configure search parameters based on preferences
            web_search_mode = source_preferences.get("web_search_mode", "comprehensive")
            
            # Map internal preference values to valid Perplexity API search_mode values
            search_mode_mapping = {
                "comprehensive": "web",
                "focused": "web", 
                "academic": "academic",
                "web": "web"
            }
            search_mode = search_mode_mapping.get(web_search_mode, "web")
            
            search_recency_filter = source_preferences.get("recency_preference")
            
            # Build request
            headers = {
                "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            web_search_options = {}
            research_depth = content_preferences.get("research_depth", "moderate")
            if research_depth == "comprehensive":
                web_search_options["return_related_questions"] = True
                web_search_options["return_images"] = False
                web_search_options["return_citations"] = True
            
            perplexity_system_prompt = PERPLEXITY_SYSTEM_PROMPT.format(current_time=get_current_datetime_str())
            perplexity_messages = [
                {"role": "system", "content": perplexity_system_prompt},
                {"role": "user", "content": query},
            ]

            payload = {
                "model": config.PERPLEXITY_MODEL, 
                "messages": perplexity_messages, 
                "stream": False,
                "search_mode": search_mode,
                "web_search_options": web_search_options
            }
            
            if search_recency_filter:
                payload["search_recency_filter"] = search_recency_filter

            # Make API request
            response = requests.post("https://api.perplexity.ai/chat/completions", 
                                   headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                response_data = response.json()
                search_result = response_data["choices"][0]["message"]["content"]
                citations = response_data.get("citations", [])
                search_results = response_data.get("search_results", [])

                # Log results
                display_result = search_result[:75] + "..." if len(search_result) > 75 else search_result
                logger.info(f'🔍 {self.source_name}: ✅ Result received: "{display_result}"')
                if citations:
                    logger.info(f"🔍 {self.source_name}: ✅ Found {len(citations)} citations")
                if search_results:
                    logger.info(f"🔍 {self.source_name}: ✅ Found {len(search_results)} search result sources")

                return {
                    "success": True,
                    "result": search_result,
                    "query_used": query,
                    "citations": citations,
                    "search_results": search_results,
                    "source": self.source_name
                }
            else:
                error_message = f"Perplexity API request failed with status code {response.status_code}: {response.text}"
                logger.error(f"🔍 {self.source_name}: ❌ {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "source": self.source_name
                }
                
        except Exception as e:
            error_message = f"Perplexity search error: {str(e)}"
            logger.error(f"🔍 {self.source_name}: ❌ Exception: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "source": self.source_name
            }
    
    def _get_source_preferences(self, user_id: str) -> dict:
        """Get user's source preferences from personalization context."""
        if not user_id:
            return {}
        
        try:
            from nodes.base import personalization_manager
            logger.info(f"🔍 {self.source_name}: Retrieving personalization context for user {user_id}")
            personalization_context = personalization_manager.get_personalization_context(user_id)
            content_prefs = personalization_context.get("content_preferences", {})
            source_preferences = content_prefs.get("source_types", {})
            logger.debug(f"🔍 {self.source_name}: Retrieved source preferences for user {user_id}: {source_preferences}")
            return source_preferences
        except Exception as e:
            logger.warning(f"🔍 {self.source_name}: ⚠️ Could not retrieve personalization context for user {user_id}: {str(e)}")
            return {}

    def _get_content_preferences(self, user_id: str) -> dict:
        """Get full content preferences from personalization context."""
        if not user_id:
            return {}
        try:
            from nodes.base import personalization_manager
            personalization_context = personalization_manager.get_personalization_context(user_id)
            return personalization_context.get("content_preferences", {})
        except Exception as e:
            logger.warning(f"🔍 {self.source_name}: ⚠️ Could not retrieve content preferences for user {user_id}: {str(e)}")
            return {}


class OpenAlexSearchService(BaseSearchService):
    """Service for OpenAlex academic search."""
    
    def __init__(self):
        super().__init__("OpenAlex")
        self.base_url = "https://api.openalex.org"
        self.headers = {
            "User-Agent": "ResearcherPrototype/1.0 (mailto:researcher@example.com)"
        }
    
    def validate_config(self) -> bool:
        """OpenAlex API is free and doesn't require API keys."""
        return True
    
    async def search(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OpenAlex academic search."""
        logger.info(f"🔍 {self.source_name}: Preparing to search")
        
        # Get query with academic optimization if available
        academic_query = state.get("workflow_context", {}).get("academic_search_query")
        refined_query = state.get("workflow_context", {}).get("refined_search_query")
        original_query = get_last_user_message(state.get("messages", []))
        
        query = academic_query or refined_query or original_query
        if not query:
            return {
                "success": False,
                "error": f"No query found for {self.source_name} search (no academic, refined, or original query).",
                "source": self.source_name
            }
        
        self._log_search_start(query)
        
        try:
            search_results = await self._search_openalex(query, limit=10)
            
            if search_results.get("success"):
                results = search_results.get("results", [])
                result_count = len(results)
                
                if result_count > 0:
                    formatted_content = self._format_results(search_results)
                    
                    logger.info(f"🔍 {self.source_name}: ✅ Found {result_count} results")
                    return {
                        "success": True,
                        "content": formatted_content,  # Changed from "result" to "content"
                        "raw_results": search_results,  # Add raw_results with original structure
                        "query_used": query,
                        "source": self.source_name,
                        "result_count": result_count
                    }
                else:
                    return {
                        "success": True,
                        "content": f"No relevant academic papers found on {self.source_name}.",
                        "raw_results": {"results": [], "total_count": 0},  # Empty results in expected structure
                        "query_used": query,
                        "source": self.source_name,
                        "result_count": 0
                    }
            else:
                error_msg = search_results.get("error", "Unknown error")
                logger.warning(f"🔍 {self.source_name}: ❌ Search failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "source": self.source_name
                }
                
        except Exception as e:
            error_message = f"{self.source_name} search error: {str(e)}"
            logger.error(f"🔍 {self.source_name}: ❌ Exception: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "source": self.source_name
            }
    
    async def _search_openalex(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Execute OpenAlex search with smart query strategy."""
        try:
            # Smart search strategy: try title/abstract search first, then general search
            title_params = {
                "filter": f"title.search:{query},type:article,is_retracted:false",
                "sort": "relevance_score:desc",
                "per_page": min(limit, 25),
                "select": "id,title,publication_year,authorships,primary_location,open_access,cited_by_count,abstract_inverted_index,concepts,type"
            }
            
            title_response = requests.get(f"{self.base_url}/works", 
                                        params=title_params, 
                                        headers=self.headers, 
                                        timeout=20)
            
            if title_response.status_code == 200:
                title_data = title_response.json()
                title_results = title_data.get("results", [])
                
                if len(title_results) >= 3:  # Good results from title search
                    return {
                        "success": True,
                        "results": title_results[:limit],
                        "search_strategy": "title_search"
                    }
            
            # If title search didn't yield enough, try abstract search
            abstract_params = {
                "filter": f"abstract.search:{query},type:article,is_retracted:false",
                "sort": "cited_by_count:desc",  # Sort by citations for quality
                "per_page": min(limit, 25),
                "select": "id,title,publication_year,authorships,primary_location,open_access,cited_by_count,abstract_inverted_index,concepts,type"
            }
            
            abstract_response = requests.get(f"{self.base_url}/works", 
                                           params=abstract_params, 
                                           headers=self.headers, 
                                           timeout=20)
            
            if abstract_response.status_code == 200:
                abstract_data = abstract_response.json()
                abstract_results = abstract_data.get("results", [])
                
                # Combine and deduplicate results
                all_results = list(title_results) if 'title_results' in locals() else []
                seen_ids = {r.get("id") for r in all_results}
                
                for result in abstract_results:
                    if result.get("id") not in seen_ids:
                        all_results.append(result)
                        if len(all_results) >= limit:
                            break
                
                return {
                    "success": True,
                    "results": all_results[:limit],
                    "search_strategy": "combined"
                }
            else:
                return {
                    "success": False,
                    "error": f"OpenAlex API error: {abstract_response.status_code} - {abstract_response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "OpenAlex API request timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching OpenAlex: {str(e)}"
            }
    
    def _format_results(self, search_results: Dict[str, Any]) -> str:
        """Format OpenAlex results for LLM context."""
        results = search_results.get("results", [])
        if not results:
            return "No relevant academic papers found on OpenAlex."
        
        lines = [f"OPENALEX ACADEMIC PAPERS ({min(len(results), 10)} items shown):\n"]
        
        for i, item in enumerate(results[:10], 1):
            title = item.get("title", "No title")
            year = item.get("publication_year", "Unknown year")
            
            # Format authors
            authorships = item.get("authorships", [])
            authors = []
            for auth in authorships[:3]:  # Limit to first 3 authors
                if auth.get("author", {}).get("display_name"):
                    authors.append(auth["author"]["display_name"])
            
            if len(authorships) > 3:
                authors.append("et al.")
            
            author_str = ", ".join(authors) if authors else "Unknown authors"
            
            # Get journal/venue
            primary_location = item.get("primary_location", {})
            venue = primary_location.get("source", {}).get("display_name", "Unknown venue")
            
            # Get citation count
            cited_by_count = item.get("cited_by_count", 0)
            
            # Get abstract snippet
            abstract_index = item.get("abstract_inverted_index", {})
            abstract_text = ""
            if abstract_index:
                # Reconstruct first part of abstract
                word_positions = []
                for word, positions in abstract_index.items():
                    for pos in positions[:1]:  # Just first occurrence
                        word_positions.append((pos, word))
                
                # Sort by position and take first 50 words
                word_positions.sort()
                abstract_words = [word for _, word in word_positions[:50]]
                abstract_text = " ".join(abstract_words)
                if len(word_positions) > 50:
                    abstract_text += "..."
            
            # Format entry
            lines.append(f"{i}. **{title}** ({year})")
            lines.append(f"   Authors: {author_str}")
            lines.append(f"   Venue: {venue}")
            lines.append(f"   Citations: {cited_by_count}")
            
            if abstract_text:
                lines.append(f"   Abstract: {abstract_text}")
            
            # Add OpenAlex link
            openalex_id = item.get("id", "").replace("https://openalex.org/", "")
            if openalex_id:
                lines.append(f"   OpenAlex ID: {openalex_id}")
            
            lines.append("")  # Blank line between entries
        
        return "\n".join(lines)


class HackerNewsSearchService(BaseSearchService):
    """Service for Hacker News social search."""
    
    def __init__(self):
        super().__init__("Hacker News")
        self.search_url = "https://hn.algolia.com/api/v1/search"
    
    def validate_config(self) -> bool:
        """No API key required for HN Algolia endpoint."""
        return True
    
    async def search(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Hacker News search."""
        logger.info(f"🔍 {self.source_name}: Preparing to search")
        
        # Check for social-optimized query first
        social_query = state.get("workflow_context", {}).get("social_search_query")
        if social_query:
            query = social_query
            logger.info(f"🔍 {self.source_name}: Using LLM-optimized social query: '{query}'")
        else:
            query = self._get_query(state)
            if not query:
                return {
                    "success": False,
                    "error": "No query found for Hacker News search",
                    "source": self.source_name
                }
            logger.info(f"🔍 {self.source_name}: No social query available, using standard refined query")
        
        self._log_search_start(query)
        
        try:
            params = {
                "query": query,
                "tags": "(story,comment)",
                "hitsPerPage": min(10, 50),
                "typoTolerance": "min",
                "restrictSearchableAttributes": "title,comment_text,url"
            }

            response = requests.get(self.search_url, params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                
                if hits:
                    formatted_content = self._format_results({"hits": hits})
                    logger.info(f"🔍 {self.source_name}: ✅ Found {len(hits)} discussions")
                    return {
                        "success": True,
                        "content": formatted_content,  # Changed from "result" to "content"
                        "raw_results": {"results": hits, "total_count": len(hits)},  # Add raw_results structure
                        "query_used": query,
                        "source": self.source_name,
                        "result_count": len(hits)
                    }
                else:
                    return {
                        "success": True,
                        "content": f"No relevant discussions found on {self.source_name}.",
                        "raw_results": {"results": [], "total_count": 0},  # Empty results in expected structure
                        "query_used": query,
                        "source": self.source_name,
                        "result_count": 0
                    }
            else:
                error_message = f"Hacker News API request failed with status {response.status_code}: {response.text}"
                logger.error(f"🔍 {self.source_name}: ❌ {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "source": self.source_name
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Hacker News API request timed out",
                "source": self.source_name
            }
        except Exception as e:
            error_message = f"Error searching Hacker News: {str(e)}"
            logger.error(f"🔍 {self.source_name}: ❌ Exception: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "source": self.source_name
            }
    
    def _format_results(self, search_results: Dict[str, Any]) -> str:
        """Format Hacker News results for LLM context."""
        items = search_results.get("hits", [])
        if not items:
            return "No relevant discussions found on Hacker News."
        
        lines = [f"HACKER NEWS DISCUSSIONS ({min(len(items), 10)} items shown):\n"]
        
        for i, item in enumerate(items[:10], 1):
            item_type = "Story" if item.get("title") else "Comment"
            
            if item_type == "Story":
                title = item.get("title", "No title")
                url = item.get("url", "")
                points = item.get("points", 0)
                num_comments = item.get("num_comments", 0)
                created_at = item.get("created_at", "")
                
                lines.append(f"{i}. **{title}** [{item_type}]")
                if url:
                    lines.append(f"   URL: {url}")
                lines.append(f"   Points: {points}, Comments: {num_comments}")
                if created_at:
                    lines.append(f"   Posted: {created_at}")
                    
            else:  # Comment
                comment_text = item.get("comment_text", "")
                story_title = item.get("story_title", "Unknown story")
                author = item.get("author", "Unknown")
                points = item.get("points", 0)
                
                # Truncate long comments
                if len(comment_text) > 200:
                    comment_text = comment_text[:200] + "..."
                
                lines.append(f"{i}. **Comment on: {story_title}** [{item_type}]")
                lines.append(f"   Author: {author}, Points: {points}")
                if comment_text:
                    lines.append(f"   Text: {comment_text}")
            
            lines.append("")  # Blank line between entries
        
        return "\n".join(lines)


class PubMedSearchService(BaseSearchService):
    """Service for PubMed medical search."""
    
    def __init__(self):
        super().__init__("PubMed")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.email = config.PUBMED_EMAIL
    
    def validate_config(self) -> bool:
        """PubMed doesn't require API key but email is recommended."""
        return True  # Always available
    
    async def search(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PubMed search."""
        logger.info(f"🔍 {self.source_name}: Preparing to search")
        
        # Check for medical-optimized query first
        medical_query = state.get("workflow_context", {}).get("medical_search_query")
        if medical_query:
            query = medical_query
            logger.info(f"🔍 {self.source_name}: Using LLM-optimized medical query: '{query}'")
        else:
            query = self._get_query(state)
            if not query:
                return {
                    "success": False,
                    "error": "No query found for PubMed search",
                    "source": self.source_name
                }
            logger.info(f"🔍 {self.source_name}: No medical query available, using standard refined query")
        
        self._log_search_start(query)
        
        try:
            # Step 1: Search for article IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": "10",
                "retmode": "json",
                "sort": "relevance",
                "tool": "ResearcherPrototype",
                "email": self.email
            }
            
            search_response = requests.get(f"{self.base_url}/esearch.fcgi", 
                                         params=search_params, 
                                         timeout=20)
            
            if search_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"PubMed search failed with status {search_response.status_code}",
                    "source": self.source_name
                }
            
            search_data = search_response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return {
                    "success": True,
                    "content": f"No relevant medical literature found on {self.source_name}.",
                    "raw_results": {"results": [], "total_count": 0},  # Empty results in expected structure
                    "query_used": query,
                    "source": self.source_name,
                    "result_count": 0
                }
            
            # Step 2: Fetch article details
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml",
                "tool": "ResearcherPrototype",
                "email": self.email
            }
            
            fetch_response = requests.get(f"{self.base_url}/efetch.fcgi", 
                                        params=fetch_params, 
                                        timeout=20)
            
            if fetch_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"PubMed fetch failed with status {fetch_response.status_code}",
                    "source": self.source_name
                }
            
            # Parse XML and format results
            articles = self._parse_pubmed_xml(fetch_response.text)
            formatted_content = self._format_results({"articles": articles})
            
            logger.info(f"🔍 {self.source_name}: ✅ Found {len(articles)} articles")
            return {
                "success": True,
                "content": formatted_content,  # Changed from "result" to "content"
                "raw_results": {"results": articles, "total_count": len(articles)},  # Add raw_results structure
                "query_used": query,
                "source": self.source_name,
                "result_count": len(articles)
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "PubMed API request timed out",
                "source": self.source_name
            }
        except Exception as e:
            error_message = f"Error searching PubMed: {str(e)}"
            logger.error(f"🔍 {self.source_name}: ❌ Exception: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "source": self.source_name
            }
    
    def _parse_pubmed_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML response into structured data."""
        # Simple XML parsing - in production you'd use xml.etree.ElementTree
        articles = []
        
        # This is a simplified parser - normally you'd use proper XML parsing
        # For now, return a basic structure to maintain functionality
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                title_elem = article.find(".//ArticleTitle")
                abstract_elem = article.find(".//Abstract/AbstractText")
                pmid_elem = article.find(".//PMID")
                journal_elem = article.find(".//Journal/Title")
                pub_date_elem = article.find(".//PubDate/Year")
                
                # Extract authors
                authors = []
                for author in article.findall(".//Author"):
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None and forename is not None:
                        authors.append(f"{forename.text} {lastname.text}")
                
                article_data = {
                    "title": title_elem.text if title_elem is not None else "No title",
                    "abstract": abstract_elem.text if abstract_elem is not None else "",
                    "pmid": pmid_elem.text if pmid_elem is not None else "",
                    "journal": journal_elem.text if journal_elem is not None else "Unknown journal",
                    "year": pub_date_elem.text if pub_date_elem is not None else "Unknown year",
                    "authors": authors[:3]  # Limit to first 3 authors
                }
                articles.append(article_data)
                
        except Exception as e:
            logger.warning(f"🔍 {self.source_name}: Error parsing XML: {str(e)}")
            # Return empty list if parsing fails
            
        return articles
    
    def _format_results(self, search_results: Dict[str, Any]) -> str:
        """Format PubMed results for LLM context."""
        articles = search_results.get("articles", [])
        if not articles:
            return "No relevant medical literature found on PubMed."
        
        lines = [f"PUBMED MEDICAL LITERATURE ({min(len(articles), 10)} items shown):\n"]
        
        for i, article in enumerate(articles[:10], 1):
            title = article.get("title", "No title")
            authors = article.get("authors", [])
            journal = article.get("journal", "Unknown journal")
            year = article.get("year", "Unknown year")
            pmid = article.get("pmid", "")
            abstract = article.get("abstract", "")
            
            author_str = ", ".join(authors)
            if len(authors) == 3:  # Assume truncated
                author_str += " et al."
            
            lines.append(f"{i}. **{title}** ({year})")
            if author_str:
                lines.append(f"   Authors: {author_str}")
            lines.append(f"   Journal: {journal}")
            if pmid:
                lines.append(f"   PMID: {pmid}")
                lines.append(f"   URL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            
            # Add abstract snippet
            if abstract:
                if len(abstract) > 300:
                    abstract = abstract[:300] + "..."
                lines.append(f"   Abstract: {abstract}")
            
            lines.append("")  # Blank line between entries
        
        return "\n".join(lines)