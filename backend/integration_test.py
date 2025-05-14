# integration_test.py
import os
import unittest
from graph_builder import create_chat_graph

class IntegrationTest(unittest.TestCase):
    def test_openai_integration(self):
        # Skip if no API key is set
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("No OpenAI API key found")
        
        # Create a test state
        state = {
            "messages": [
                {"role": "user", "content": "Say 'This is a test' and nothing else"}
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.0,  # Use 0 for deterministic results
            "max_tokens": 20
        }
        
        # Create the graph
        graph = create_chat_graph()
        
        # Run the graph with the real API
        result = graph.invoke(state)
        
        # Check the result
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 2)
        self.assertEqual(result["messages"][1]["role"], "assistant")
        print(f"API Response: {result['messages'][1]['content']}")

if __name__ == "__main__":
    unittest.main()
