"""
Comprehensive tests for research_storage_node functionality.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from nodes.research_storage_node import research_storage_node
from nodes.base import ChatState


class TestResearchStorageNode:
    """Test suite for research_storage_node functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_state = {
            "module_results": {
                "search": {
                    "success": True,
                    "result": "Comprehensive research findings about climate change impacts on agriculture."
                },
                "research_quality_assessor": {
                    "success": True,
                    "quality_assessment": {
                        "key_insights": ["Global warming affects crop yields", "Adaptation strategies needed"],
                        "findings_summary": "Climate change significantly impacts agriculture globally",
                        "source_urls": ["https://climate.gov", "https://agriculture.org"]
                    },
                    "overall_quality_score": 0.85
                },
                "research_deduplication": {
                    "is_duplicate": False,
                    "similarity_score": 0.2
                }
            },
            "workflow_context": {
                "research_metadata": {
                    "topic_name": "Climate Change Agriculture",
                    "user_id": "test_user_123"
                },
                "refined_search_query": "climate change agriculture impacts 2024"
            }
        }
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_success_high_quality(self, mock_research_manager):
        """Test successful storage of high-quality research findings."""
        # Mock successful storage
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(self.base_state)
        
        # Verify research manager was called correctly
        mock_research_manager.store_research_finding.assert_called_once()
        call_args = mock_research_manager.store_research_finding.call_args[0]
        user_id, topic_name, finding = call_args
        
        assert user_id == "test_user_123"
        assert topic_name == "Climate Change Agriculture"
        assert finding["findings_content"] == "Comprehensive research findings about climate change impacts on agriculture."
        assert finding["quality_score"] == 0.85
        assert finding["research_query"] == "climate change agriculture impacts 2024"
        assert len(finding["key_insights"]) == 2
        assert len(finding["source_urls"]) == 2
        
        # Verify update_topic_last_researched called
        mock_research_manager.update_topic_last_researched.assert_called()
        
        # Verify result
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is True
        assert storage_results["stored"] is True
        assert storage_results["quality_score"] == 0.85
        assert storage_results["insights_count"] == 2
        assert storage_results["topic_updated"] is True
        assert "finding_id" in storage_results
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.9)
    def test_research_storage_quality_below_threshold(self, mock_research_manager):
        """Test behavior when quality score is below threshold."""
        # Quality score is 0.85, threshold is 0.9
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(self.base_state)
        
        # Should not store finding but should update topic
        mock_research_manager.store_research_finding.assert_not_called()
        mock_research_manager.update_topic_last_researched.assert_called_once_with(
            "test_user_123", "Climate Change Agriculture"
        )
        
        # Verify result
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is True
        assert storage_results["stored"] is False
        assert storage_results["reason"] == "Quality below threshold"
        assert storage_results["quality_score"] == 0.85
        assert storage_results["quality_threshold"] == 0.9
        assert storage_results["topic_updated"] is True
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_duplicate_findings(self, mock_research_manager):
        """Test behavior when findings are duplicates."""
        # Set duplicate flag
        state_with_duplicate = self.base_state.copy()
        state_with_duplicate["module_results"]["research_deduplication"] = {
            "is_duplicate": True,
            "similarity_score": 0.9
        }
        
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(state_with_duplicate)
        
        # Should not store finding but should update topic
        mock_research_manager.store_research_finding.assert_not_called()
        mock_research_manager.update_topic_last_researched.assert_called_once()
        
        # Verify result
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is True
        assert storage_results["stored"] is False
        assert storage_results["reason"] == "Duplicate findings"
        assert storage_results["similarity_score"] == 0.9
        assert storage_results["topic_updated"] is True
    
    def test_research_storage_no_search_results(self):
        """Test behavior when search results are not available."""
        state_no_search = self.base_state.copy()
        state_no_search["module_results"]["search"] = {"success": False}
        
        result = research_storage_node(state_no_search)
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is False
        assert storage_results["stored"] is False
        assert "No successful search results" in storage_results["error"]
    
    def test_research_storage_no_quality_assessment(self):
        """Test behavior when quality assessment is not available."""
        state_no_quality = self.base_state.copy()
        state_no_quality["module_results"]["research_quality_assessor"] = {"success": False}
        
        result = research_storage_node(state_no_quality)
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is False
        assert storage_results["stored"] is False
        assert "No successful quality assessment" in storage_results["error"]
    
    def test_research_storage_missing_search_module(self):
        """Test behavior when search module results are missing entirely."""
        state_missing_search = self.base_state.copy()
        del state_missing_search["module_results"]["search"]
        
        result = research_storage_node(state_missing_search)
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is False
        assert storage_results["stored"] is False
    
    def test_research_storage_missing_quality_module(self):
        """Test behavior when quality assessment module results are missing entirely."""
        state_missing_quality = self.base_state.copy()
        del state_missing_quality["module_results"]["research_quality_assessor"]
        
        result = research_storage_node(state_missing_quality)
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is False
        assert storage_results["stored"] is False
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_manager_storage_failure(self, mock_research_manager):
        """Test behavior when research manager fails to store finding."""
        mock_research_manager.store_research_finding.return_value = False
        
        result = research_storage_node(self.base_state)
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is False
        assert storage_results["stored"] is False
        assert "Failed to store research finding" in storage_results["error"]
        assert storage_results["quality_score"] == 0.85
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_exception_handling(self, mock_research_manager):
        """Test exception handling during storage process."""
        mock_research_manager.store_research_finding.side_effect = Exception("Database connection failed")
        
        result = research_storage_node(self.base_state)
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is False
        assert storage_results["stored"] is False
        assert "Database connection failed" in storage_results["error"]
        assert storage_results["quality_score"] == 0.85
    
    def test_research_storage_missing_research_metadata(self):
        """Test behavior when research metadata is missing."""
        state_no_metadata = self.base_state.copy()
        state_no_metadata["workflow_context"] = {}
        
        result = research_storage_node(state_no_metadata)
        
        # Should use default values for missing metadata
        storage_results = result["module_results"]["research_storage"]
        # Should fail because no search results due to missing metadata, but let's check the logic
        assert "research_storage" in result["module_results"]
    
    def test_research_storage_partial_research_metadata(self):
        """Test behavior with partial research metadata."""
        state_partial_metadata = self.base_state.copy()
        state_partial_metadata["workflow_context"]["research_metadata"] = {
            "topic_name": "Test Topic"
            # Missing user_id
        }
        
        # Should use default user_id
        result = research_storage_node(state_partial_metadata)
        
        # The function should handle missing user_id with default value
        assert "research_storage" in result["module_results"]
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_missing_deduplication_results(self, mock_research_manager):
        """Test behavior when deduplication results are missing."""
        state_no_dedup = self.base_state.copy()
        del state_no_dedup["module_results"]["research_deduplication"]
        
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(state_no_dedup)
        
        # Should proceed with storage (assuming not duplicate when dedup missing)
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is True
        assert storage_results["stored"] is True
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_empty_quality_assessment(self, mock_research_manager):
        """Test behavior with empty quality assessment data."""
        state_empty_quality = self.base_state.copy()
        state_empty_quality["module_results"]["research_quality_assessor"] = {
            "success": True,
            "quality_assessment": {},  # Empty assessment
            "overall_quality_score": 0.8
        }
        
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(state_empty_quality)
        
        # Should handle empty assessment gracefully
        mock_research_manager.store_research_finding.assert_called_once()
        call_args = mock_research_manager.store_research_finding.call_args[0]
        finding = call_args[2]
        
        assert finding["key_insights"] == []
        assert finding["source_urls"] == []
        assert finding["findings_summary"] == ""
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is True
        assert storage_results["stored"] is True
        assert storage_results["insights_count"] == 0
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_missing_refined_query(self, mock_research_manager):
        """Test behavior when refined search query is missing."""
        state_no_query = self.base_state.copy()
        del state_no_query["workflow_context"]["refined_search_query"]
        
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(state_no_query)
        
        # Should use empty query when missing
        call_args = mock_research_manager.store_research_finding.call_args[0]
        finding = call_args[2]
        assert finding["research_query"] == ""
        
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["success"] is True
        assert storage_results["stored"] is True
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    @patch('time.time')
    def test_research_storage_timing_consistency(self, mock_time, mock_research_manager):
        """Test that timing is consistent between finding storage and topic update."""
        mock_time.return_value = 1640995200.0  # Fixed timestamp
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(self.base_state)
        
        # Verify both calls use the same timestamp
        store_call = mock_research_manager.store_research_finding.call_args[0]
        finding = store_call[2]
        assert finding["research_time"] == 1640995200.0
        
        update_call = mock_research_manager.update_topic_last_researched.call_args
        assert update_call[0][2] == 1640995200.0  # Third argument is timestamp
        
        storage_results = result["module_results"]["research_storage"]
        assert "1640995200" in storage_results["finding_id"]
    
    @patch('nodes.research_storage_node.research_manager')
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_content_length_calculation(self, mock_research_manager):
        """Test that content length is calculated correctly."""
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(self.base_state)
        
        expected_length = len("Comprehensive research findings about climate change impacts on agriculture.")
        storage_results = result["module_results"]["research_storage"]
        assert storage_results["content_length"] == expected_length
    
    @patch('nodes.research_storage_node.research_manager')  
    @patch('nodes.research_storage_node.config.RESEARCH_QUALITY_THRESHOLD', 0.7)
    def test_research_storage_preserves_existing_module_results(self, mock_research_manager):
        """Test that storage node preserves existing module results."""
        state_with_existing = self.base_state.copy()
        state_with_existing["module_results"]["router"] = {"decision": "research", "confidence": 0.9}
        
        mock_research_manager.store_research_finding.return_value = True
        mock_research_manager.update_topic_last_researched.return_value = True
        
        result = research_storage_node(state_with_existing)
        
        # Should preserve existing results
        assert "router" in result["module_results"]
        assert result["module_results"]["router"]["decision"] == "research"
        assert "research_storage" in result["module_results"] 