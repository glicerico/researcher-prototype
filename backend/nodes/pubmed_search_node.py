"""
PubMed search node for medical and biomedical research queries.
Uses NCBI E-utilities API (free, no API key required but email recommended).
"""

import asyncio
from typing import Dict, Any, List
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from urllib.parse import quote_plus
from nodes.base_api_search_node import BaseAPISearchNode
from nodes.base import ChatState, logger, config


class PubMedSearchNode(BaseAPISearchNode):
    """Search node for PubMed medical and biomedical research."""
    
    def __init__(self):
        super().__init__("PubMed")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.search_url = f"{self.base_url}/esearch.fcgi"
        self.fetch_url = f"{self.base_url}/efetch.fcgi"
        self.email = getattr(config, 'PUBMED_EMAIL', 'researcher@example.com')
    
    def validate_config(self) -> bool:
        """PubMed E-utilities is free but recommends an email for identification."""
        # Always return True since email is optional but recommended
        return True
    
    async def search(self, query: str, limit: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search PubMed for medical/biomedical research papers.
        
        Args:
            query: Search query
            limit: Maximum number of results (default 20, max 200)
            
        Returns:
            Dict with search results
        """
        try:
            # Step 1: Search for PMIDs
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': min(limit, 200),  # Reasonable limit
                'retmode': 'xml',
                'email': self.email,
                'tool': 'ResearcherPrototype'
            }
            
            # Add date filters if scope indicates recent research
            scope_filters = kwargs.get("scope_filters", [])
            if "recent" in scope_filters:
                # Search last 2 years for medical research
                end_date = datetime.now()
                start_date = end_date - timedelta(days=730)
                date_filter = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[pdat]"
                search_params['term'] = f"({query}) AND {date_filter}"
            elif "medical" in scope_filters:
                # Add medical research focus
                search_params['term'] = f"({query}) AND (clinical[sb] OR systematic[sb])"
            
            # Search for PMIDs
            search_response = requests.get(
                self.search_url,
                params=search_params,
                timeout=30
            )
            
            if search_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"PubMed search failed with status {search_response.status_code}",
                    "results": [],
                    "total_count": 0
                }
            
            # Parse search results XML
            search_root = ET.fromstring(search_response.content)
            pmid_list = [id_elem.text for id_elem in search_root.findall('.//Id')]
            count_elem = search_root.find('.//Count')
            total_count = int(count_elem.text) if count_elem is not None else 0
            
            if not pmid_list:
                return {
                    "success": True,
                    "results": [],
                    "total_count": 0,
                    "metadata": {
                        "query_used": query,
                        "database": "pubmed",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            # Step 2: Fetch detailed information for papers
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(pmid_list),
                'retmode': 'xml',
                'email': self.email,
                'tool': 'ResearcherPrototype'
            }
            
            fetch_response = requests.get(
                self.fetch_url,
                params=fetch_params,
                timeout=30
            )
            
            if fetch_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"PubMed fetch failed with status {fetch_response.status_code}",
                    "results": [],
                    "total_count": 0
                }
            
            # Parse detailed results XML
            results = self._parse_pubmed_xml(fetch_response.content)
            
            return {
                "success": True,
                "results": results,
                "total_count": total_count,
                "metadata": {
                    "query_used": query,
                    "database": "pubmed",
                    "pmids_fetched": len(pmid_list),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "PubMed API request timed out",
                "results": [],
                "total_count": 0
            }
        except ET.ParseError as e:
            return {
                "success": False,
                "error": f"Error parsing PubMed XML response: {str(e)}",
                "results": [],
                "total_count": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error searching PubMed: {str(e)}",
                "results": [],
                "total_count": 0
            }
    
    def _parse_pubmed_xml(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse PubMed XML response into structured data."""
        results = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    # Extract PMID
                    pmid_elem = article.find('.//PMID')
                    pmid = pmid_elem.text if pmid_elem is not None else "Unknown"
                    
                    # Extract basic info
                    medline_citation = article.find('.//MedlineCitation')
                    if medline_citation is None:
                        continue
                    
                    # Title
                    title_elem = medline_citation.find('.//ArticleTitle')
                    title = title_elem.text if title_elem is not None else "No title"
                    
                    # Abstract
                    abstract_elems = medline_citation.findall('.//AbstractText')
                    abstract_parts = []
                    for abstract_elem in abstract_elems:
                        if abstract_elem.text:
                            # Check for structured abstract labels
                            label = abstract_elem.get('Label')
                            text = abstract_elem.text
                            if label:
                                abstract_parts.append(f"{label}: {text}")
                            else:
                                abstract_parts.append(text)
                    abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available"
                    
                    # Authors
                    authors = []
                    for author in medline_citation.findall('.//Author'):
                        lastname_elem = author.find('LastName')
                        forename_elem = author.find('ForeName')
                        if lastname_elem is not None and forename_elem is not None:
                            authors.append(f"{forename_elem.text} {lastname_elem.text}")
                        elif lastname_elem is not None:
                            authors.append(lastname_elem.text)
                    
                    # Journal
                    journal_elem = medline_citation.find('.//Title')
                    journal = journal_elem.text if journal_elem is not None else "Unknown journal"
                    
                    # Publication date
                    pub_date_elem = medline_citation.find('.//PubDate')
                    year = "Unknown year"
                    if pub_date_elem is not None:
                        year_elem = pub_date_elem.find('Year')
                        if year_elem is not None:
                            year = year_elem.text
                    
                    # MeSH terms (Medical Subject Headings)
                    mesh_terms = []
                    for mesh in medline_citation.findall('.//MeshHeading'):
                        descriptor = mesh.find('DescriptorName')
                        if descriptor is not None and descriptor.text:
                            mesh_terms.append(descriptor.text)
                    
                    # DOI
                    doi = None
                    for article_id in article.findall('.//ArticleId'):
                        if article_id.get('IdType') == 'doi':
                            doi = article_id.text
                            break
                    
                    results.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                        "mesh_terms": mesh_terms[:5],  # Limit to top 5 MeSH terms
                        "doi": doi,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing individual PubMed article: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing PubMed XML: {str(e)}")
            
        return results
    
    def format_results(self, raw_results: Dict[str, Any]) -> str:
        """Format PubMed results into readable text."""
        papers = raw_results.get("results", [])
        total_count = raw_results.get("total_count", 0)
        
        if not papers:
            return "No medical research papers found in PubMed."
        
        formatted_output = []
        formatted_output.append(f"PUBMED MEDICAL RESEARCH ({len(papers)} papers shown, {total_count} total):\n")
        
        for i, paper in enumerate(papers[:10], 1):  # Limit to top 10 for readability
            title = paper.get("title", "No title")
            authors = paper.get("authors", [])
            year = paper.get("year", "Unknown year")
            journal = paper.get("journal", "Unknown journal")
            abstract = paper.get("abstract", "No abstract available")
            mesh_terms = paper.get("mesh_terms", [])
            pmid = paper.get("pmid", "Unknown")
            doi = paper.get("doi")
            url = paper.get("url", "")
            
            # Format authors
            authors_str = ", ".join(authors[:3])
            if len(authors) > 3:
                authors_str += f" et al. ({len(authors)} authors total)"
            elif not authors:
                authors_str = "Authors not listed"
            
            # Format MeSH terms
            mesh_str = ", ".join(mesh_terms[:3]) if mesh_terms else "General medical"
            
            formatted_output.append(f"{i}. **{title}** ({year})")
            formatted_output.append(f"   Authors: {authors_str}")
            formatted_output.append(f"   Journal: {journal} | PMID: {pmid} | Topics: {mesh_str}")
            
            if abstract and len(abstract) > 50 and abstract != "No abstract available":
                # Truncate long abstracts
                abstract_preview = abstract[:350] + "..." if len(abstract) > 350 else abstract
                formatted_output.append(f"   Abstract: {abstract_preview}")
            
            if doi:
                formatted_output.append(f"   📄 DOI: {doi}")
                
            formatted_output.append(f"   🔗 PubMed: {url}")
            formatted_output.append("")  # Empty line between papers
        
        if len(papers) > 10:
            formatted_output.append(f"... and {len(papers) - 10} more medical papers available")
        
        return "\n".join(formatted_output)


# Create the search node function
pubmed_search_node_instance = PubMedSearchNode()

async def pubmed_search_node(state: ChatState) -> ChatState:
    """PubMed search node entry point."""
    # Extract scope filters for specialized medical search
    scope_filters = pubmed_search_node_instance.extract_scope_filters(state)
    
    # Override the search method call to pass scope filters
    refined_query = state.get("workflow_context", {}).get("refined_search_query")
    from utils import get_last_user_message
    original_user_query = get_last_user_message(state.get("messages", []))
    query_to_search = refined_query if refined_query else original_user_query
    
    if not query_to_search:
        state["module_results"]["pubmed"] = {
            "success": False,
            "error": "No query found for PubMed search (neither refined nor original).",
        }
        return state
    
    logger.info(f"🔍 PubMed: Searching for medical research: \"{query_to_search[:75]}...\"")
    
    # Perform search with scope filters
    try:
        search_results = await pubmed_search_node_instance.search(
            query_to_search,
            scope_filters=scope_filters
        )
        
        if search_results.get("success", False):
            formatted_content = pubmed_search_node_instance.format_results(search_results)
            result_count = search_results.get("total_count", 0)
            logger.info(f'🔍 PubMed: Found {result_count} medical research papers')
            
            state["module_results"]["pubmed"] = {
                "success": True,
                "result": formatted_content,
                "query_used": query_to_search,
                "total_count": result_count,
                "source": "PubMed",
                "metadata": search_results.get("metadata", {})
            }
        else:
            error_message = search_results.get("error", "Unknown error in PubMed search")
            logger.error(f"PubMed search failed: {error_message}")
            state["module_results"]["pubmed"] = {
                "success": False,
                "error": error_message,
                "source": "PubMed"
            }
            
    except Exception as e:
        error_message = f"Error in PubMed search: {str(e)}"
        logger.error(error_message, exc_info=True)
        state["module_results"]["pubmed"] = {
            "success": False,
            "error": error_message,
            "source": "PubMed"
        }
    
    return state