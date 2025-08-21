# Automated Tests

This folder contains all the automated tests for the backend, separated into `unit/` and `integration/` tests to ensure the code is working correctly.

## Structure

- **`unit/`** - Unit tests for individual modules and functions
- **`integration/`** - Integration tests including external API testing

## Notable Integration Tests

- **`test_search_apis.py`** - Direct testing of external search APIs (Semantic Scholar, PubMed, Hacker News)
  ```bash
  # Test all APIs
  python tests/integration/test_search_apis.py --all --query "your query"
  
  # Test specific API
  python tests/integration/test_search_apis.py --semantic-scholar --query "machine learning" --limit 5
  ```

- **`test_openai_integration.py`** - OpenAI API integration tests 