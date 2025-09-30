import React from 'react';
import '../styles/TopicsHeader.css';

const TopicsHeader = ({ 
  stats, 
  selectedCount, 
  totalCount, 
  onCleanup, 
  onBulkDelete, 
  onSelectAll, 
  loading,
  researchEngineStatus,
  onToggleGlobalResearch,
  researchEngineLoading,
  activeTopicsCount,
  onImmediateResearch,
  immediateResearchLoading,
  onShowMotivation,
  onShowEngineSettings,
  onDeleteNonActivated,
  onAddCustomTopic
}) => {


  // Determine immediate research button state
  const isResearchEngineRunning = true;
  const hasActiveTopics = activeTopicsCount > 0;
  const isImmediateResearchDisabled = immediateResearchLoading || loading || !isResearchEngineRunning || !hasActiveTopics;
  
  const getImmediateResearchTooltip = () => {
    if (!isResearchEngineRunning) {
      return 'Research engine is not running. Enable it first.';
    }
    if (!hasActiveTopics) {
      return 'No active research topics. Enable research on topics first.';
    }
    return `Research ${activeTopicsCount} active topic${activeTopicsCount > 1 ? 's' : ''} immediately`;
  };

  return (
    <div className="topics-header">
      {/* Header Content */}
      <div className="header-content">
        <h1>Research Topics</h1>
        <p className="header-subtitle">
          Discover and manage AI-suggested research topics from your conversations
        </p>
      </div>

      {/* Stats Overview */}
      <div className="stats-overview">
        <div className="stat-card highlight">
          <div className="stat-number">{activeTopicsCount}</div>
          <div className="stat-label">Active Research</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.total_topics || 0}</div>
          <div className="stat-label">Total Topics</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.total_sessions || 0}</div>
          <div className="stat-label">Sessions</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {stats.average_confidence_score ? stats.average_confidence_score.toFixed(1) : '0.0'}
          </div>
          <div className="stat-label">Avg Confidence</div>
        </div>
      </div>

      {/* Global engine status removed; per-user autonomy handles scheduling */}

      {/* Action Controls */}
      <div className="action-controls">
        <div className="selection-info">
          {selectedCount > 0 ? (
            <span className="selection-count">
              {selectedCount} of {totalCount} selected
            </span>
          ) : (
            <span className="total-count">
              {totalCount} topic{totalCount !== 1 ? 's' : ''} shown
            </span>
          )}
        </div>

        <div className="action-buttons">
          {/* Add Custom Topic */}
          <button 
            className="add-custom-topic-btn"
            onClick={onAddCustomTopic}
            disabled={loading}
            title="Add a custom research topic"
          >
            ➕ Add Topic
          </button>

          {/* Selection Controls */}
          {totalCount > 0 && (
            <button 
              className="select-all-btn"
              onClick={onSelectAll}
              disabled={loading}
            >
              {selectedCount === totalCount ? 'Deselect All' : 'Select All'}
            </button>
          )}

          {/* Bulk Actions */}
          {selectedCount > 0 && (
            <button 
              className="bulk-delete-btn"
              onClick={onBulkDelete}
              disabled={loading}
            >
              Delete Selected ({selectedCount})
            </button>
          )}

          {/* Cleanup */}
          <button 
            className="cleanup-btn"
            onClick={onCleanup}
            disabled={loading}
            title="Remove old topics and duplicates"
          >
            🧹 Cleanup
          </button>

          {/* Delete Non-Activated Topics */}
          <button 
            className="delete-non-activated-btn"
            onClick={onDeleteNonActivated}
            disabled={loading}
            title="Delete all topics that are not activated for research"
          >
            🗑️ Delete Inactive
          </button>
        </div>
      </div>
    </div>
  );
};

export default TopicsHeader; 