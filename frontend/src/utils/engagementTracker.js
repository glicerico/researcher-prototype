/**
 * Engagement Tracker - Utilities for tracking user engagement and behavior
 */

import { trackUserEngagement } from '../services/api';

class EngagementTracker {
  constructor() {
    this.isEnabled = true;
  }

  /**
   * Enable or disable engagement tracking
   */
  setEnabled(enabled) {
    this.isEnabled = enabled;
  }









  /**
   * Track interaction with content (clicks, selections, etc.)
   */
  trackInteraction(contentId, interactionType, data = {}) {
    if (!this.isEnabled) return;

    console.log('👤 EngagementTracker: User interaction tracked:', { contentId, interactionType, data });

    // Track as engagement event
    this.trackEngagementEvent({
      type: 'content_interaction',
      contentId,
      interactionType,
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Track specific engagement events (feedback, links, etc.)
   */
  async trackEngagementEvent(eventData) {
    if (!this.isEnabled) return;

    try {
      console.log('👤 EngagementTracker: Sending engagement event:', eventData.type);
      console.log('👤 EngagementTracker: Event data:', eventData);
      
      await trackUserEngagement('engagement_event', eventData);
      
      console.log(`👤 EngagementTracker: ✅ Successfully tracked ${eventData.type} event`);
    } catch (error) {
      console.error('👤 EngagementTracker: ❌ Failed to track engagement event:', error);
      console.error('👤 EngagementTracker: ❌ Failed event data:', eventData);
    }
  }

  /**
   * Track session continuation
   */
  trackSessionContinuation(sessionId, continuationType = 'new_message') {
    if (!this.isEnabled) return;

    console.log('👤 EngagementTracker: ✅ Session continuation tracked:', sessionId, continuationType);
    
    this.trackEngagementEvent({
      type: 'session_continuation',
      sessionId,
      continuationType,
      timestamp: Date.now()
    });
  }

  /**
   * Extract source types from research finding data
   */
  extractSourceTypes(contentData) {
    const sourceTypes = [];
    
    if (contentData.citations) {
      contentData.citations.forEach(citation => {
        const url = citation.toLowerCase();
        
        if (url.includes('arxiv.org') || url.includes('.edu') || url.includes('pubmed')) {
          sourceTypes.push('academic_papers');
        } else if (url.includes('news') || url.includes('reuters') || url.includes('bloomberg')) {
          sourceTypes.push('news_articles');
        } else if (url.includes('blog') || url.includes('medium.com')) {
          sourceTypes.push('expert_blogs');
        } else if (url.includes('.gov')) {
          sourceTypes.push('government_reports');
        } else {
          sourceTypes.push('industry_reports');
        }
      });
    }

    return [...new Set(sourceTypes)]; // Remove duplicates
  }

  /**
   * Check if topic was initiated by user vs system
   */
  isTopicInitiatedByUser(responseData) {
    // Simple heuristic - could be enhanced with more sophisticated detection
    return responseData.routing_analysis?.module_used !== 'autonomous_research';
  }




}

// Create singleton instance
const engagementTracker = new EngagementTracker();

// React hook for easy component integration
export const useEngagementTracking = () => {
  return {
    trackInteraction: (contentId, type, data) => engagementTracker.trackInteraction(contentId, type, data),
    trackEvent: (eventData) => engagementTracker.trackEngagementEvent(eventData),
    trackSessionContinuation: (sessionId, type) => engagementTracker.trackSessionContinuation(sessionId, type),
    setEnabled: (enabled) => engagementTracker.setEnabled(enabled)
  };
};

// Export individual functions for direct use
export const trackEngagement = (eventData) => engagementTracker.trackEngagementEvent(eventData);
export const trackSessionContinuation = (sessionId, type) => engagementTracker.trackSessionContinuation(sessionId, type);

export default engagementTracker;