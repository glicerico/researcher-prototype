# Services

This directory contains business logic and services that are used by the API endpoints. It helps to separate concerns and keeps the API layer thin.

## Key Services

### `motivation.py` - Intelligent Motivation System
Hierarchical motivation system for autonomous research scheduling:

**Global Motivation (`MotivationSystem`)**:
- Tracks global drives: boredom, curiosity, tiredness, satisfaction
- Gates overall research activity with `should_research()` method
- Prevents unnecessary resource usage when system should rest

**Per-Topic Motivation**:
- `evaluate_topics(user_id, topics)` - Returns prioritized list of topics to research
- `should_research_topic(user_id, topic)` - Evaluates individual topics
- Factors: staleness pressure, user engagement, research success rate
- Staleness coefficients: LLM-assessed values (0.1=stable, 2.0=urgent)

**Integration**:
- Uses PersonalizationManager for user engagement data
- Configurable via environment variables (see CLAUDE.md)
- Called by autonomous_research_engine for intelligent topic selection

### `autonomous_research_engine.py` - Research Orchestration
LangGraph-based autonomous research engine that uses the motivation system to intelligently schedule background research on user topics. 