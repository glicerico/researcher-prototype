# Zep Manual Integration Test

This script allows manual testing of Zep knowledge graph search functionality to debug topic expansion issues.

## Setup

1. Ensure Zep is configured in your `.env`:
```bash
ZEP_ENABLED=true
ZEP_API_KEY=your_zep_api_key_here
```

2. Run from the backend directory with virtual environment activated:
```bash
cd backend
source venv/bin/activate
```

## Usage Examples

### Test Knowledge Graph Search
```bash
# Test a specific user and query
python tests/integration/test_zep_manual.py --user fine-calf-52 --query "Alzheimer treatments"

# Test with verbose output (shows raw JSON)
python tests/integration/test_zep_manual.py --user guest --query "machine learning" --verbose

# Search only nodes or edges
python tests/integration/test_zep_manual.py --user test-user --query "AI" --scope nodes
python tests/integration/test_zep_manual.py --user test-user --query "AI" --scope edges

# Increase result limit
python tests/integration/test_zep_manual.py --user guest --query "technology" --limit 20
```

### Test Conversation Storage
```bash
# Store a test conversation and check for immediate graph data
python tests/integration/test_zep_manual.py --user new-test-user --store-test-conversation

# Combine conversation storage with search test
python tests/integration/test_zep_manual.py --user new-test-user --store-test-conversation --query "artificial intelligence"
```

## Understanding Results

### No Results Found
This is normal and expected when:
- User has no conversation data in Zep
- Knowledge graph processing hasn't completed yet (can take minutes to hours)
- Query doesn't match extracted entities/relationships

### Results Found
When you see nodes and edges, it means:
- ✅ User has conversation data in Zep
- ✅ Knowledge graph has been processed
- ✅ Topic expansion should work for this user

## Debugging Topic Expansion Issues

1. **Test the exact user from your logs:**
```bash
python tests/integration/test_zep_manual.py --user fine-calf-52 --query "Recent Advances in Alzheimer's Treatments"
```

2. **Try simpler queries:**
```bash
python tests/integration/test_zep_manual.py --user fine-calf-52 --query "Alzheimer"
python tests/integration/test_zep_manual.py --user fine-calf-52 --query "treatments"
```

3. **Test conversation storage:**
```bash
python tests/integration/test_zep_manual.py --user fine-calf-52 --store-test-conversation
```

4. **Check with verbose output:**
```bash
python tests/integration/test_zep_manual.py --user fine-calf-52 --query "test" --verbose
```

## Expected Workflow

1. **New User**: No graph data initially
2. **After Conversations**: Still no immediate graph data
3. **After Processing Time**: Graph data appears (entities and relationships extracted)
4. **Topic Expansion Works**: Once graph data exists

## Command Line Options

- `--user, -u`: User ID to test (required)
- `--query, -q`: Search query to test
- `--scope, -s`: Search scope (nodes, edges, both)
- `--limit, -l`: Maximum results (default: 10)
- `--reranker, -r`: Reranker type (default: cross_encoder)
- `--verbose, -v`: Show detailed output including raw JSON
- `--store-test-conversation`: Store test conversation and check for graph data

## Troubleshooting

### "Zep is not enabled"
- Check `ZEP_ENABLED=true` in `.env`
- Verify `ZEP_API_KEY` is set

### "ModuleNotFoundError"
- Run from backend directory: `cd backend`
- Activate virtual environment: `source venv/bin/activate`

### Connection Errors
- Verify ZEP_API_KEY is valid
- Check network connectivity to Zep Cloud
