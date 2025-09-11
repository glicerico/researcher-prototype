import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from '../context/SessionContext';
import TopicsHeader from './TopicsHeader';
import TopicsFilters from './TopicsFilters';
import MotivationStats from './MotivationStats';
import EngineSettings from './EngineSettings';
import AddTopicForm from './AddTopicForm';
import { 
  getAllTopicSuggestions,
  getTopicStatistics,
  deleteSessionTopics, 
  deleteTopicById, 
  cleanupTopics,
  deleteNonActivatedTopics,
  createCustomTopic,
  enableTopicResearchById,
  disableTopicResearchById,
  getResearchEngineStatus,
  startResearchEngine,
  stopResearchEngine,
  triggerManualResearch
} from '../services/api';
import '../styles/TopicsDashboard.css';

const TopicsDashboard = () => {
  const { userId } = useSession();
  const [topics, setTopics] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState(new Set());
  const [researchEngineStatus, setResearchEngineStatus] = useState(null);
  const [researchEngineLoading, setResearchEngineLoading] = useState(false);
  const [immediateResearchLoading, setImmediateResearchLoading] = useState(false);
  const [activeTopicsCount, setActiveTopicsCount] = useState(0);
  const [showMotivation, setShowMotivation] = useState(false);
  const [showEngineSettings, setShowEngineSettings] = useState(false);
  const [showAddTopicForm, setShowAddTopicForm] = useState(false);
  const [filters, setFilters] = useState({
    searchTerm: '',
    sessionFilter: 'all',
    confidenceFilter: 'all',
    researchStatus: 'all',
    sortBy: 'date',
    sortOrder: 'desc', // asc, desc
    autoOnly: false,
  });
  const [expandedTopics, setExpandedTopics] = useState(new Set());

  // Helper function to format dates
  const formatDate = (timestamp) => {
    if (!timestamp) return 'Unknown date';
    
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  // Load topics and stats
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [topicsResponse, statsResponse, engineStatus] = await Promise.all([
        getAllTopicSuggestions(),
        getTopicStatistics(),
        getResearchEngineStatus().catch(() => ({ available: false, enabled: false, running: false }))
      ]);
      
      const topicsData = topicsResponse.topic_suggestions || [];
      setTopics(topicsData);
      setStats(statsResponse || {});
      setActiveTopicsCount(
        topicsData.filter(topic => topic.is_active_research).length
      );
      setResearchEngineStatus(engineStatus);
      
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

  // Auto-refresh data every 10 seconds when user is selected
  useEffect(() => {
    if (!userId) return;

    const interval = setInterval(() => {
      loadData();
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [userId, loadData]);

  // Handle global research engine toggle
  const handleToggleGlobalResearch = async () => {
    if (!researchEngineStatus) return;
    
    try {
      setResearchEngineLoading(true);
      
      if (researchEngineStatus.running) {
        await stopResearchEngine();
        setResearchEngineStatus(prev => ({ ...prev, running: false }));
      } else {
        await startResearchEngine();
        setResearchEngineStatus(prev => ({ ...prev, running: true }));
      }
      
    } catch (err) {
      console.error('Error toggling research engine:', err);
      setError('Failed to toggle research engine. Please try again.');
      // Refresh status to get correct state
      loadData();
    } finally {
      setResearchEngineLoading(false);
    }
  };

  // Handle immediate research trigger
  const handleImmediateResearch = async () => {
    if (!userId || immediateResearchLoading) return;
    
    try {
      setImmediateResearchLoading(true);
      setError(null);
      
      const result = await triggerManualResearch(userId);
      
      if (result.success) {
        const topicsResearched = result.topics_researched || 0;
        if (topicsResearched > 0) {
          // Refresh data to show any updates
          await loadData();
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
      setImmediateResearchLoading(false);
    }
  };

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
      // Auto expansions only filter
      if (filters.autoOnly && !topic.is_expansion) {
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

  // Handle delete non-activated topics
  const handleDeleteNonActivated = async () => {
    const nonActivatedCount = topics.filter(topic => !topic.is_active_research).length;
    
    if (nonActivatedCount === 0) {
      setError('No inactive topics found to delete.');
      return;
    }
    
    if (!window.confirm(`Delete all ${nonActivatedCount} topics that are not activated for research? This action cannot be undone.`)) {
      return;
    }
    
    try {
      setLoading(true);
      const result = await deleteNonActivatedTopics();
      
      if (result.success) {
        await loadData(); // Reload to reflect changes
        // Clear any previous error message
        setError(null);
      } else {
        setError('Failed to delete inactive topics. Please try again.');
      }
    } catch (err) {
      console.error('Error deleting non-activated topics:', err);
      setError('Failed to delete inactive topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle showing add topic form
  const handleShowAddTopicForm = () => {
    setShowAddTopicForm(true);
  };

  // Handle closing add topic form
  const handleCloseAddTopicForm = () => {
    setShowAddTopicForm(false);
  };

  // Handle topic added successfully
  const handleTopicAdded = (newTopic) => {
    // Refresh data to show the new topic
    loadData();
    
    // Update active topics count if the topic was created with research enabled
    if (newTopic.is_active_research) {
      setActiveTopicsCount(prev => prev + 1);
    }
    
    // Clear any previous error messages
    setError(null);
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
      
      // Optimistically update the UI and active count
      setTopics(prevTopics => 
        prevTopics.map(t => 
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: true }
            : t
        )
      );
      setActiveTopicsCount(prev => prev + 1);
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
      
      // Optimistically update the UI and active count
      setTopics(prevTopics => 
        prevTopics.map(t => 
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: false }
            : t
        )
      );
      setActiveTopicsCount(prev => prev - 1);
    } catch (error) {
      console.error('Error disabling research:', error);
      setError('Failed to disable research. Please try again.');
      // Refresh topics to get correct state
      loadData();
    }
  };

  // Handle topic expansion
  const toggleTopic = (topicKey) => {
    const newExpandedTopics = new Set(expandedTopics);
    if (newExpandedTopics.has(topicKey)) {
      newExpandedTopics.delete(topicKey);
    } else {
      newExpandedTopics.add(topicKey);
    }
    setExpandedTopics(newExpandedTopics);
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
        researchEngineStatus={researchEngineStatus}
        onToggleGlobalResearch={handleToggleGlobalResearch}
        researchEngineLoading={researchEngineLoading}
        activeTopicsCount={activeTopicsCount}
        onImmediateResearch={handleImmediateResearch}
        immediateResearchLoading={immediateResearchLoading}
        onShowMotivation={() => setShowMotivation(true)}
        onShowEngineSettings={() => setShowEngineSettings(true)}
        onDeleteNonActivated={handleDeleteNonActivated}
        onAddCustomTopic={handleShowAddTopicForm}
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
            <div className="empty-icon">📚</div>
            <h3>No Topics Found</h3>
            <p>
              {topics.length === 0 
                ? "You haven't generated any research topics yet. Start chatting to discover interesting topics!"
                : "No topics match your current filters. Try adjusting your search criteria."
              }
            </p>
          </div>
        ) : (
          <div className="topics-list">
            {filteredAndSortedTopics.map((topic, index) => {
              const topicKey = `${topic.session_id}-${index}`;
              const isSelected = selectedTopics.has(topicKey);
              const isExpanded = expandedTopics.has(topicKey);
              
              return (
                <div key={topicKey} className={`topic-item ${isSelected ? 'selected' : ''} ${topic.is_active_research ? 'active-research' : ''}`}>
                  <div 
                    className="topic-header"
                    onClick={() => toggleTopic(topicKey)}
                  >
                    <div className="topic-info">
                      <div className="topic-title-row">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleTopicSelect(topic.session_id, index, e.target.checked);
                          }}
                          className="topic-checkbox"
                        />
                        <h3 className="topic-name">{topic.name}</h3>
                        {topic.is_expansion && (
                          <span className="auto-badge" aria-label="Auto expansion">Auto</span>
                        )}
                        {topic.is_active_research && (
                          <span className="research-status-badge">
                            <span className="badge-icon">🔬</span>
                            <span className="badge-text">RESEARCHING</span>
                          </span>
                        )}
                        {topic.expansion_status === 'paused' && (
                          <span className="expansion-status paused" aria-label="Expansion status: Paused">Paused</span>
                        )}
                        {topic.expansion_status === 'retired' && (
                          <span className="expansion-status retired" aria-label="Expansion status: Retired">Retired</span>
                        )}
                      </div>
                      <div className="topic-stats">
                        <span className="confidence-score">
                          Confidence: {(topic.confidence_score * 100).toFixed(0)}%
                        </span>
                        <span className="topic-date">
                          {formatDate(topic.suggested_at)}
                        </span>
                        {topic.session_id && (
                          <span className="session-info">
                            Session: {topic.session_id.substring(0, 8)}...
                          </span>
                        )}
                        {topic.is_expansion && topic.origin && topic.origin.parent_topic && (
                          <span className="parent-tag" aria-label={"Parent topic: " + topic.origin.parent_topic}>
                            Parent: {topic.origin.parent_topic}
                          </span>
                        )}
                        {topic.is_expansion && topic.origin && (
                          <span className="expansion-hint">
                            {topic.origin.method}{topic.origin.similarity != null ? ' · ' + Number(topic.origin.similarity).toFixed(2) : ''}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="topic-toggle">
                      <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                        ▼
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="topic-details">
                      <div className="topic-description">
                        <h4>Description</h4>
                        <p>{topic.description}</p>
                      </div>
                      {topic.is_expansion && topic.origin && topic.origin.parent_topic && (
                        <div className="parent-line">
                          Expanded from: <strong>{topic.origin.parent_topic}</strong> (depth {topic.expansion_depth})
                          {topic.origin.rationale && (
                            <p className="expansion-hint">{topic.origin.rationale}</p>
                          )}
                        </div>
                      )}
                      
                      {topic.conversation_context && (
                        <div className="topic-context">
                          <h4>Context</h4>
                          <p className="context-text">"{topic.conversation_context}"</p>
                        </div>
                      )}
                      
                      <div className="topic-actions">
                        {!topic.is_active_research ? (
                          <button
                            className="research-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEnableResearch(topic);
                            }}
                            title="Start researching this topic"
                          >
                            <span className="btn-icon">🔬</span>
                            <span className="btn-text">Start Research</span>
                          </button>
                        ) : (
                          <button
                            className="stop-research-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDisableResearch(topic);
                            }}
                            title="Stop researching this topic"
                          >
                            <span className="btn-icon">⏹️</span>
                            <span className="btn-text">Stop Research</span>
                          </button>
                        )}
                        
                        <button
                          className="delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteTopic(topic.topic_id, topic.name);
                          }}
                          title="Delete this topic"
                        >
                          <span className="btn-icon">🗑️</span>
                          <span className="btn-text">Delete</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {showMotivation && (
        <MotivationStats onClose={() => setShowMotivation(false)} />
      )}
      
      {showEngineSettings && (
        <EngineSettings onClose={() => setShowEngineSettings(false)} />
      )}
      
      {showAddTopicForm && (
        <AddTopicForm 
          isOpen={showAddTopicForm}
          onClose={handleCloseAddTopicForm}
          onTopicAdded={handleTopicAdded}
        />
      )}
    </div>
  );
};

export default TopicsDashboard; 
