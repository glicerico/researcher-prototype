import React, { useState, useEffect, useCallback } from 'react';
import { getTopSessionTopics, deleteTopicById, enableTopicResearchById, disableTopicResearchById, triggerManualResearch } from '../services/api';
import { useSession } from '../context/SessionContext';
import TopicSidebarItem from './TopicSidebarItem';
import '../styles/ConversationTopics.css';

const ConversationTopics = ({ sessionId, isCollapsed, onToggleCollapse, onTopicUpdate }) => {
  const { userId } = useSession();
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [researchLoading, setResearchLoading] = useState(false);

  // Fetch topics for the current session
  const fetchTopics = useCallback(async () => {
    if (!sessionId) {
      setTopics([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await getTopSessionTopics(sessionId, 3);
      setTopics(response.topics || []);
      setLastUpdate(Date.now());
      
      // Notify parent component of topic update
      if (onTopicUpdate) {
        onTopicUpdate(response.topics || []);
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
      fetchTopics();
    }, 15000); // Refresh every 15 seconds

    return () => clearInterval(interval);
  }, [sessionId, fetchTopics]);

  // Handle enabling research for a topic
  const handleEnableResearch = async (topic) => {
    try {
      // Use the new safe ID-based API instead of index-based
      await enableTopicResearchById(topic.topic_id);
      
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
      // Refresh topics to get correct state
      fetchTopics();
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

  // Handle immediate research trigger
  const handleImmediateResearch = async () => {
    if (!userId || researchLoading) return;
    
    try {
      setResearchLoading(true);
      const result = await triggerManualResearch(userId);
      
      if (result.success) {
        // Show success feedback
        const topicsResearched = result.topics_researched || 0;
        if (topicsResearched > 0) {
          setError(null);
          // Refresh topics to show any updates
          await fetchTopics();
        } else {
          setError('No active research topics found to research');
        }
      } else {
        setError('Research trigger failed: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error triggering immediate research:', error);
      setError('Failed to trigger research. Please try again.');
    } finally {
      setResearchLoading(false);
    }
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

  // Count active research topics
  const activeTopicsCount = topics.filter(topic => topic.is_active_research).length;

  return (
    <div className="conversation-topics">
      <div className="topics-header">
        <h3>Research Topics</h3>
        <div className="header-actions">
          {activeTopicsCount > 0 && (
            <button 
              className="immediate-research-button"
              onClick={handleImmediateResearch}
              disabled={researchLoading || loading}
              title={`Research ${activeTopicsCount} active topic${activeTopicsCount > 1 ? 's' : ''} now`}
            >
              {researchLoading ? (
                <>🔄 Researching...</>
              ) : (
                <>🚀 Research Now</>
              )}
            </button>
          )}
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

      <div className="topics-content">
        {loading && topics.length === 0 ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading topics...</p>
          </div>
        ) : error ? (
          <div className="error-state">
            <p>{error}</p>
            <button onClick={handleRefresh}>Retry</button>
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