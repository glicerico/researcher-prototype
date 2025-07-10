import React, { useState } from 'react';
import '../styles/TopicSidebarItem.css';

const TopicSidebarItem = ({ topic, index, onEnableResearch, onDisableResearch, onDelete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

  // Handlers for expanded view (no event propagation stoppage)
  const handleEnableResearch = async () => {
    setActionLoading('enable');
    try {
      await onEnableResearch();
    } finally {
      setActionLoading(null);
    }
  };

  const handleDisableResearch = async () => {
    setActionLoading('disable');
    try {
      await onDisableResearch();
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Delete topic "${topic.name}"?`)) {
      setActionLoading('delete');
      try {
        await onDelete();
      } finally {
        setActionLoading(null);
      }
    }
  };
  
  // Click handlers for compact view buttons to stop event propagation
  const handleEnableResearchClick = (e) => {
    e.stopPropagation();
    handleEnableResearch();
  };
  
  const handleDisableResearchClick = (e) => {
    e.stopPropagation();
    handleDisableResearch();
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    handleDelete();
  };


  const confidencePercentage = Math.round(topic.confidence_score * 100);
  const confidenceClass = 
    topic.confidence_score >= 0.8 ? 'high' :
    topic.confidence_score >= 0.6 ? 'medium' : 'low';

  return (
    <div className={`topic-list-item ${topic.is_active_research ? 'active-research' : ''} ${isExpanded ? 'expanded' : ''}`}>
      {/* Compact Header - Always Visible */}
      <div className="topic-compact-header">
        <div className="topic-compact-info" onClick={() => setIsExpanded(!isExpanded)}>
          <div className="topic-compact-title">
            <span className="topic-name-compact" title={topic.name}>
              {topic.name}
            </span>
            {topic.is_active_research && (
              <span className="research-indicator">🔬</span>
            )}
          </div>
          <div className="topic-compact-meta">
            <span className={`confidence-compact ${confidenceClass}`}>
              {confidencePercentage}%
            </span>
          </div>
        </div>
        
        <div className="topic-compact-actions">
          <div className="topic-actions compact">
            {!topic.is_active_research ? (
                <button
                  className="action-btn research-btn"
                  onClick={handleEnableResearchClick}
                  disabled={actionLoading === 'enable'}
                  title="Start researching this topic"
                >
                  {actionLoading === 'enable' ? <span className="btn-loading">⏳</span> : <span className="btn-icon">🔬</span>}
                </button>
              ) : (
                <button
                  className="action-btn stop-research-btn"
                  onClick={handleDisableResearchClick}
                  disabled={actionLoading === 'disable'}
                  title="Stop researching this topic"
                >
                  {actionLoading === 'disable' ? <span className="btn-loading">⏳</span> : <span className="btn-icon">⏹️</span>}
                </button>
              )}
              <button
                className="action-btn delete-btn"
                onClick={handleDeleteClick}
                disabled={actionLoading === 'delete'}
                title="Remove this topic"
              >
                {actionLoading === 'delete' ? <span className="btn-loading">⏳</span> : <span className="btn-icon">🗑️</span>}
              </button>
          </div>
          <button
            className="expand-toggle"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Show less' : 'Show more'}
          >
            <span className="expand-icon">{isExpanded ? '▲' : '▼'}</span>
          </button>
        </div>
      </div>

      {/* Expanded Details - Only Visible When Expanded */}
      {isExpanded && (
        <div className="topic-expanded-content">
          {/* Description */}
          {topic.description && (
            <div className="topic-description">
              <p>{topic.description}</p>
            </div>
          )}

          {/* Confidence Bar */}
          <div className="topic-confidence">
            <div className={`confidence-bar-container ${confidenceClass}`}>
              <div 
                className="confidence-fill"
                style={{ width: `${confidencePercentage}%` }}
              ></div>
            </div>
            <span className="confidence-label">{confidencePercentage}% confidence</span>
          </div>

          {/* Action Buttons */}
          <div className="topic-actions">
            {!topic.is_active_research ? (
              <button
                className="action-btn research-btn"
                onClick={handleEnableResearch}
                disabled={actionLoading === 'enable'}
                title="Start researching this topic"
              >
                {actionLoading === 'enable' ? (
                  <span className="btn-loading">⏳</span>
                ) : (
                  <>
                    <span className="btn-icon">🔬</span>
                    <span className="btn-text">Research</span>
                  </>
                )}
              </button>
            ) : (
              <button
                className="action-btn stop-research-btn"
                onClick={handleDisableResearch}
                disabled={actionLoading === 'disable'}
                title="Stop researching this topic"
              >
                {actionLoading === 'disable' ? (
                  <span className="btn-loading">⏳</span>
                ) : (
                  <>
                    <span className="btn-icon">⏹️</span>
                    <span className="btn-text">Stop</span>
                  </>
                )}
              </button>
            )}

            <button
              className="action-btn delete-btn"
              onClick={handleDelete}
              disabled={actionLoading === 'delete'}
              title="Remove this topic"
            >
              {actionLoading === 'delete' ? (
                <span className="btn-loading">⏳</span>
              ) : (
                <>
                  <span className="btn-icon">🗑️</span>
                  <span className="btn-text">Delete</span>
                </>
              )}
            </button>
          </div>

          {/* Additional Details */}
          {(topic.conversation_context || topic.suggested_at) && (
            <div className="topic-metadata">
              {topic.conversation_context && (
                <div className="metadata-item">
                  <label>Context:</label>
                  <p className="context-text">"{topic.conversation_context}"</p>
                </div>
              )}
              
              <div className="metadata-item">
                <label>Suggested:</label>
                <span>{new Date(topic.suggested_at * 1000).toLocaleDateString()}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TopicSidebarItem; 