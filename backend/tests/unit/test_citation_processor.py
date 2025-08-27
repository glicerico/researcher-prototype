import pytest
from services.citation_processor import CitationProcessor


class TestCitationProcessor:
    """Test cases for the citation processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = CitationProcessor()
        
        self.sample_unified_citations = [
            {
                "title": "Academic Paper on AI",
                "url": "https://example.com/paper1",
                "type": "academic",
                "authors": [{"name": "John Doe"}, {"name": "Jane Smith"}],
                "year": "2024",
                "venue": "AI Conference"
            },
            {
                "title": "Clinical Study",
                "url": "https://example.com/clinical1",
                "type": "clinical",
                "authors": [{"name": "Dr. Smith"}],
                "journal": "Medical Journal",
                "pubdate": "2024-01-15"
            },
            {
                "title": "Reddit Discussion",
                "url": "https://reddit.com/discussion1",
                "type": "sentiment",
                "author": "user123",
                "points": "150",
                "comments": "45"
            },
            {
                "title": "Web Article",
                "url": "https://example.com/article1",
                "type": "web"
            }
        ]
    
    def test_create_citation_url_map_with_unified_citations(self):
        """Test URL map creation with unified citations."""
        result = self.processor.create_citation_url_map(self.sample_unified_citations, [])
        expected = {
            1: "https://example.com/paper1",
            2: "https://example.com/clinical1", 
            3: "https://reddit.com/discussion1",
            4: "https://example.com/article1"
        }
        assert result == expected
    
    def test_create_citation_url_map_with_fallback(self):
        """Test URL map creation with fallback citations."""
        fallback_urls = ["https://fallback1.com", "https://fallback2.com"]
        result = self.processor.create_citation_url_map([], fallback_urls)
        expected = {1: "https://fallback1.com", 2: "https://fallback2.com"}
        assert result == expected
    
    def test_replace_citation_markers(self):
        """Test citation marker replacement."""
        text = "This is a finding [1] and another [2] with no match [3]."
        url_map = {1: "https://example.com/1", 2: "https://example.com/2"}
        
        result = self.processor.replace_citation_markers(text, url_map)
        expected = "This is a finding [[1]](https://example.com/1) and another [[2]](https://example.com/2) with no match [3]."
        assert result == expected
    
    def test_replace_citation_markers_double_bracket_prevention(self):
        """Test that double brackets are not re-wrapped."""
        text = "Already double [[1]] and single [2]."
        url_map = {1: "https://example.com/1", 2: "https://example.com/2"}
        
        result = self.processor.replace_citation_markers(text, url_map)
        expected = "Already double [[1]](https://example.com/1) and single [[2]](https://example.com/2)."
        assert result == expected
    
    def test_replace_citation_markers_mixed_scenarios(self):
        """Test mixed citation bracketing scenarios."""
        text = "Mix [1] and [[2]] and [3]."
        url_map = {1: "https://example.com/1", 2: "https://example.com/2", 3: "https://example.com/3"}
        
        result = self.processor.replace_citation_markers(text, url_map)
        expected = "Mix [[1]](https://example.com/1) and [[2]](https://example.com/2) and [[3]](https://example.com/3)."
        assert result == expected
    
    def test_replace_citation_markers_adjacent_citations(self):
        """Test adjacent citations are handled correctly."""
        text = "[1][2][[3]]"
        url_map = {1: "https://example.com/1", 2: "https://example.com/2", 3: "https://example.com/3"}
        
        result = self.processor.replace_citation_markers(text, url_map)
        expected = "[[1]](https://example.com/1)[[2]](https://example.com/2)[[3]](https://example.com/3)"
        assert result == expected
    
    def test_format_academic_citation(self):
        """Test academic citation formatting."""
        citation = self.sample_unified_citations[0]
        result = self.processor._format_academic_citation(citation, 1)
        assert "[1]. [Academic Paper on AI](https://example.com/paper1)" in result
        assert "Authors: John Doe, Jane Smith" in result
        assert "Year: 2024" in result
        assert "Venue: AI Conference" in result
    
    def test_format_clinical_citation(self):
        """Test clinical citation formatting."""
        citation = self.sample_unified_citations[1]
        result = self.processor._format_clinical_citation(citation, 2)
        assert "[2]. [Clinical Study](https://example.com/clinical1)" in result
        assert "Authors: Dr. Smith" in result
        assert "Journal: Medical Journal" in result
        assert "Published: 2024-01-15" in result
    
    def test_format_social_citation(self):
        """Test social media citation formatting."""
        citation = self.sample_unified_citations[2]
        result = self.processor._format_social_citation(citation, 3)
        assert "[3]. [Reddit Discussion](https://reddit.com/discussion1)" in result
        assert "Author: user123" in result
        assert "Points: 150" in result
        assert "Comments: 45" in result
    
    def test_format_web_citation(self):
        """Test web citation formatting."""
        citation = self.sample_unified_citations[3]
        result = self.processor._format_web_citation(citation, 4)
        assert result == "[4]. [Web Article](https://example.com/article1)"
    
    def test_group_citations_by_type(self):
        """Test citation grouping by type."""
        web, academic, social, medical = self.processor._group_citations_by_type(self.sample_unified_citations)
        
        assert len(web) == 1
        assert len(academic) == 1
        assert len(social) == 1
        assert len(medical) == 1
        
        assert "Web Article" in web[0]
        assert "Academic Paper on AI" in academic[0]
        assert "Reddit Discussion" in social[0]
        assert "Clinical Study" in medical[0]
    
    def test_generate_sources_section_with_unified_citations(self):
        """Test sources section generation with unified citations."""
        successful_sources = [{"name": "Academic"}, {"name": "Web"}]
        
        result = self.processor.generate_sources_section(
            self.sample_unified_citations, [], successful_sources, ""
        )
        
        assert "Information synthesized from 2 sources" in result
        assert "**Web Search:**" in result
        assert "**Academic Papers:**" in result
        assert "**Social Media:**" in result
        assert "**Medical Research:**" in result
    
    def test_generate_sources_section_with_fallback(self):
        """Test sources section generation with fallback sources."""
        search_sources = [
            {"title": "Fallback Article", "url": "https://fallback.com"}
        ]
        
        result = self.processor.generate_sources_section(
            [], search_sources, [], ""
        )
        
        assert "**Sources:**" in result
        assert "[1]. [Fallback Article](https://fallback.com)" in result
    
    def test_generate_sources_section_with_failure_note(self):
        """Test sources section with failure note."""
        result = self.processor.generate_sources_section(
            [], [], [], "Some sources failed to load"
        )
        
        assert "*Some sources failed to load*" in result
    
    def test_generate_sources_section_empty(self):
        """Test sources section generation with no sources."""
        result = self.processor.generate_sources_section([], [], [], "")
        assert result == ""
    
    def test_process_citations_complete(self):
        """Test complete citation processing."""
        text = "Research shows [1] and studies indicate [2]."
        successful_sources = [{"name": "Academic"}, {"name": "Web"}]
        
        result = self.processor.process_citations(
            text, self.sample_unified_citations, [], [], successful_sources, ""
        )
        
        # Check that citation markers are replaced
        assert "[[1]]" in result
        assert "[[2]]" in result
        
        # Check that sources section is appended
        assert "**Sources:**" in result
        assert "**Academic Papers:**" in result
        assert "Information synthesized from 2 sources" in result
    
    def test_process_citations_with_fallback(self):
        """Test citation processing with fallback citations."""
        text = "Finding [1] shows results."
        fallback_citations = ["https://fallback.com"]
        
        result = self.processor.process_citations(
            text, [], fallback_citations, [], [], ""
        )
        
        assert "[[1]](https://fallback.com)" in result
    
    def test_unknown_citation_type_warning(self, caplog):
        """Test warning for unknown citation types."""
        unknown_citation = [{
            "title": "Unknown Source",
            "url": "https://unknown.com",
            "type": "unknown_type"
        }]
        
        self.processor._group_citations_by_type(unknown_citation)
        
        assert "Unknown citation type 'unknown_type'" in caplog.text