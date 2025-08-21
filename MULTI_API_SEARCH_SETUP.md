# Multi-API Search Implementation

## Overview

The researcher prototype now supports multiple specialized search APIs in addition to Perplexity:

- **Semantic Scholar** - Academic research papers (free)
- **Hacker News** - Community discussions and social sentiment (free)
- **PubMed** - Medical and biomedical research (free)
- **Perplexity** - General web search (existing)

## New Routing Options

The router now supports these search types:

1. **search** - General web search via Perplexity (existing)
2. **academic_search** - Academic papers via Semantic Scholar
3. **social_search** - Community discussions via Hacker News
4. **medical_search** - Medical research via PubMed
5. **chat** - General conversation (existing)
6. **analyzer** - Data analysis (existing)

## Configuration

### Required Environment Variables

Add these to your `.env` file:

```bash
# PubMed (optional - email recommended)
PUBMED_EMAIL=your_email@example.com
```

### Hacker News Setup

No setup required. We use the public Algolia HN Search API.

### Cost Considerations

- **Semantic Scholar**: Free (no API key required)
- **PubMed**: Free (no API key required, email recommended)
- **Hacker News**: Free

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
→ Routes to: social_search (Hacker News)
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
2. Hacker News for community sentiment
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

# Test Hacker News
python -c "
import asyncio
from nodes.hacker_news_search_node import HackerNewsSearchNode
node = HackerNewsSearchNode()
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
- **Hacker News**: ~0.5-1.0 seconds per query
- **PubMed**: ~3-5 seconds per query (XML parsing required)
- **Perplexity**: ~2-4 seconds per query (existing)

## Error Handling

Each search node gracefully handles:
- API unavailability (falls back to other sources)
- Rate limiting
- Network timeouts
- Invalid responses

The integrator combines results from successful sources and notes any failures in logs.