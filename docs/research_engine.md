# Autonomous Research Engine

The **autonomous research engine** runs in the background, gathering high-quality information on the topics you mark as interesting.  It does not block normal chat usage and can be turned on/off at any time.

## Why?

• Free the user from manual searching.  
• Surface fresh, credible insights.  
• Keep the assistant's knowledge up-to-date.

## How it Works

1. **Topic discovery** – after each chat message the `topic_extractor_node` suggests candidate topics.  
2. **Subscription** – the UI lets you enable research per topic; selected topics are persisted in `storage_data/`.
3. **Motivation model** – internal boredom / curiosity / tiredness / satisfaction drives decide when to launch a research cycle (default every ~2 h on average).  You can tweak rates & threshold via environment variables or debug APIs.
4. **Graph workflow** – the research LangGraph (`research_graph_builder.py`) runs: initialization ➜ query generation ➜ source selection ➜ multi-source search coordination ➜ integration ➜ quality scoring ➜ deduplication ➜ storage.
5. **Review** – findings appear in the sidebar with summary, quality bars & source links.

## Multi-Source Search Architecture

The system uses an intelligent multi-source analyzer that replaces the previous single-choice router:

### Intent Classification
The `multi_source_analyzer_node` classifies user queries into three intents:
- **chat**: General conversation, greetings, simple questions
- **search**: Information gathering requiring external sources  
- **analysis**: Deep analysis tasks using the analyzer node

### Source Selection (Search Intent)
For search queries, the system automatically selects up to 3 relevant sources:
- **Web Search** (`search`): Current information, news, general topics
- **Academic Search** (`academic_search`): Scholarly articles via Semantic Scholar
- **Social Search** (`social_search`): Community discussions via Hacker News API
- **Medical Search** (`medical_search`): Medical literature via PubMed

### Parallel Execution
The `source_coordinator_node` executes selected search sources concurrently using LangGraph's fan-out/fan-in pattern, then the `integrator_node` synthesizes results from all successful sources while gracefully handling any failures.

## Autonomous Research Multi-Source Flow

The autonomous research engine now leverages the same multi-source capabilities as the chat system:

### Research-Specific Source Selection
1. **Research Source Selector** (`research_source_selector_node`): Analyzes research topics to select the most appropriate sources
   - **Scientific/Technical Topics**: Academic + Web sources
   - **Medical/Health Topics**: Medical + Academic sources  
   - **Technology/Startup Topics**: Web + Social sources
   - **Current Events**: Web + Social sources
   - **Academic Fields**: Academic + Medical (if health-related)

### Enhanced Research Workflow
```
Research Topic → Query Generation → Source Selection → Multi-Source Search → Integration → Quality Assessment → Deduplication → Storage
```

### Benefits for Autonomous Research
- **Comprehensive Coverage**: Multiple perspectives on each research topic
- **Source Diversity**: Academic rigor combined with current developments
- **Parallel Efficiency**: All sources searched simultaneously
- **Quality Filtering**: Results assessed across multiple source types
- **Automatic Relevance**: Sources selected based on topic characteristics

## Motivation System Mechanics

The research engine uses a drive-based motivation system where **boredom** and **curiosity** accumulate over time, while **tiredness** and **satisfaction** act as inhibitors during research.

### Drive Equations

The motivation level is calculated as:
```
motivation = (boredom + curiosity) - (tiredness + satisfaction)
```

**Research triggers when**: `motivation ≥ MOTIVATION_THRESHOLD`

#### Drive Updates Over Time

| Drive | When Active | Update Formula |
|-------|-------------|----------------|
| **Boredom** | Always (idle) | `boredom += BOREDOM_RATE × time_delta` |
| **Curiosity** | Always | `curiosity -= CURIOSITY_DECAY × time_delta` |
| **Tiredness** | During research | `tiredness += time_delta` then `tiredness -= TIREDNESS_DECAY × time_delta` |
| **Satisfaction** | After research | `satisfaction += quality_score` then `satisfaction -= SATISFACTION_DECAY × time_delta` |

### Visual Flow Diagram

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Motivated : "motivation ≥ threshold<br/>(boredom + curiosity) > (tiredness + satisfaction)"
    Motivated --> Researching : "spawns research cycle"
    Researching --> Idle : "research complete<br/>satisfaction ↑, tiredness ↑"
    
    note right of Idle : "• Boredom accumulates<br/>• Curiosity decays<br/>• Tiredness/satisfaction decay"
    note right of Motivated : "• High motivation state<br/>• Ready to research"
    note right of Researching : "• Research active<br/>• Tiredness builds<br/>• Will add satisfaction when done"
```

### Parameter Impact Examples

With default values (`THRESHOLD=2.0`, `BOREDOM_RATE=0.0005`, `CURIOSITY_DECAY=0.0002`):

```mermaid
graph LR
    A["🕐 Time: 0h<br/>Motivation: 0"] --> B["🕐 Time: 2h<br/>Motivation: 1.0<br/>(boredom accumulated)"]
    B --> C["🕐 Time: 4h<br/>Motivation: 2.0<br/>🚀 RESEARCH TRIGGERED"]
    C --> D["🕐 Research Complete<br/>Motivation: -1.0<br/>(satisfaction + tiredness)"]
    D --> E["🕐 Time: 6h<br/>Motivation: 0.5<br/>(drives decay)"]
```

## Controlling the Engine

| Action | HTTP route | Front-end |
|--------|-----------|-----------|
| Start | `POST /research/control/start` | EngineSettings modal |
| Stop  | `POST /research/control/stop`  | EngineSettings modal |
| Trigger single cycle | `POST /research/trigger/{userId}` |  Topics dashboard "🚀 Research Now" |

### Motivation debug

* `GET  /research/debug/motivation` – current drive values
* `POST /research/debug/adjust-drives` – set boredom/curiosity… manually
* `POST /research/debug/update-config` – override threshold & decay rates at runtime

### Parameter Tuning Guide

| Behavior Goal | Parameter Changes | Effect |
|---------------|------------------|--------|
| **More frequent research** | ↑ `BOREDOM_RATE` or ↓ `MOTIVATION_THRESHOLD` | Triggers research sooner |
| **Less frequent research** | ↓ `BOREDOM_RATE` or ↑ `MOTIVATION_THRESHOLD` | Longer intervals between research |
| **Longer research sessions** | ↓ `TIREDNESS_DECAY` | Takes longer to get tired |
| **Shorter research sessions** | ↑ `TIREDNESS_DECAY` | Gets tired faster |
| **More persistent curiosity** | ↓ `CURIOSITY_DECAY` | Curiosity lasts longer |
| **Quick satisfaction reset** | ↑ `SATISFACTION_DECAY` | Ready for new research sooner |

#### Example Configurations

**Aggressive Research** (every ~1 hour):
```env
MOTIVATION_THRESHOLD=1.5
MOTIVATION_BOREDOM_RATE=0.001
```

**Conservative Research** (every ~6 hours):
```env
MOTIVATION_THRESHOLD=3.0
MOTIVATION_BOREDOM_RATE=0.0002
```

### Best Practices

* Begin with 1-2 focused topics (e.g. "GPT-4 performance benchmarks").
* Lower `RESEARCH_QUALITY_THRESHOLD` if you prefer more-but-noisier findings.
* Use the debug API (`/research/debug/motivation`) to monitor drive levels.
* Periodically mark findings as read or delete old ones to keep the sidebar tidy.

## Configuration Reference (excerpt)

All variables live in `backend/.env` (see template):

```
RESEARCH_ENGINE_ENABLED=true
RESEARCH_INTERVAL_HOURS=2          # approximate cadence
RESEARCH_MODEL=gpt-4o-mini
RESEARCH_QUALITY_THRESHOLD=0.6
RESEARCH_MAX_TOPICS_PER_USER=3

# Motivation drives
MOTIVATION_THRESHOLD=2.0
MOTIVATION_BOREDOM_RATE=0.0005
MOTIVATION_CURIOSITY_DECAY=0.0002
MOTIVATION_TIREDNESS_DECAY=0.0002
MOTIVATION_SATISFACTION_DECAY=0.0002
``` 