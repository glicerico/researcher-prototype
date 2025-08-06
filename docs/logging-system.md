# Logging System Documentation

This document describes the unified logging system used throughout the AI researcher assistant, with special focus on the personalization system monitoring capabilities.

## Overview

The system uses a standardized emoji-based logging format that provides visual process identification and status indicators across all components. This makes it easy for administrators to monitor system health, debug issues, and track user interactions.

## Logging Format

### Standard Pattern

```
[EMOJI] [COMPONENT]: [STATUS_EMOJI] [MESSAGE]
```

**Example:**
```
👤 ProfileManager: ✅ Updated preferences for user user123. Categories: ['content_preferences']
🔍 Search: ❌ Perplexity API key not configured
🌐 API: Tracking engagement for user user123: research_finding
```

## Process Identifiers (Primary Emojis)

### Personalization System
All personalization components use **👤** for unified identification:

- **👤 ProfileManager** - User profile and preference management
- **👤 PersonalizationManager** - AI learning and personalization processes  
- **👤 UserProfile** - Frontend user interface components
- **👤 EngagementTracker** - User analytics and behavior tracking

### LangGraph Processing Nodes
Each processing node has its own identifier:

- **🔍** - Search operations (SearchNode, TopicExtractor, QueryGenerator)
- **💾** - Storage operations (ResearchStorage)
- **🎯** - Quality assessment (ResearchQualityAssessor) 
- **🧠** - Memory/initialization operations (InitializerNode, IntegratorNode)
- **🔄** - Deduplication operations (ResearchDeduplication)

### API Layer
- **🌐 API** - Web API endpoints and request handling

## Status Indicators (Secondary Emojis)

### Success Operations - ✅
Used for successful completions, achievements, and positive outcomes:

```
👤 ProfileManager: ✅ Updated preferences for user user123
🔍 Search: ✅ Found 12 citations
💾 Research Storage: ✅ Successfully stored research finding
🌐 API: ✅ Successfully updated preferences for user user123
```

### Errors and Failures - ❌
Used for critical errors, failures, and exceptions:

```
👤 ProfileManager: ❌ Error getting preferences for user user123: file not found
🔍 Search: ❌ Perplexity API key not configured
🎯 Research Quality Assessor: ❌ No successful search results to assess
🌐 API: ❌ Error updating preferences for user user123: validation error
```

### Warnings and Non-Critical Issues - ⚠️
Used for warnings, non-critical issues, and informational alerts:

```
👤 EngagementTracker: ⚠️ No active session found for scroll tracking
💾 Research Storage: ⚠️ Quality score 0.42 below threshold 0.6 - not storing
🧠 Initializer: ⚠️ No memory context found for this thread
```

### Special Status Indicators

#### Disabled Features - 🚫
```
👤 PersonalizationManager: 🚫 Disabled learning for user user123, type: source_preference_news
```

#### Updates and Modifications - 🔄
```
👤 UserProfile: 🔄 Refreshed personalization data after preference update
```

## Component-Specific Logging

### Personalization System Logging

#### ProfileManager (`👤 ProfileManager`)
```
👤 ProfileManager: Creating default preferences for user user123
👤 ProfileManager: ✅ Updated preferences for user user123. Categories: ['content_preferences']
👤 ProfileManager: Tracking engagement for user user123: research_finding
👤 ProfileManager: ❌ Error getting preferences for user user123: file permission denied
```

#### PersonalizationManager (`👤 PersonalizationManager`)
```
👤 PersonalizationManager: Processing engagement for user user123, type: research_finding
👤 PersonalizationManager: ✅ Completed learning update for user user123
👤 PersonalizationManager: Adjusting source preferences for user user123: {'academic_papers': 0.1}
👤 PersonalizationManager: 🚫 Disabled learning for user user123, type: optimal_response_length
👤 PersonalizationManager: ❌ Error tracking engagement for user user123: invalid data format
```

#### UserProfile Component (`👤 UserProfile`)
```
👤 UserProfile: Applying personality preset: academic
👤 UserProfile: Saving preferences for user: user123
👤 UserProfile: ✅ Successfully saved preferences for user: user123
👤 UserProfile: 🔄 Refreshed personalization data after preference update
👤 UserProfile: ❌ Error updating preferences for user: user123
```

#### EngagementTracker (`👤 EngagementTracker`)
```
👤 EngagementTracker: Starting reading session for content: research_456
👤 EngagementTracker: Scroll milestone reached for research_456: 50%
👤 EngagementTracker: ✅ Content marked as completed for: research_456
👤 EngagementTracker: ✅ Successfully tracked research engagement for research_456
👤 EngagementTracker: ⚠️ No active session found for scroll tracking: research_789
👤 EngagementTracker: ❌ Failed to track research engagement for content: research_456
```

### API Layer Logging (`🌐 API`)
```
🌐 API: Getting preferences for user user123
🌐 API: ✅ Successfully updated preferences for user user123
🌐 API: Tracking engagement for user user123: research_finding
🌐 API: User user123 overriding learned behavior: source_preference_academic_papers = 0.9
🌐 API: ❌ Error getting preferences for user user123: database connection failed
```

### LangGraph Processing Logging

#### Search Operations (`🔍`)
```
🔍 Search: Preparing to search for information
🔍 Search: Searching for: "AI personalization research"
🔍 Search: ✅ Result received: "Comprehensive research on AI personalization..."
🔍 Search: ✅ Found 12 citations
🔍 Search: ❌ Perplexity API request failed with status code 429
```

#### Storage Operations (`💾`)
```
💾 Research Storage: Processing research findings for storage
💾 Research Storage: Storing high-quality finding for topic 'AI Ethics' (score: 0.85)
💾 Research Storage: ✅ Successfully stored research finding for 'AI Ethics'
💾 Research Storage: ⚠️ Quality score 0.42 below threshold 0.6 - not storing
💾 Research Storage: ❌ Failed to store research finding for 'AI Ethics'
```

#### Quality Assessment (`🎯`)
```
🎯 Research Quality Assessor: Evaluating research findings quality
🎯 Research Quality Assessor: Assessing quality for topic 'Machine Learning'
🎯 Research Quality Assessor: ✅ Quality assessment completed - Overall score: 0.85
🎯 Research Quality Assessor: ❌ No successful search results to assess
```

#### Memory Operations (`🧠`)
```
🧠 Initializer: Setting up user state and thread
🧠 Initializer: ✅ Generated new thread ID: user123-20240101_120000
🧠 Initializer: ✅ Retrieved memory context from ZEP
🧠 Initializer: ⚠️ No memory context found for this thread
🧠 Integrator: ✅ Generated response: "Based on recent research..."
```

## Monitoring and Filtering

### Filter by Process Type

#### Personalization System Monitoring
```bash
# All personalization events
grep "👤" application.log

# Specific component
grep "👤 ProfileManager" application.log
grep "👤 PersonalizationManager" application.log
grep "👤 UserProfile" application.log
grep "👤 EngagementTracker" application.log
```

#### LangGraph Processing Monitoring  
```bash
# Search operations
grep "🔍" application.log

# Storage operations  
grep "💾" application.log

# Quality assessment
grep "🎯" application.log

# Memory operations
grep "🧠" application.log
```

#### API Layer Monitoring
```bash
# All API requests
grep "🌐 API" application.log
```

### Filter by Status

#### Success Operations
```bash
# All successful operations
grep "✅" application.log

# Successful personalization operations
grep "👤.*✅" application.log
```

#### Error Tracking
```bash
# All errors
grep "❌" application.log

# Personalization system errors
grep "👤.*❌" application.log

# API errors
grep "🌐.*❌" application.log
```

#### Warning Monitoring
```bash
# All warnings
grep "⚠️" application.log

# System warnings
grep "💾.*⚠️\|🧠.*⚠️" application.log
```

### Combined Filtering

#### User-Specific Monitoring
```bash
# All events for specific user
grep "user123" application.log | grep "👤\|🌐"

# Personalization events for user
grep "user123" application.log | grep "👤"

# API events for user  
grep "user123" application.log | grep "🌐"
```

#### Error Analysis by Component
```bash
# Personalization errors
grep "👤.*❌" application.log

# Search errors
grep "🔍.*❌" application.log

# Storage errors
grep "💾.*❌" application.log

# API errors
grep "🌐.*❌" application.log
```

## Log Levels and Configuration

### Python Backend Logging

The backend uses Python's standard logging module with custom formatters:

```python
import logging

# Set log level for personalization components
logging.getLogger("researcher_prototype.personalization").setLevel(logging.DEBUG)

# Set log level for API components  
logging.getLogger("researcher_prototype.api").setLevel(logging.INFO)

# Set log level for LangGraph nodes
logging.getLogger("researcher_prototype.nodes").setLevel(logging.INFO)
```

### Frontend Console Logging

The frontend uses console logging for development and debugging:

```javascript
// Enable detailed engagement tracking logs
localStorage.setItem('debug_engagement', 'true');

// Enable personalization component logs
localStorage.setItem('debug_personalization', 'true');
```

## Log Analysis Tools

### Basic Log Analysis

#### Count Events by Component
```bash
# Count personalization events
grep -c "👤" application.log

# Count by specific component
grep -c "👤 ProfileManager" application.log
grep -c "👤 PersonalizationManager" application.log
grep -c "🔍 Search" application.log
```

#### Error Rate Analysis
```bash
# Total vs error ratio for personalization
total=$(grep -c "👤" application.log)
errors=$(grep -c "👤.*❌" application.log)
echo "Personalization error rate: $(($errors * 100 / $total))%"
```

#### User Activity Analysis
```bash
# Most active users in personalization
grep "👤" application.log | grep -o "user[0-9]*" | sort | uniq -c | sort -nr
```

### Advanced Analysis with awk

#### Success Rate by Component
```bash
grep "👤" application.log | awk '
/✅/ { success++ }
/❌/ { errors++ }
/⚠️/ { warnings++ }
END { 
    total = success + errors + warnings
    printf "Success: %d (%.1f%%)\n", success, success*100/total
    printf "Errors: %d (%.1f%%)\n", errors, errors*100/total  
    printf "Warnings: %d (%.1f%%)\n", warnings, warnings*100/total
}'
```

#### Response Time Analysis (for timed operations)
```bash
grep "👤.*reading_time" application.log | awk '{
    match($0, /reading_time=([0-9.]+)/, arr)
    if (arr[1]) {
        times[++count] = arr[1]
        total += arr[1]
    }
}
END {
    avg = total/count
    printf "Average reading time: %.2f seconds\n", avg
    printf "Total interactions: %d\n", count
}'
```

## Production Monitoring

### Log Rotation

Configure log rotation for production environments:

```bash
# /etc/logrotate.d/researcher-prototype
/var/log/researcher-prototype/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 app app
    postrotate
        systemctl reload researcher-prototype
    endscript
}
```

### Monitoring Alerts

Set up monitoring alerts for critical patterns:

#### High Error Rate Alert
```bash
# Alert if error rate exceeds 5% in last hour
errors=$(grep "❌" application.log | tail -1000 | wc -l)
total=$(tail -1000 application.log | wc -l)
if [ $((errors * 100 / total)) -gt 5 ]; then
    echo "ALERT: High error rate detected: $((errors * 100 / total))%"
fi
```

#### Personalization System Health
```bash
# Check if personalization system is responding
recent_activity=$(grep "👤" application.log | tail -100 | wc -l)
if [ $recent_activity -lt 10 ]; then
    echo "WARNING: Low personalization activity in recent logs"
fi
```

### Integration with Monitoring Tools

#### Prometheus Metrics
Export key metrics for Prometheus monitoring:

```python
from prometheus_client import Counter, Histogram

# Personalization metrics
personalization_operations = Counter('personalization_operations_total', 
                                   'Total personalization operations', 
                                   ['component', 'status'])

engagement_tracking_duration = Histogram('engagement_tracking_duration_seconds',
                                       'Time spent tracking engagement')
```

#### Structured Logging

For production, consider structured logging with JSON format:

```python
import structlog

logger = structlog.get_logger()
logger.info("preferences_updated", 
           user_id="user123", 
           component="ProfileManager",
           categories=["content_preferences"],
           status="success")
```

This enables better log aggregation and analysis in tools like ELK stack or Splunk.

## Troubleshooting Common Issues

### Personalization System Issues

#### No Learning Occurring
```bash
# Check for personalization activity
grep "👤 PersonalizationManager" application.log | grep -v "❌"

# Look for engagement tracking
grep "👤 EngagementTracker" application.log | grep "✅"
```

#### Preference Update Failures
```bash
# Check API preference updates
grep "🌐 API.*preferences" application.log

# Check ProfileManager operations
grep "👤 ProfileManager.*preferences" application.log
```

#### High Error Rates
```bash
# Identify most common errors
grep "👤.*❌" application.log | awk -F': ' '{print $3}' | sort | uniq -c | sort -nr
```

### Performance Issues

#### Slow Engagement Tracking
```bash
# Look for performance warnings
grep "👤 EngagementTracker" application.log | grep -E "(slow|timeout|performance)"
```

#### API Response Times
```bash
# Monitor API response patterns
grep "🌐 API" application.log | grep -E "(timeout|slow|delay)"
```

This logging system provides comprehensive visibility into all aspects of the AI researcher assistant, making it easy to monitor system health, debug issues, and ensure optimal performance of the personalization features.