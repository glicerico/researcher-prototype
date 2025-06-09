import React, { useState } from 'react';
import '../styles/TopicCard.css';

const TopicCard = ({ 
  topic, 
  index, 
  isSelected, 
  onSelect, 
  onDelete, 
  onEnableResearch, 
  onDisableResearch 
}) => {
  const [showFullDescription, setShowFullDescription] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  
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

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    return 'low';
  };

  const getConfidenceLabel = (score) => {
    if (score >= 0.8) return 'High confidence';
    if (score >= 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  const truncateText = (text, maxLength = 120) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const handleEnableResearch = async (e) => {
    e.stopPropagation();
    setActionLoading('enable');
    try {
      await onEnableResearch();
    } finally {
      setActionLoading(null);
    }
  };

  const handleDisableResearch = async (e) => {
    e.stopPropagation();
    setActionLoading('disable');
    try {
      await onDisableResearch();
    } finally {
      setActionLoading(null);
    }
  };

  const handleCardClick = (e) => {
    // Don't expand if clicking on interactive elements
    if (e.target.closest('.topic-actions') || 
        e.target.closest('.topic-checkbox') ||
        e.target.closest('.confidence-badge')) {
      return;
    }
    setShowFullDescription(!showFullDescription);
  };

  return (
    <div 
      className={`topic-card ${isSelected ? 'selected' : ''} ${getConfidenceColor(topic.confidence_score)} ${topic.is_active_research ? 'active-research' : ''}`}
      onClick={handleCardClick}
    >
      {/* Selection Checkbox */}
      <div className="topic-checkbox">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(e.target.checked)}
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Topic Header */}
      <div className="topic-header">
        <h3 className="topic-name" title={topic.name}>
          {topic.name}
          {topic.is_active_research && (
            <span className="research-status-badge">
              <span className="badge-icon">🔬</span>
              <span className="badge-text">RESEARCHING</span>
            </span>
          )}
        </h3>
        <div className="topic-meta">
          <div 
            className={`confidence-badge confidence-${getConfidenceColor(topic.confidence_score)}`}
            title={getConfidenceLabel(topic.confidence_score)}
          >
            <div className="confidence-bar">
              <div 
                className="confidence-fill"
                style={{ width: `${topic.confidence_score * 100}%` }}
              ></div>
            </div>
            <span className="confidence-score">
              {(topic.confidence_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Topic Description */}
      <div className="topic-description">
        <p>
          {showFullDescription ? topic.description : truncateText(topic.description)}
        </p>
        {topic.description && topic.description.length > 120 && (
          <button 
            className="expand-btn"
            onClick={(e) => {
              e.stopPropagation();
              setShowFullDescription(!showFullDescription);
            }}
          >
            {showFullDescription ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {/* Topic Footer */}
      <div className="topic-footer">
        <div className="topic-info">
          <span className="topic-date" title={`Suggested at: ${formatDate(topic.suggested_at)}`}>
            📅 {formatDate(topic.suggested_at)}
          </span>
          {topic.session_id && (
            <span className="session-id" title={`Session: ${topic.session_id}`}>
              💬 {topic.session_id.substring(0, 8)}...
            </span>
          )}
        </div>

        {/* Context Preview */}
        {topic.conversation_context && (
          <div className="context-preview">
            <span className="context-label">Context:</span>
            <span className="context-text" title={topic.conversation_context}>
              "{truncateText(topic.conversation_context, 60)}"
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="topic-actions">
          {/* Research Actions */}
          {onEnableResearch && onDisableResearch && (
            <>
              {!topic.is_active_research ? (
                <button
                  className="research-btn"
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
                  className="stop-research-btn"
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
            </>
          )}
          
          <button
            className="delete-btn"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            title="Delete this topic"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>
  );
};

export default TopicCard; 