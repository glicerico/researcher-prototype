/**
 * Engagement Tracker - Utilities for tracking user engagement and behavior
 */

import { trackUserEngagement } from '../services/api';

class EngagementTracker {
  constructor() {
    this.readingSessions = new Map();
    this.interactionTimers = new Map();
    this.isEnabled = true;
  }

  /**
   * Enable or disable engagement tracking
   */
  setEnabled(enabled) {
    this.isEnabled = enabled;
  }

  /**
   * Start tracking reading time for content
   */
  startReadingSession(contentId, contentData = {}) {
    if (!this.isEnabled) return;

    const session = {
      contentId,
      startTime: Date.now(),
      contentData,
      interactions: [],
      scrollEvents: [],
      completed: false
    };

    this.readingSessions.set(contentId, session);
  }

  /**
   * Track scroll events to measure content completion
   */
  trackScrollEvent(contentId, scrollPercentage) {
    if (!this.isEnabled) return;

    const session = this.readingSessions.get(contentId);
    if (!session) return;

    session.scrollEvents.push({
      timestamp: Date.now(),
      percentage: scrollPercentage
    });

    // Mark as completed if user has scrolled through most of the content
    if (scrollPercentage > 80 && !session.completed) {
      session.completed = true;
    }
  }

  /**
   * Track interaction with content (clicks, selections, etc.)
   */
  trackInteraction(contentId, interactionType, data = {}) {
    if (!this.isEnabled) return;

    const session = this.readingSessions.get(contentId);
    if (!session) return;

    session.interactions.push({
      type: interactionType,
      timestamp: Date.now(),
      data
    });
  }

  /**
   * End reading session and send tracking data
   */
  async endReadingSession(contentId, userId) {
    if (!this.isEnabled) return;

    const session = this.readingSessions.get(contentId);
    if (!session) return;

    const endTime = Date.now();
    const readingTime = (endTime - session.startTime) / 1000; // Convert to seconds

    // Calculate completion rate based on scroll events
    const maxScroll = session.scrollEvents.length > 0 
      ? Math.max(...session.scrollEvents.map(e => e.percentage))
      : 0;
    
    const completionRate = Math.min(maxScroll / 100, 1.0);

    // Determine if user had follow-up interactions
    const hasFollowUp = session.interactions.some(i => 
      ['copy', 'share', 'bookmark', 'click_citation'].includes(i.type)
    );

    // Extract source types from content
    const sourceTypes = this.extractSourceTypes(session.contentData);

    // Prepare tracking data
    const trackingData = {
      reading_time_seconds: readingTime,
      completion_rate: completionRate,
      content_length: session.contentData.content_length || 0,
      source_types: sourceTypes,
      has_follow_up: hasFollowUp,
      interaction_count: session.interactions.length,
      topic_name: session.contentData.topic_name || 'unknown'
    };

    try {
      await trackUserEngagement('research_finding', trackingData);
    } catch (error) {
      console.error('Failed to track engagement:', error);
    }

    // Clean up
    this.readingSessions.delete(contentId);
  }

  /**
   * Track chat response engagement
   */
  async trackChatEngagement(responseData, userId, readingTime, hasFollowUp = false) {
    if (!this.isEnabled) return;

    const trackingData = {
      reading_time_seconds: readingTime,
      completion_rate: 1.0, // Assume full completion for chat responses
      response_length: responseData.response?.length || 0,
      has_follow_up: hasFollowUp,
      model_used: responseData.model,
      topic_initiated: this.isTopicInitiatedByUser(responseData)
    };

    try {
      await trackUserEngagement('chat_response', trackingData);
    } catch (error) {
      console.error('Failed to track chat engagement:', error);
    }
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

  /**
   * Create intersection observer for automatic scroll tracking
   */
  createScrollObserver(contentElement, contentId, threshold = [0.25, 0.5, 0.75, 1.0]) {
    if (!this.isEnabled || !contentElement) return null;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const percentage = Math.round(entry.intersectionRatio * 100);
          this.trackScrollEvent(contentId, percentage);
        }
      });
    }, {
      threshold,
      rootMargin: '0px'
    });

    observer.observe(contentElement);
    return observer;
  }

  /**
   * Track time spent on page/component
   */
  startPageTimer(pageId) {
    if (!this.isEnabled) return;

    this.interactionTimers.set(pageId, {
      startTime: Date.now(),
      lastActivity: Date.now()
    });
  }

  /**
   * Update activity timestamp
   */
  updateActivity(pageId) {
    if (!this.isEnabled) return;

    const timer = this.interactionTimers.get(pageId);
    if (timer) {
      timer.lastActivity = Date.now();
    }
  }

  /**
   * End page timer and get session duration
   */
  endPageTimer(pageId) {
    if (!this.isEnabled) return 0;

    const timer = this.interactionTimers.get(pageId);
    if (!timer) return 0;

    const sessionDuration = (Date.now() - timer.startTime) / 1000;
    this.interactionTimers.delete(pageId);
    
    return sessionDuration;
  }
}

// Create singleton instance
const engagementTracker = new EngagementTracker();

// React hook for easy component integration
export const useEngagementTracking = () => {
  return {
    startReading: (contentId, contentData) => engagementTracker.startReadingSession(contentId, contentData),
    endReading: (contentId, userId) => engagementTracker.endReadingSession(contentId, userId),
    trackScroll: (contentId, percentage) => engagementTracker.trackScrollEvent(contentId, percentage),
    trackInteraction: (contentId, type, data) => engagementTracker.trackInteraction(contentId, type, data),
    trackChat: (responseData, userId, readingTime, hasFollowUp) => 
      engagementTracker.trackChatEngagement(responseData, userId, readingTime, hasFollowUp),
    createScrollObserver: (element, contentId) => engagementTracker.createScrollObserver(element, contentId),
    startPageTimer: (pageId) => engagementTracker.startPageTimer(pageId),
    updateActivity: (pageId) => engagementTracker.updateActivity(pageId),
    endPageTimer: (pageId) => engagementTracker.endPageTimer(pageId),
    setEnabled: (enabled) => engagementTracker.setEnabled(enabled)
  };
};

export default engagementTracker;