import React, { useState } from 'react';
import '../styles/TopicSidebarItem.css';

const TopicSidebarItem = ({ topic, index, onEnableResearch, onDisableResearch, onDelete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

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

  const confidencePercentage = Math.round(topic.confidence_score * 100);
  const confidenceClass = 
    topic.confidence_score >= 0.8 ? 'high' :
    topic.confidence_score >= 0.6 ? 'medium' : 'low';

  return (
    <div className={`topic-list-item ${topic.is_active_research ? 'active-research' : ''}`}>
      <div className="topic-main-content">
        {/* Topic Header Row */}
        <div className="topic-header-row">
          <div className="topic-info">
            <div className="topic-title">
              <h4 className="topic-name" title={topic.name}>
                {topic.name}
              </h4>
              {topic.is_active_research && (
                <span className="research-status-badge">
                  <span className="badge-icon">🔬</span>
                  <span className="badge-text">RESEARCHING</span>
                </span>
              )}
            </div>
            
            <div className="topic-confidence">
              <div className={`confidence-bar-container ${confidenceClass}`}>
                <div 
                  className="confidence-fill"
                  style={{ width: `${confidencePercentage}%` }}
                ></div>
              </div>
              <span className="confidence-label">{confidencePercentage}% confidence</span>
            </div>

            {topic.description && (
              <p className="topic-description-preview">
                {topic.description.length > 120 ? topic.description.substring(0, 120) + '...' : topic.description}
              </p>
            )}
          </div>

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
                </>
              )}
            </button>

            <button
              className="action-btn expand-btn"
              onClick={() => setIsExpanded(!isExpanded)}
              title={isExpanded ? 'Show less' : 'Show more'}
            >
              <span className="btn-icon">{isExpanded ? '▲' : '▼'}</span>
            </button>
          </div>
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="topic-details-expanded">
            <div className="details-grid">
              {topic.description && (
                <div className="detail-section">
                  <label className="detail-label">Full Description</label>
                  <p className="detail-content">{topic.description}</p>
                </div>
              )}

              {topic.conversation_context && (
                <div className="detail-section">
                  <label className="detail-label">Context from Conversation</label>
                  <p className="detail-content context-text">
                    "{topic.conversation_context}"
                  </p>
                </div>
              )}

              <div className="detail-section">
                <label className="detail-label">Topic Metadata</label>
                <div className="metadata-grid">
                  <div className="metadata-item">
                    <span className="metadata-key">Confidence:</span>
                    <span className="metadata-value">{confidencePercentage}%</span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-key">Suggested:</span>
                    <span className="metadata-value">
                      {new Date(topic.suggested_at * 1000).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-key">Status:</span>
                    <span className="metadata-value">
                      {topic.is_active_research ? 'Active Research' : 'Suggested'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TopicSidebarItem; 