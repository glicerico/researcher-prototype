# Multi-API Search Implementation

## Overview

The researcher prototype now supports multiple specialized search APIs in addition to Perplexity:

- **Semantic Scholar** - Academic research papers (free)
- **Reddit** - Community discussions and social sentiment (free tier available)
- **PubMed** - Medical and biomedical research (free)
- **Perplexity** - General web search (existing)

## New Routing Options

The router now supports these search types:

1. **search** - General web search via Perplexity (existing)
2. **academic_search** - Academic papers via Semantic Scholar
3. **social_search** - Community discussions via Reddit
4. **medical_search** - Medical research via PubMed
5. **chat** - General conversation (existing)
6. **analyzer** - Data analysis (existing)

## Configuration

### Required Environment Variables

Add these to your `.env` file:

```bash
# Reddit API (optional - for social search)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=ResearcherPrototype:1.0 (by /u/your_reddit_username)

# PubMed (optional - email recommended)
PUBMED_EMAIL=your_email@example.com
```

### Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Choose "script" type
4. Note the client ID (under app name) and client secret
5. Add these to your `.env` file

### Cost Considerations

- **Semantic Scholar**: Free (no API key required)
- **PubMed**: Free (no API key required, email recommended)
- **Reddit**: Free up to 100 queries per minute, then $0.24/1000 requests

## Usage Examples

The router automatically selects the appropriate search source based on query content:

### Academic Research
```
User: "Find research papers on machine learning"
→ Routes to: academic_search (Semantic Scholar)
```

### Medical Research
```
User: "Medical studies on diabetes treatment"
→ Routes to: medical_search (PubMed)
```

### Social Sentiment
```
User: "What do people think about the new iPhone?"
→ Routes to: social_search (Reddit)
```

### General Web Search
```
User: "What happened in the news today?"
→ Routes to: search (Perplexity)
```

## Scope Filters

The router also sets scope filters that affect search behavior:

- **recent**: Focus on recent information (last 1-3 years)
- **academic**: Prefer academic/scholarly sources
- **medical**: Medical/health-related content
- **social**: Community discussions and public opinion

## Integration

The system integrates results from multiple sources when appropriate. For example, a query about "Tesla stock analysis" might use:

1. Perplexity for general market information
2. Reddit for community sentiment
3. Academic sources for financial research papers

## Testing

Test individual search nodes:

```bash
# Test Semantic Scholar
python -c "
import asyncio
from nodes.semantic_scholar_node import SemanticScholarSearchNode
node = SemanticScholarSearchNode()
asyncio.run(node.search('your query here', limit=3))
"

# Test Reddit (requires API keys)
python -c "
import asyncio
from nodes.reddit_search_node import RedditSearchNode
node = RedditSearchNode()
asyncio.run(node.search('your query here', limit=5))
"

# Test PubMed
python -c "
import asyncio
from nodes.pubmed_search_node import PubMedSearchNode
node = PubMedSearchNode()
asyncio.run(node.search('your medical query here', limit=3))
"
```

## Performance

- **Semantic Scholar**: ~2-3 seconds per query
- **Reddit**: ~1-2 seconds per query (requires OAuth)
- **PubMed**: ~3-5 seconds per query (XML parsing required)
- **Perplexity**: ~2-4 seconds per query (existing)

## Error Handling

Each search node gracefully handles:
- API unavailability (falls back to other sources)
- Rate limiting
- Network timeouts
- Invalid responses

The integrator combines results from successful sources and notes any failures in logs.