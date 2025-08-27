"""
Citation processing module for response rendering.

This module handles the conversion of citation data into formatted markdown
sources sections and processes citation markers in text.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from nodes.base import logger


class CitationProcessor:
    """Handles citation processing and formatting for response rendering."""
    
    def __init__(self):
        """Initialize the citation processor."""
        pass
    
    def create_citation_url_map(self, unified_citations: List[Dict[str, Any]], 
                               fallback_citations: List[str]) -> Dict[int, str]:
        """
        Create a mapping from citation numbers to URLs.
        
        Args:
            unified_citations: List of detailed citation objects
            fallback_citations: List of URLs as fallback
            
        Returns:
            Dictionary mapping citation numbers to URLs
        """
        if unified_citations:
            return {i + 1: citation.get("url", "") for i, citation in enumerate(unified_citations)}
        else:
            return {i + 1: url for i, url in enumerate(fallback_citations)}
    
    def replace_citation_markers(self, text: str, citation_url_map: Dict[int, str]) -> str:
        """
        Replace citation markers [n] with markdown hyperlinks, avoiding double bracketing.
        
        Args:
            text: Text containing citation markers
            citation_url_map: Mapping from citation numbers to URLs
            
        Returns:
            Text with citation markers replaced by hyperlinks
        """
        def replace_citation(match):
            citation_num = int(match.group(1))
            url = citation_url_map.get(citation_num)
            if url:
                # Check if this citation is already wrapped in double brackets
                # by looking at the preceding character
                full_match = match.group(0)  # The full match like "[1]"
                start_pos = match.start()
                
                # Check if there's a '[' immediately before this match
                if start_pos > 0 and text[start_pos - 1] == '[':
                    # Already has an opening bracket, so we just need the closing bracket and URL
                    return f"{citation_num}]]({url})"
                else:
                    # Wrap the citation number in another set of brackets to keep them in the link text
                    return f"[[{citation_num}]]({url})"
            return match.group(0)  # Return original if no URL found

        # First, handle any existing double-bracketed citations [[n]]
        # These are already properly formatted, so we just add the URL
        def replace_double_bracketed(match):
            citation_num = int(match.group(1))
            url = citation_url_map.get(citation_num)
            if url:
                return f"[[{citation_num}]]({url})"
            return match.group(0)
        
        # Process double-bracketed citations first
        text = re.sub(r"\[\[(\d+)\]\]", replace_double_bracketed, text)
        
        # Then process single-bracketed citations that aren't already processed
        # Use negative lookbehind and lookahead to avoid matching citations that are part of [[n]]
        return re.sub(r"(?<!\[)\[(\d+)\](?!\])", replace_citation, text)
    
    def _format_academic_citation(self, citation: Dict[str, Any], citation_counter: int) -> str:
        """Format an academic citation with metadata."""
        title = citation.get("title", "Unknown Title")
        url = citation.get("url", "")
        
        citation_parts = [f"[{citation_counter}]. [{title}]({url})"]
        
        # Add academic-specific metadata
        authors = citation.get("authors", [])
        year = citation.get("year")
        venue = citation.get("venue")
        metadata_parts = []
        
        if authors and len(authors) > 0:
            author_names = [a.get("name", "") for a in authors[:2]]  # First 2 authors
            if author_names:
                metadata_parts.append(f"Authors: {', '.join(author_names)}")
        if year:
            metadata_parts.append(f"Year: {year}")
        if venue:
            metadata_parts.append(f"Venue: {venue}")
        
        if metadata_parts:
            citation_parts.append(f" — {'; '.join(metadata_parts)}")
        
        return "".join(citation_parts)
    
    def _format_clinical_citation(self, citation: Dict[str, Any], citation_counter: int) -> str:
        """Format a clinical/medical citation with metadata."""
        title = citation.get("title", "Unknown Title")
        url = citation.get("url", "")
        
        citation_parts = [f"[{citation_counter}]. [{title}]({url})"]
        
        # Add clinical-specific metadata
        authors = citation.get("authors", [])
        journal = citation.get("journal")
        pubdate = citation.get("pubdate")
        metadata_parts = []
        
        if authors and len(authors) > 0:
            author_names = [a.get("name", "") for a in authors[:2]]
            if author_names:
                metadata_parts.append(f"Authors: {', '.join(author_names)}")
        if journal:
            metadata_parts.append(f"Journal: {journal}")
        if pubdate:
            metadata_parts.append(f"Published: {pubdate}")
        
        if metadata_parts:
            citation_parts.append(f" — {'; '.join(metadata_parts)}")
        
        return "".join(citation_parts)
    
    def _format_social_citation(self, citation: Dict[str, Any], citation_counter: int) -> str:
        """Format a social media citation with metadata."""
        title = citation.get("title", "Unknown Title")
        url = citation.get("url", "")
        
        citation_parts = [f"[{citation_counter}]. [{title}]({url})"]
        
        # Add social-specific metadata
        author = citation.get("author")
        points = citation.get("points")
        comments = citation.get("comments")
        metadata_parts = []
        
        if author:
            metadata_parts.append(f"Author: {author}")
        if points:
            metadata_parts.append(f"Points: {points}")
        if comments:
            metadata_parts.append(f"Comments: {comments}")
        
        if metadata_parts:
            citation_parts.append(f" — {'; '.join(metadata_parts)}")
        
        return "".join(citation_parts)
    
    def _format_web_citation(self, citation: Dict[str, Any], citation_counter: int) -> str:
        """Format a web citation (simple format)."""
        title = citation.get("title", "Unknown Title")
        url = citation.get("url", "")
        
        return f"[{citation_counter}]. [{title}]({url})"
    
    def _group_citations_by_type(self, unified_citations: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        Group citations by their type and format them.
        
        Args:
            unified_citations: List of citation objects
            
        Returns:
            Tuple of (web_citations, academic_citations, social_citations, medical_citations)
        """
        web_citations = []
        academic_citations = []
        social_citations = []
        medical_citations = []
        
        citation_counter = 1
        
        for citation in unified_citations:
            url = citation.get("url", "")
            citation_type = citation.get("type", "")
            
            if url:
                if citation_type in ["academic", "scholarly"]:
                    academic_citations.append(self._format_academic_citation(citation, citation_counter))
                elif citation_type == "clinical":
                    medical_citations.append(self._format_clinical_citation(citation, citation_counter))
                elif citation_type == "sentiment":
                    social_citations.append(self._format_social_citation(citation, citation_counter))
                elif citation_type == "web":
                    web_citations.append(self._format_web_citation(citation, citation_counter))
                else:
                    # Default handling for unrecognized citation types
                    logger.warning(f"Unknown citation type '{citation_type}' for citation {citation_counter}, adding to web citations")
                    web_citations.append(self._format_web_citation(citation, citation_counter))
                
                citation_counter += 1
        
        return web_citations, academic_citations, social_citations, medical_citations
    
    def _build_sources_content_with_headers(self, web_citations: List[str], academic_citations: List[str], 
                                          social_citations: List[str], medical_citations: List[str]) -> List[str]:
        """Build the sources content with appropriate headers."""
        sources_content_parts = []
        
        if web_citations:
            sources_content_parts.append("**Web Search:**")
            sources_content_parts.extend(web_citations)
        
        if academic_citations:
            if sources_content_parts:
                sources_content_parts.append("")  # Empty line between sections
            sources_content_parts.append("**Academic Papers:**")
            sources_content_parts.extend(academic_citations)
        
        if social_citations:
            if sources_content_parts:
                sources_content_parts.append("")
            sources_content_parts.append("**Social Media:**")
            sources_content_parts.extend(social_citations)
        
        if medical_citations:
            if sources_content_parts:
                sources_content_parts.append("")
            sources_content_parts.append("**Medical Research:**")
            sources_content_parts.extend(medical_citations)
        
        return sources_content_parts
    
    def _format_fallback_sources(self, search_sources: List[Dict[str, Any]]) -> List[str]:
        """Format fallback sources when no unified citations are available."""
        sources_list = []
        for i, source in enumerate(search_sources, 1):
            title = source.get("title", "Unknown Title")
            url = source.get("url")
            if url:
                sources_list.append(f"[{i}]. [{title}]({url})")
        return sources_list
    
    def generate_sources_section(self, unified_citations: List[Dict[str, Any]], 
                                search_sources: List[Dict[str, Any]], 
                                successful_sources: List[Dict[str, Any]], 
                                failure_note: str = "") -> str:
        """
        Generate the complete sources section for a response.
        
        Args:
            unified_citations: List of detailed citation objects
            search_sources: Fallback search sources  
            successful_sources: List of successful source operations
            failure_note: Optional note about failed sources
            
        Returns:
            Formatted sources section as markdown string
        """
        if not (unified_citations or search_sources or successful_sources):
            # Still show failure note if present, even with no sources
            if failure_note:
                return f"\n*{failure_note.strip()}*"
            return ""
        
        sources_section_parts = []
        
        # Add source attribution summary if multiple sources were used
        if len(successful_sources) > 1:
            source_names = [s.get("name", "Unknown") for s in successful_sources]
            attribution = f"\n\n*Information synthesized from {len(successful_sources)} sources: {', '.join(source_names)}*"
            sources_section_parts.append(attribution)
        
        # Add detailed sources list from unified citations (preferred)
        if unified_citations:
            web_citations, academic_citations, social_citations, medical_citations = self._group_citations_by_type(unified_citations)
            sources_content_parts = self._build_sources_content_with_headers(
                web_citations, academic_citations, social_citations, medical_citations
            )
            
            if sources_content_parts:
                sources_section_parts.append("\n\n**Sources:**\n" + "\n".join(sources_content_parts))
        
        # Fallback to old search_sources format if no unified citations
        elif search_sources:
            sources_list = self._format_fallback_sources(search_sources)
            if sources_list:
                sources_section_parts.append("\n\n**Sources:**\n" + "\n".join(sources_list))
        
        # Add failure notice if any sources failed
        if failure_note:
            sources_section_parts.append(f"\n*{failure_note.strip()}*")
        
        return "".join(sources_section_parts)
    
    def process_citations(self, text: str, unified_citations: List[Dict[str, Any]], 
                         fallback_citations: List[str], search_sources: List[Dict[str, Any]], 
                         successful_sources: List[Dict[str, Any]], failure_note: str = "") -> str:
        """
        Complete citation processing: replace markers and add sources section.
        
        Args:
            text: Text with citation markers to process
            unified_citations: List of detailed citation objects
            fallback_citations: List of URLs as fallback
            search_sources: Fallback search sources
            successful_sources: List of successful source operations
            failure_note: Optional note about failed sources
            
        Returns:
            Text with processed citations and sources section
        """
        # Create URL mapping and replace citation markers
        citation_url_map = self.create_citation_url_map(unified_citations, fallback_citations)
        processed_text = self.replace_citation_markers(text, citation_url_map)
        
        # Generate and append sources section
        sources_section = self.generate_sources_section(
            unified_citations, search_sources, successful_sources, failure_note
        )
        
        return processed_text + sources_section


# Global instance for easy import
citation_processor = CitationProcessor()