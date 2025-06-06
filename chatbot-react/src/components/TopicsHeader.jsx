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
  onShowEngineSettings
}) => {


  // Determine immediate research button state
  const isResearchEngineRunning = researchEngineStatus?.running || false;
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

      {/* Research Engine Status */}
      {researchEngineStatus && (
        <div className="research-engine-status">
          <div className="status-indicator">
            <div className={`status-dot ${researchEngineStatus.running ? 'active' : 'inactive'}`}></div>
            <span className="status-text">
              Research Engine: {researchEngineStatus.running ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="engine-controls">
            <button 
              className={`engine-toggle-btn ${researchEngineStatus.running ? 'stop' : 'start'}`}
              onClick={onToggleGlobalResearch}
              disabled={researchEngineLoading || loading}
            >
              <span className="btn-icon">
                {researchEngineStatus.running ? '⏹️' : '▶️'}
              </span>
              <span className="btn-text">
                {researchEngineLoading ? (
                  researchEngineStatus.running ? 'Stopping...' : 'Starting...'
                ) : (
                  researchEngineStatus.running ? (
                    <>Stop<br />Engine</>
                  ) : (
                    <>Enable<br />Engine</>
                  )
                )}
              </span>
            </button>
            
            <button 
              className="immediate-research-button"
              onClick={onImmediateResearch}
              disabled={isImmediateResearchDisabled}
              title={getImmediateResearchTooltip()}
            >
              <span className="btn-icon">
                {immediateResearchLoading ? '🔄' : '🚀'}
              </span>
              <span className="btn-text">
                {immediateResearchLoading ? (
                  <>Searching...</>
                ) : (
                  <>Run<br />Now</>
                )}
              </span>
            </button>
            
            <button
              className="motivation-button"
              onClick={onShowMotivation}
              title="View motivation drives and research impetus"
            >
              <span className="btn-icon">💡</span>
              <span className="btn-text">
                View<br />Drives
              </span>
            </button>
            
            <button
              className="help-button"
              onClick={onShowEngineSettings}
              title="Configure research timing and frequency presets"
            >
              <span className="btn-icon">⏰</span>
              <span className="btn-text">
                Research<br />Timing
              </span>
            </button>
          </div>
        </div>
      )}

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
        </div>
      </div>
    </div>
  );
};

export default TopicsHeader; 