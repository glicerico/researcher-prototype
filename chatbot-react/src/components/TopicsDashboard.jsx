import React, { useState, useEffect, useCallback } from 'react';
import { 
  getAllTopicSuggestions, 
  getTopicStatistics, 
  deleteSessionTopics, 
  deleteTopicById,
  cleanupTopics,
  enableTopicResearchById,
  disableTopicResearchById
} from '../services/api';
import TopicCard from './TopicCard';
import TopicsHeader from './TopicsHeader';
import TopicsFilters from './TopicsFilters';
import '../styles/TopicsDashboard.css';

const TopicsDashboard = () => {
  const [topics, setTopics] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState(new Set());
  const [filters, setFilters] = useState({
    searchTerm: '',
    minConfidence: 0,
    maxConfidence: 1,
    sortBy: 'confidence', // confidence, date, name
    sortOrder: 'desc' // asc, desc
  });

  // Load topics and stats
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [topicsResponse, statsResponse] = await Promise.all([
        getAllTopicSuggestions(),
        getTopicStatistics()
      ]);
      
      setTopics(topicsResponse.topic_suggestions || []);
      setStats(statsResponse);
    } catch (err) {
      console.error('Error loading topics data:', err);
      setError('Failed to load topics. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter and sort topics
  const filteredAndSortedTopics = React.useMemo(() => {
    let filtered = topics.filter(topic => {
      // Search filter
      if (filters.searchTerm) {
        const searchLower = filters.searchTerm.toLowerCase();
        if (!topic.name.toLowerCase().includes(searchLower) && 
            !topic.description.toLowerCase().includes(searchLower)) {
          return false;
        }
      }
      
      // Confidence filter
      if (topic.confidence_score < filters.minConfidence || 
          topic.confidence_score > filters.maxConfidence) {
        return false;
      }
      
      return true;
    });

    // Sort topics
    filtered.sort((a, b) => {
      let comparison = 0;
      
      switch (filters.sortBy) {
        case 'confidence':
          comparison = a.confidence_score - b.confidence_score;
          break;
        case 'date':
          comparison = a.suggested_at - b.suggested_at;
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        default:
          comparison = 0;
      }
      
      return filters.sortOrder === 'desc' ? -comparison : comparison;
    });

    return filtered;
  }, [topics, filters]);

  // Handle topic selection
  const handleTopicSelect = (sessionId, topicIndex, selected) => {
    const topicKey = `${sessionId}-${topicIndex}`;
    const newSelected = new Set(selectedTopics);
    
    if (selected) {
      newSelected.add(topicKey);
    } else {
      newSelected.delete(topicKey);
    }
    
    setSelectedTopics(newSelected);
  };

  // Handle select all
  const handleSelectAll = () => {
    if (selectedTopics.size === filteredAndSortedTopics.length) {
      // Deselect all
      setSelectedTopics(new Set());
    } else {
      // Select all visible topics
      const allKeys = new Set();
      filteredAndSortedTopics.forEach((topic, index) => {
        allKeys.add(`${topic.session_id}-${index}`);
      });
      setSelectedTopics(allKeys);
    }
  };

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedTopics.size === 0) return;

    if (!window.confirm(`Delete ${selectedTopics.size} selected topics?`)) {
      return;
    }

    try {
      setLoading(true);

      // Group selected topics by session
      const sessionGroups = {};
      filteredAndSortedTopics.forEach((topic, index) => {
        const topicKey = `${topic.session_id}-${index}`;
        if (selectedTopics.has(topicKey)) {
          if (!sessionGroups[topic.session_id]) {
            sessionGroups[topic.session_id] = [];
          }
          sessionGroups[topic.session_id].push(topic);
        }
      });

      // Count total topics per session
      const totalBySession = {};
      topics.forEach((topic) => {
        totalBySession[topic.session_id] = (totalBySession[topic.session_id] || 0) + 1;
      });

      const deletionPromises = [];
      for (const [sessionId, sessionTopics] of Object.entries(sessionGroups)) {
        if (sessionTopics.length === totalBySession[sessionId]) {
          // All topics from this session selected - delete entire session
          deletionPromises.push(deleteSessionTopics(sessionId));
        } else {
          // Delete individual topics by ID
          sessionTopics.forEach((topic) => {
            deletionPromises.push(deleteTopicById(topic.topic_id));
          });
        }
      }

      await Promise.all(deletionPromises);

      // Clear selection and reload data
      setSelectedTopics(new Set());
      await loadData();

    } catch (err) {
      console.error('Error deleting topics:', err);
      setError('Failed to delete topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle cleanup
  const handleCleanup = async () => {
    if (!window.confirm('Clean up old and duplicate topics? This action cannot be undone.')) {
      return;
    }
    
    try {
      setLoading(true);
      await cleanupTopics();
      await loadData();
    } catch (err) {
      console.error('Error cleaning up topics:', err);
      setError('Failed to clean up topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle individual topic deletion
  const handleDeleteTopic = async (topicId, topicName) => {
    if (!window.confirm(`Delete topic "${topicName}"?`)) {
      return;
    }
    
    try {
      await deleteTopicById(topicId);  // Use safe ID-based deletion
      await loadData();  // Reload to reflect changes
    } catch (err) {
      console.error('Error deleting topic:', err);
      setError('Failed to delete topic. Please try again.');
    }
  };

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
      setError('Failed to enable research. Please try again.');
      // Refresh topics to get correct state
      loadData();
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
      setError('Failed to disable research. Please try again.');
      // Refresh topics to get correct state
      loadData();
    }
  };

  if (loading && topics.length === 0) {
    return (
      <div className="topics-dashboard">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading topics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="topics-dashboard">
      <TopicsHeader 
        stats={stats}
        selectedCount={selectedTopics.size}
        totalCount={filteredAndSortedTopics.length}
        onCleanup={handleCleanup}
        onBulkDelete={handleBulkDelete}
        onSelectAll={handleSelectAll}
        loading={loading}
      />
      
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={loadData}>Retry</button>
        </div>
      )}
      
      <TopicsFilters 
        filters={filters}
        onFiltersChange={setFilters}
        topicsCount={filteredAndSortedTopics.length}
      />
      
      <div className="topics-content">
        {filteredAndSortedTopics.length === 0 ? (
          <div className="empty-state">
            <h3>No Topics Found</h3>
            <p>
              {topics.length === 0 
                ? "You haven't generated any research topics yet. Start chatting to discover interesting topics!"
                : "No topics match your current filters. Try adjusting your search criteria."
              }
            </p>
          </div>
        ) : (
          <div className="topics-grid">
            {filteredAndSortedTopics.map((topic, index) => (
              <TopicCard
                key={`${topic.session_id}-${index}`}
                topic={topic}
                index={index}
                isSelected={selectedTopics.has(`${topic.session_id}-${index}`)}
                onSelect={(selected) => handleTopicSelect(topic.session_id, index, selected)}
                onDelete={() => handleDeleteTopic(topic.topic_id, topic.name)}
                onEnableResearch={() => handleEnableResearch(topic)}
                onDisableResearch={() => handleDisableResearch(topic)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TopicsDashboard; 