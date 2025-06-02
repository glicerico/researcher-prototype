import React, { useState, useEffect, useCallback } from 'react';
import { 
  getAllTopicSuggestions, 
  getTopicStatistics, 
  deleteSessionTopics, 
  cleanupTopics 
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
      
      // Group by session for efficient deletion
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
      
      // Delete entire sessions that have all topics selected
      const deletionPromises = [];
      for (const [sessionId, sessionTopics] of Object.entries(sessionGroups)) {
        // For now, we'll delete the entire session if any topics are selected
        // In a more sophisticated implementation, we'd have individual topic deletion
        deletionPromises.push(deleteSessionTopics(sessionId));
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
  const handleDeleteTopic = async (sessionId) => {
    if (!window.confirm('Delete all topics from this session?')) {
      return;
    }
    
    try {
      await deleteSessionTopics(sessionId);
      await loadData();
    } catch (err) {
      console.error('Error deleting topic:', err);
      setError('Failed to delete topic. Please try again.');
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
                isSelected={selectedTopics.has(`${topic.session_id}-${index}`)}
                onSelect={(selected) => handleTopicSelect(topic.session_id, index, selected)}
                onDelete={() => handleDeleteTopic(topic.session_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TopicsDashboard; 