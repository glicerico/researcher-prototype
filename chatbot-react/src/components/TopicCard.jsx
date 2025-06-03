import React, { useState } from 'react';
import '../styles/TopicCard.css';

const TopicCard = ({ topic, isSelected, onSelect, onDelete }) => {
  const [showFullDescription, setShowFullDescription] = useState(false);
  
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
      className={`topic-card ${isSelected ? 'selected' : ''} ${getConfidenceColor(topic.confidence_score)}`}
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