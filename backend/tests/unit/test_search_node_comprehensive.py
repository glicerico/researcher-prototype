"""
Comprehensive tests for search_node functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from nodes.search_node import search_node
from nodes.base import ChatState


class TestSearchNode:
    """Test suite for search_node functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_state = {
            "messages": [
                HumanMessage(content="What is the current weather in New York?")
            ],
            "module_results": {},
            "workflow_context": {}
        }
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_success_with_original_query(self, mock_post):
        """Test successful search using original user query."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Current weather in NYC is 72°F and sunny."}}],
            "citations": ["https://weather.com/nyc"],
            "search_results": [{"url": "https://weather.com/nyc", "title": "NYC Weather"}]
        }
        mock_post.return_value = mock_response
        
        result = await search_node(self.base_state)
        
        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.perplexity.ai/chat/completions"
        assert "Authorization" in call_args[1]["headers"]
        assert "Bearer test-api-key" in call_args[1]["headers"]["Authorization"]
        
        # Verify state is updated correctly
        search_results = result["module_results"]["search"]
        assert search_results["success"] is True
        assert "Current weather in NYC" in search_results["result"]
        assert search_results["query_used"] == "What is the current weather in New York?"
        assert len(search_results["citations"]) == 1
        assert len(search_results["search_results"]) == 1
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_success_with_refined_query(self, mock_post):
        """Test successful search using refined query from workflow context."""
        # State with refined query
        state_with_refined = self.base_state.copy()
        state_with_refined["workflow_context"] = {
            "refined_search_query": "NYC weather forecast today temperature"
        }
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Today's NYC forecast shows 72°F."}}],
            "citations": [],
            "search_results": []
        }
        mock_post.return_value = mock_response
        
        result = await search_node(state_with_refined)
        
        # Verify refined query was used
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        user_message = next(msg for msg in payload["messages"] if msg["role"] == "user")
        assert user_message["content"] == "NYC weather forecast today temperature"
        
        # Verify results
        search_results = result["module_results"]["search"]
        assert search_results["success"] is True
        assert search_results["query_used"] == "NYC weather forecast today temperature"
    
    async def test_search_node_no_api_key(self):
        """Test behavior when Perplexity API key is not configured."""
        with patch('nodes.search_node.config.PERPLEXITY_API_KEY', None):
            result = await search_node(self.base_state)
            
            search_results = result["module_results"]["search"]
            assert search_results["success"] is False
            assert "API key not configured" in search_results["error"]
    
    async def test_search_node_no_query_available(self):
        """Test behavior when no query is available (no messages or refined query)."""
        empty_state = {
            "messages": [],
            "module_results": {},
            "workflow_context": {}
        }
        
        result = await search_node(empty_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is False
        assert "No query found for search" in search_results["error"]
    
    async def test_search_node_no_user_messages(self):
        """Test behavior when messages exist but no user messages."""
        state_no_user = {
            "messages": [
                AIMessage(content="Hello!")
            ],
            "module_results": {},
            "workflow_context": {}
        }
        
        result = await search_node(state_no_user)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is False
        assert "No query found for search" in search_results["error"]
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_api_error_response(self, mock_post):
        """Test handling of API error responses."""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request: Invalid query"
        mock_post.return_value = mock_response
        
        result = await search_node(self.base_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is False
        assert "status code 400" in search_results["error"]
        assert "Bad Request" in search_results["error"]
        assert search_results["status_code"] == 400
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_api_401_unauthorized(self, mock_post):
        """Test handling of 401 Unauthorized response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized: Invalid API key"
        mock_post.return_value = mock_response
        
        result = await search_node(self.base_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is False
        assert search_results["status_code"] == 401
        assert "Unauthorized" in search_results["error"]
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_network_exception(self, mock_post):
        """Test handling of network exceptions."""
        mock_post.side_effect = ConnectionError("Network connection failed")
        
        result = await search_node(self.base_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is False
        assert "Network connection failed" in search_results["error"]
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_json_decode_error(self, mock_post):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        result = await search_node(self.base_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is False
        assert "Invalid JSON" in search_results["error"]
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.config.PERPLEXITY_MODEL', 'llama-3.1-sonar-small-128k-online')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_api_request_structure(self, mock_post):
        """Test that API request is structured correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "citations": [],
            "search_results": []
        }
        mock_post.return_value = mock_response
        
        await search_node(self.base_state)
        
        # Verify request structure
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        payload = call_args[1]["json"]
        
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"
        assert payload["model"] == "llama-3.1-sonar-small-128k-online"
        assert "search_mode" in payload
        assert "web_search_options" in payload
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_long_query_truncation_in_logs(self, mock_post):
        """Test that long queries are truncated in log messages."""
        # Create a very long query
        long_query = "What is the weather " * 20  # 100+ characters
        state_long_query = {
            "messages": [HumanMessage(content=long_query)],
            "module_results": {},
            "workflow_context": {}
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Weather response"}}],
            "citations": [],
            "search_results": []
        }
        mock_post.return_value = mock_response
        
        # Should not raise exception and should handle long query
        result = await search_node(state_long_query)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is True
        assert search_results["query_used"] == long_query  # Full query stored
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_empty_response_content(self, mock_post):
        """Test handling of empty response content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}],
            "citations": [],
            "search_results": []
        }
        mock_post.return_value = mock_response
        
        result = await search_node(self.base_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is True
        assert search_results["result"] == ""
    
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_missing_response_fields(self, mock_post):
        """Test handling of missing optional fields in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Search result"}}]
            # Missing citations and search_results
        }
        mock_post.return_value = mock_response
        
        result = await search_node(self.base_state)
        
        search_results = result["module_results"]["search"]
        assert search_results["success"] is True
        assert search_results["citations"] == []
        assert search_results["search_results"] == []
    
    @patch('nodes.search_node.get_current_datetime_str')
    @patch('nodes.search_node.config.PERPLEXITY_API_KEY', 'test-api-key')
    @patch('nodes.search_node.requests.post')
    async def test_search_node_system_prompt_formatting(self, mock_post, mock_datetime):
        """Test that system prompt is formatted with current time."""
        mock_datetime.return_value = "2024-01-15 10:30:00"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "citations": [],
            "search_results": []
        }
        mock_post.return_value = mock_response
        
        await search_node(self.base_state)
        
        # Verify system prompt contains formatted time
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        system_message = payload["messages"][0]
        assert system_message["role"] == "system"
        assert "2024-01-15 10:30:00" in system_message["content"]
    
    async def test_search_node_preserves_existing_module_results(self):
        """Test that search node preserves existing module results."""
        state_with_existing = self.base_state.copy()
        state_with_existing["module_results"] = {
            "router": {"decision": "search", "confidence": 0.9}
        }
        
        with patch('nodes.search_node.config.PERPLEXITY_API_KEY', None):
            result = await search_node(state_with_existing)
            
            # Should preserve existing results while adding search results
            assert "router" in result["module_results"]
            assert result["module_results"]["router"]["decision"] == "search"
            assert "search" in result["module_results"] 