# AI Personalization System

The researcher assistant includes a comprehensive, privacy-preserving personalization system that learns from user interactions to provide increasingly tailored responses and research findings.

## Overview

The personalization system consists of four main components that work together to understand and adapt to user preferences:

- **Secure Architecture**: Data managed with proper authentication
- **Transparent Learning**: Users can see exactly what the system has learned
- **User Control**: Override or disable any learned behavior
- **Adaptive Responses**: Dynamic tone, format, and content prioritization

## Architecture

### Core Components

#### 👤 ProfileManager (`backend/storage/profile_manager.py`)
Manages user profiles, preferences, and engagement analytics.

**Key Features:**
- User preference storage and retrieval
- Engagement tracking and analytics
- Preference change logging and history
- File migration and data management

**Storage Files per User:**
- `{user_id}_preferences.json` - Explicit user preferences
- `{user_id}_engagement_analytics.json` - Interaction data and metrics
- `{user_id}_personalization_history.json` - Learning history and changes

#### 👤 PersonalizationManager (`backend/storage/personalization_manager.py`)
Advanced learning engine that analyzes user behavior and adapts system responses.

**Learning Capabilities:**
- **Source Type Preferences**: Learns which research sources users engage with most
- **Format Optimization**: Adapts response length and structure based on engagement patterns
- **Content Prioritization**: Prioritizes topics and depth based on user engagement
- **Engagement Analysis**: Uses multiple metrics to measure user satisfaction and interest

**Adaptation Types:**
- Research source weighting (academic papers vs. news vs. blogs)
- Response length optimization
- Detail level adjustment

#### 👤 UserProfile Component (`frontend/src/components/UserProfile.jsx`)
Three-tab interface for managing personalization settings.

**Tabs:**
1. **Personality**: Communication style and tone preferences
2. **Content Preferences**: Research depth, source types, format settings
3. **What I've Learned**: Transparent view of all learned behaviors with override controls

#### 👤 EngagementTracker (`frontend/src/utils/engagementTracker.js`)
Comprehensive tracking of user interactions and reading patterns.

**Tracking Features:**
- Thumbs up/down feedback collection
- Link click tracking  
- Source exploration monitoring
- Session continuation analysis
- Research activation detection
- Scroll-based completion detection
- Source type engagement metrics

## User Experience

### Explicit Preferences

Users can directly configure:

**Content & Interaction Preferences:**
- **Research Depth**: Quick, Balanced, or Detailed responses
- **Source Types**: Slider controls for academic papers, news articles, expert blogs, etc.
- **Response Format**: Use bullet points, include key insights sections (citations are always numbered inline)
 - **Notification Frequency (External)**: Preference for external alerts (email/SMS): Low, Moderate, High. Does not affect in-app notifications.

**Personality Settings:**
- **Communication Style**: Helpful, Concise, Expert, Creative, Friendly
- **Tone**: Friendly, Professional, Casual, Enthusiastic, Direct
- **Quick Presets**: Academic, Business, Creative, Technical personalities

### Learned Behaviors

The system automatically learns from user interactions:

**Source Preference Learning:**
```javascript
// Example: User consistently reads academic papers to completion
// but skips news articles
academic_papers: 0.9,  // High preference (learned)
news_articles: 0.3     // Low preference (learned)
```

**Format Optimization:**
- Optimal response length based on reading patterns
- Structured vs. narrative response preferences
- Detail level preferences based on follow-up questions

**Engagement Patterns:**
- Follow-up question frequency
- Most engaged source types

### Transparency and Control

#### What I've Learned Dashboard

Users can see all learned behaviors in the **"What I've Learned"** tab:

**Sections:**
- **Source Type Preferences**: Shows learned weights with override buttons
- **Format Optimizations**: Displays optimal response length and structure preferences
- **Engagement Patterns**: Analytics on explicit feedback and interaction habits
- **Recent Adaptations**: History of system learning with effectiveness scores
- **User Overrides**: List of user-modified behaviors

**User Actions:**
- **Override**: Change any learned preference to a specific value
- **Disable Learning**: Stop automatic adjustment for specific behaviors
- **Reset**: Clear learned behaviors and start fresh

## Technical Implementation

### Search Parameter Integration

The search experience blends the user's learned preferences with query intent inferred by the Search Optimizer LLM.

- Intent-first parameters (from optimizer):
  - recency_filter: week | month | year | null
  - search_mode: web | academic | null
  - context_size: low | medium | high | null
  - confidence: per-parameter confidence in [0.0, 1.0]

- Preference fallbacks (from your profile):
  - search_mode fallback: if `content_preferences.source_types.academic_papers ≥ 0.7` → academic, else web
  - context_size fallback: map `content_preferences.research_depth` → shallow→low, balanced→medium, deep→high
  - recency_filter: remains intent-driven (no preference fallback)

Merge rule: use the optimizer’s choice when its confidence ≥ 0.7; otherwise, fall back to the learned preference.

This design keeps recency tightly aligned with user intent (e.g., “latest”, “updates”), while respecting stable user tastes for academic vs. web mode and desired context size.

### Data Storage

Each user has personalization data stored in three categories:

#### Preferences File (`{user_id}_preferences.json`)
```json
{
  "content_preferences": {
    "research_depth": "balanced",
    "source_types": {
      "academic_papers": 0.8,
      "news_articles": 0.6,
      "expert_blogs": 0.7,
      "government_reports": 0.5,
      "industry_reports": 0.6
    }
  },
  "format_preferences": {
    "response_length": "medium",
    "detail_level": "balanced",
    "use_bullet_points": true,
    "include_key_insights": true
  },
  "personality": {
    "style": "helpful",
    "tone": "friendly"
  }
}
```

#### Engagement Analytics (`{user_id}_engagement_analytics.json`)
```json
{
  "research_interactions": [
    {
      "timestamp": 1704067200,
      "topic_name": "AI Ethics", 
      "feedback": "up",
      "link_clicks": 2,
      "source_exploration_clicks": 1,
      "source_types": ["academic_papers", "expert_blogs"]
    }
  ],
  "chat_interactions": [
    {
      "timestamp": 1704067300,
      "response_length": 450,
      "feedback": "up",
      "session_continuation_rate": 1.0,
      "link_clicks": 0,
      "source_exploration_clicks": 1
    }
  ],
  "summary_stats": {
    "total_interactions": 25,
    "thumbs_up_rate": 0.82,
    "avg_link_clicks": 1.4,
    "most_engaged_sources": ["academic_papers", "expert_blogs"]
  }
}
```

#### Personalization History (`{user_id}_personalization_history.json`)
```json
{
  "learned_behaviors": {
    "source_preferences": {
      "academic_papers": 0.9,
      "news_articles": 0.4
    },
    "format_optimizations": {
      "optimal_response_length": 350,
      "prefers_structured_responses": true
    },
    "engagement_patterns": {
      "follow_up_frequency": 0.35,
      "preferred_sources": ["academic_papers", "expert_blogs"]
    }
  },
  "adaptation_history": [
    {
      "timestamp": 1704067200,
      "adaptation_type": "source_preference_academic_papers",
      "change_made": "Increased preference from 0.7 to 0.8",
      "reason": "Positive feedback and high engagement",
      "effectiveness_score": 0.85
    }
  ],
  "user_overrides": {
    "source_preference_news_articles": {
      "value": 0.7,
      "timestamp": 1704067300,
      "learning_disabled": false
    }
  },
  "learning_stats": {
    "total_adaptations": 15,
    "recent_activity": 3
  }
}
```

## API Reference

The personalization system provides REST API endpoints for managing user preferences, tracking engagement, and controlling learned behaviors. All endpoints require user authentication through session management.

### Base URL

```
http://localhost:8000/api/users
```

### API Endpoints

#### Get User Preferences

Retrieves the current user's personalization preferences.

```http
GET /api/users/preferences
```

**Response:**

```json
{
  "content_preferences": {
    "research_depth": "balanced",
    "source_types": {
      "academic_papers": 0.8,
      "news_articles": 0.6,
      "expert_blogs": 0.7,
      "government_reports": 0.5,
      "industry_reports": 0.6
    }
  },
  "format_preferences": {
    "response_length": "medium",
    "detail_level": "balanced", 
    "use_bullet_points": true,
    "include_key_insights": true
  },
  "personality": {
    "style": "helpful",
    "tone": "friendly",
    "additional_traits": {}
  }
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved preferences
- `404 Not Found` - User preferences not found (will create defaults)
- `500 Internal Server Error` - Server error

#### Update User Preferences

Updates the user's personalization preferences.

```http
PUT /api/users/preferences
Content-Type: application/json
```

**Request Body:**

```json
{
  "content_preferences": {
    "research_depth": "detailed",
    "source_types": {
      "academic_papers": 0.9,
      "news_articles": 0.4,
      "expert_blogs": 0.8,
      "government_reports": 0.6,
      "industry_reports": 0.5
    }
  },
  "format_preferences": {
    "response_length": "long",
    "detail_level": "comprehensive",
    "use_bullet_points": false,
    "include_key_insights": true
  },
  "personality": {
    "style": "expert",
    "tone": "professional"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Preferences updated successfully"
}
```

**Status Codes:**
- `200 OK` - Preferences updated successfully
- `400 Bad Request` - Invalid preference data
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

#### Track User Engagement

Records user interaction data for personalization learning.

```http
POST /api/users/engagement/track
Content-Type: application/json
```

**Research Finding Interaction:**

```json
{
  "interaction_type": "research_finding",
  "metadata": {
    "feedback": "up",
    "link_clicks": 2,
    "source_exploration_clicks": 1,
    "content_length": 1200,
    "source_types": ["academic_papers", "expert_blogs"],
    "has_follow_up": true,
    "topic_name": "AI Ethics in Healthcare"
  }
}
```

**Chat Response Interaction:**

```json
{
  "interaction_type": "chat_response", 
  "metadata": {
    "feedback": "up",
    "session_continuation_rate": 0.8,
    "response_length": 450,
    "link_clicks": 1,
    "source_exploration_clicks": 0,
    "model_used": "gpt-4",
    "topic_initiated": true
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Engagement tracked successfully"
}
```

**Status Codes:**
- `200 OK` - Engagement tracked successfully
- `400 Bad Request` - Missing or invalid interaction data
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

#### Get Personalization Data

Retrieves comprehensive personalization data including learned behaviors, adaptation history, and user overrides.

```http
GET /api/users/personalization
```

**Response:**

```json
{
  "learned_behaviors": {
    "source_preferences": {
      "academic_papers": 0.9,
      "news_articles": 0.4,
      "expert_blogs": 0.8,
      "government_reports": 0.6,
      "industry_reports": 0.5
    },
    "format_optimizations": {
      "optimal_response_length": 380,
      "prefers_structured_responses": true
    },
    "engagement_patterns": {
      "follow_up_frequency": 0.35,
      "preferred_sources": ["academic_papers", "expert_blogs"]
    }
  },
  "adaptation_history": [
    {
      "timestamp": 1704067200,
      "adaptation_type": "source_preference_academic_papers",
      "change_made": "Increased preference from 0.8 to 0.9",
      "reason": "Positive feedback and high engagement",
      "effectiveness_score": 0.88
    }
  ],
  "user_overrides": {
    "source_preference_news_articles": {
      "value": 0.7,
      "timestamp": 1704067300,
      "learning_disabled": false
    }
  },
  "learning_stats": {
    "total_adaptations": 15,
    "recent_activity": 3
  }
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved personalization data
- `404 Not Found` - No personalization data found (returns empty structure)
- `500 Internal Server Error` - Server error

#### Override Learned Behavior

Allows users to manually override or disable specific learned behaviors.

```http
POST /api/users/personalization/override
Content-Type: application/json
```

**Override with New Value:**

```json
{
  "preference_type": "source_preference_academic_papers",
  "override_value": 0.95,
  "disable_learning": false
}
```

**Disable Learning for Preference:**

```json
{
  "preference_type": "optimal_response_length", 
  "override_value": 400,
  "disable_learning": true
}
```

**Supported Preference Types:**
- `source_preference_academic_papers`
- `source_preference_news_articles` 
- `source_preference_expert_blogs`
- `source_preference_government_reports`
- `source_preference_industry_reports`
- `optimal_response_length`
- `prefers_structured_responses`

**Response:**

```json
{
  "success": true,
  "message": "Behavior override applied successfully"
}
```

**Status Codes:**
- `200 OK` - Override applied successfully
- `400 Bad Request` - Invalid preference type or value
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### API Usage Examples

#### JavaScript/Frontend Integration

```javascript
// Get user preferences
async function getUserPreferences() {
  const response = await fetch('/api/users/preferences');
  return await response.json();
}

// Update preferences
async function updatePreferences(preferences) {
  const response = await fetch('/api/users/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preferences)
  });
  return await response.json();
}

// Track engagement 
async function trackEngagement(interactionType, metadata) {
  const response = await fetch('/api/users/engagement/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      interaction_type: interactionType,
      metadata: metadata
    })
  });
  return await response.json();
}

// Override learned behavior
async function overridePreference(preferenceType, value, disableLearning = false) {
  const response = await fetch('/api/users/personalization/override', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      preference_type: preferenceType,
      override_value: value,
      disable_learning: disableLearning
    })
  });
  return await response.json();
}
```

#### Python/Backend Integration

```python
import httpx

# Track research finding engagement  
async def track_research_engagement(user_id: str, topic: str, feedback: str, link_clicks: int):
    engagement_data = {
        "interaction_type": "research_finding",
        "metadata": {
            "feedback": feedback,
            "link_clicks": link_clicks,
            "source_exploration_clicks": 1,
            "topic_name": topic,
            "source_types": ["academic_papers"]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/users/engagement/track",
            json=engagement_data
        )
        return response.json()
```

### Learning Algorithms

#### Source Type Learning
```python
def _adjust_source_preferences(self, user_id: str, source_types: List[str], 
                             engagement_score: float):
    """Adjust source type preferences based on engagement metrics."""
    for source_type in source_types:
        if engagement_score > 0.7:
            # Increase preference for highly engaging content
            current_pref = preferences.get(source_type, 0.5)
            new_pref = min(1.0, current_pref + 0.05)
            preferences[source_type] = new_pref
```

#### Format Optimization
```python
def _optimize_response_format(self, user_id: str, response_length: int, 
                            feedback: str):
    """Learn optimal response length based on explicit feedback only."""
    if feedback == "up":
        # User gave positive feedback - increase optimal length
        optimal_length = max(current_optimal, response_length)
    elif feedback == "down":
        # User gave negative feedback - decrease optimal length
        optimal_length = min(current_optimal, response_length * 0.8)
```

## Privacy and Security

### Secure Design

1. **Server-Side Storage**: All personalization data securely stored
2. **Authenticated Access**: Personal data only accessible through authenticated user sessions
3. **User Ownership**: Complete control over personal data and learned behaviors
4. **Transparent Operations**: All learning visible to users with override capabilities

### Data Protection

1. **Access Control**: Personalization data tied to user sessions
2. **Data Isolation**: Each user's data stored in separate files
3. **Audit Trail**: All preference changes logged with timestamps
4. **User Rights**: Ability to view, modify, or delete all personal data

## Monitoring and Administration

### Logging System

All personalization operations use the unified logging system with `👤` identifier:

```
👤 ProfileManager: ✅ Updated preferences for user user123. Categories: ['content_preferences']
👤 PersonalizationManager: Processing engagement for user user123, type: research_finding
👤 PersonalizationManager: ✅ Completed learning update for user user123
👤 UserProfile: Saving preferences for user: user123
👤 EngagementTracker: ✅ Content marked as completed for: research_456
```

### Admin Monitoring

Administrators can monitor personalization system health through:

1. **Log Analysis**: Filter logs by `👤` emoji for all personalization events
2. **Status Indicators**: `✅` for success, `❌` for errors, `⚠️` for warnings
3. **Performance Metrics**: Learning effectiveness and user engagement patterns
4. **Error Tracking**: Failed learning operations and data access issues

## Additional Documentation

### Related Documentation
- **[Logging System](logging-system.md)** - Admin monitoring and logging system documentation

## Development and Extension

### Adding New Learning Behaviors

1. **Update Models**: Add new fields to Pydantic models in `backend/models.py`
2. **Extend PersonalizationManager**: Add new learning methods
3. **Update Frontend**: Add controls in PersonalizationDashboard
4. **Add API Endpoints**: Expose new behaviors through REST API

### Testing

Run personalization system tests:
```bash
cd backend
source venv/bin/activate
./run_tests.sh --all
```

### Debugging

Enable debug logging for detailed personalization operations:
```python
import logging
logging.getLogger("researcher_prototype.personalization").setLevel(logging.DEBUG)
```

For comprehensive logging analysis and monitoring, see the [Logging System Documentation](logging-system.md).

## Best Practices

### For Users
1. **Regular Review**: Check "What I've Learned" tab periodically
2. **Active Feedback**: Override behaviors that don't match preferences
3. **Explicit Settings**: Set initial preferences for faster learning
4. **Privacy Awareness**: Understand what data is being collected about your interactions

### For Developers
1. **Privacy by Design**: Secure data storage with proper access controls
2. **Transparent Operations**: Log all learning activities with clear descriptions
3. **User Control**: Always provide override and disable options
4. **Performance Monitoring**: Track learning effectiveness and system impact

### For Administrators
1. **Monitor Logs**: Regular review of `👤` personalization logs
2. **Performance Tracking**: Monitor learning effectiveness and user satisfaction
3. **Privacy Compliance**: Ensure personal data is properly secured and access-controlled
4. **System Health**: Watch for learning errors or data corruption