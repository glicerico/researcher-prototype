import React, { useState, useEffect, useCallback } from 'react';
import { getSessionTopicSuggestions, deleteTopicById, enableTopicResearchById, disableTopicResearchById } from '../services/api';
import { trackEngagement } from '../utils/engagementTracker';
import TopicSidebarItem from './TopicSidebarItem';
import ErrorModal from './ErrorModal';
import '../styles/ConversationTopics.css';

const ConversationTopics = ({ sessionId, isCollapsed, onToggleCollapse, onTopicUpdate }) => {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch topics for the current session
  const fetchTopics = useCallback(async (preserveError = false) => {
    if (!sessionId) {
      setTopics([]);
      return;
    }

    try {
      setLoading(true);
      if (!preserveError) {
        setError(null);
      }
      
      const response = await getSessionTopicSuggestions(sessionId);
      const allTopics = response.topic_suggestions || [];
      
      // Get the 3 latest topics
      const latestTopics = [...allTopics]
        .sort((a, b) => b.suggested_at - a.suggested_at)
        .slice(0, 3);
        
      const latestTopicIds = new Set(latestTopics.map(t => t.topic_id));

      // Get the top 2 confidence topics that are NOT already in the latest list
      const otherTopTopics = [...allTopics]
        .sort((a, b) => b.confidence_score - a.confidence_score)
        .filter(t => !latestTopicIds.has(t.topic_id))
        .slice(0, 2);
        
      // Combine and sort for display
      const finalTopics = [...latestTopics, ...otherTopTopics];
      finalTopics.sort((a, b) => b.suggested_at - a.suggested_at);
      
      setTopics(finalTopics);
      setLastUpdate(Date.now());
      
      // Notify parent component of topic update
      if (onTopicUpdate) {
        onTopicUpdate(finalTopics);
      }
    } catch (err) {
      console.error('Error fetching topics:', err);
      setError('Failed to load topics');
    } finally {
      setLoading(false);
    }
  }, [sessionId, onTopicUpdate]);

  // Initial fetch when sessionId changes
  useEffect(() => {
    fetchTopics();
  }, [fetchTopics]);

  // Auto-refresh topics every 15 seconds when session is active
  useEffect(() => {
    if (!sessionId) return;

    const interval = setInterval(() => {
      fetchTopics(true); // Preserve error during auto-refresh
    }, 15000); // Refresh every 15 seconds

    return () => clearInterval(interval);
  }, [sessionId, fetchTopics]);

  // Handle enabling research for a topic
  const handleEnableResearch = async (topic) => {
    try {
      // Use the new safe ID-based API instead of index-based
      await enableTopicResearchById(topic.topic_id);
      
      // Track research activation
      console.log('👤 ConversationTopics: ✅ Research activation tracked for topic:', topic.name);
      trackEngagement({
        type: 'research_activation',
        topicId: topic.topic_id,
        topicName: topic.name,
        activationType: 'conversation_topic_enable',
        timestamp: Date.now()
      });
      
      // Optimistically update the UI
      setTopics(prevTopics => 
        prevTopics.map(t => 
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: true }
            : t
        )
      );
    } catch (error) {
      console.error('Error enabling research:', error);
      
      let errorMessage = 'Failed to enable research. Please try again.';
      
      // Extract error message from response
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'object' && detail.error) {
          errorMessage = detail.error;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      }
      
      setError(errorMessage);
      
      // Don't refresh immediately so user can see the error message
      // fetchTopics() will be called by the retry button or auto-refresh
    }
  };

  // Handle disabling research for a topic
  const handleDisableResearch = async (topic) => {
    try {
      // Use the new safe ID-based API instead of index-based
      await disableTopicResearchById(topic.topic_id);
      
      // Optimistically update the UI
      setTopics(prevTopics => 
        prevTopics.map(t => 
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: false }
            : t
        )
      );
    } catch (error) {
      console.error('Error disabling research:', error);
      // Refresh topics to get correct state
      fetchTopics();
    }
  };

  // Handle deleting a topic
  const handleDeleteTopic = async (topicId) => {
    try {
      await deleteTopicById(topicId);
      
      // Remove topic from UI immediately by filtering by topic ID
      setTopics(prevTopics => 
        prevTopics.filter(topic => topic.topic_id !== topicId)
      );
    } catch (error) {
      console.error('Error deleting topic:', error);
      // Refresh topics to get correct state
      fetchTopics();
    }
  };

  // Manual refresh function
  const handleRefresh = () => {
    fetchTopics();
  };

  // Dismiss error message
  const handleDismissError = () => {
    setError(null);
  };

  if (isCollapsed) {
    return (
      <div className="conversation-topics collapsed">
        <button 
          className="expand-button"
          onClick={onToggleCollapse}
          title="Show research topics"
        >
          🔍
        </button>
      </div>
    );
  }

  return (
    <div className="conversation-topics">
      <div className="topics-header">
        <h3>Proposed Research Topics</h3>
        <div className="header-actions">
          <button
            className="refresh-button"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh topics"
          >
            🔄
          </button>
          <button
            className="collapse-button"
            onClick={onToggleCollapse}
            title="Hide topics panel"
          >
            ✕
          </button>
        </div>
      </div>

      <ErrorModal 
        isOpen={!!error}
        message={error}
        onClose={handleDismissError}
      />

      <div className="topics-content">
        {loading && topics.length === 0 ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading topics...</p>
          </div>
        ) : topics.length === 0 ? (
          <div className="empty-state">
            {!sessionId ? (
              <>
                <p>Start a conversation to discover research topics!</p>
                <small>AI will automatically suggest interesting research topics as you chat.</small>
              </>
            ) : (
              <>
                <p>No research topics yet.</p>
                <small>Topics will appear as we discuss research-worthy subjects.</small>
              </>
            )}
          </div>
        ) : (
          <div className="topics-list">
            {topics.map((topic, index) => (
              <TopicSidebarItem
                key={`${topic.session_id}-${index}`}
                topic={topic}
                index={index}
                onEnableResearch={() => handleEnableResearch(topic)}
                onDisableResearch={() => handleDisableResearch(topic)}
                onDelete={() => handleDeleteTopic(topic.topic_id)}
              />
            ))}
          </div>
        )}

        {topics.length > 0 && (
          <div className="topics-footer">
            <small>
              {loading && (
                <span className="update-indicator">🔄 Updating...</span>
              )}
              {lastUpdate && !loading && (
                <span className="last-update">
                  Updated {new Date(lastUpdate).toLocaleTimeString()}
                </span>
              )}
            </small>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationTopics; 