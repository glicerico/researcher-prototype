import React from 'react';
import '../styles/TopicsHeader.css';

const TopicsHeader = ({ 
  stats, 
  selectedCount, 
  totalCount, 
  onCleanup, 
  onBulkDelete, 
  onSelectAll, 
  loading 
}) => {
  const formatDate = (days) => {
    if (days === 0) return 'today';
    if (days === 1) return '1 day ago';
    return `${days} days ago`;
  };

  return (
    <div className="topics-header">
      <div className="header-content">
        <h1>Research Topics</h1>
        <p className="header-subtitle">
          Discover and manage AI-suggested research topics from your conversations
        </p>
      </div>

      {/* Stats Overview */}
      <div className="stats-overview">
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
            {stats.average_confidence_score ? stats.average_confidence_score.toFixed(2) : '0.00'}
          </div>
          <div className="stat-label">Avg Confidence</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {stats.oldest_topic_age_days !== undefined ? formatDate(stats.oldest_topic_age_days) : 'N/A'}
          </div>
          <div className="stat-label">Oldest Topic</div>
        </div>
      </div>

      {/* Action Controls */}
      <div className="action-controls">
        <div className="selection-info">
          {selectedCount > 0 ? (
            <span className="selection-count">
              {selectedCount} of {totalCount} selected
            </span>
          ) : (
            <span className="total-count">
              {totalCount} topics shown
            </span>
          )}
        </div>

        <div className="action-buttons">
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
              className="bulk-delete-btn danger"
              onClick={onBulkDelete}
              disabled={loading}
            >
              Delete Selected ({selectedCount})
            </button>
          )}

          {/* Cleanup */}
          <button 
            className="cleanup-btn secondary"
            onClick={onCleanup}
            disabled={loading}
            title="Remove old topics and duplicates"
          >
            🧹 Cleanup Topics
          </button>
        </div>
      </div>
    </div>
  );
};

export default TopicsHeader; 