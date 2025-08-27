import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import '../styles/ChatMessage.css';
import { trackEngagement } from '../utils/engagementTracker';

const ChatMessage = ({ role, content, routingInfo, followUpQuestions, onFollowUpClick, messageId }) => {
  const [showRoutingInfo, setShowRoutingInfo] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Custom link renderer to open external links in new tab
  const LinkRenderer = ({ href, children, ...props }) => {
    // Check if it's an external link
    const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
    
    if (isExternal) {
      return (
        <a 
          href={href} 
          target="_blank" 
          rel="noopener noreferrer" 
          onClick={(e) => e.stopPropagation()} // Prevent parent click handlers from interfering
          {...props}
        >
          {children}
        </a>
      );
    }
    
    // Internal links or non-http links use default behavior
    return <a href={href} {...props}>{children}</a>;
  };

  // ReactMarkdown components configuration
  const markdownComponents = {
    a: LinkRenderer
  };

  // Split content into main response and sources
  const parts = content.split('\n\n**Sources:**');
  const mainContent = parts[0];
  const sourcesContent = parts.length > 1 ? parts[1] : null;

  const handleFeedback = async (type) => {
    if (feedback === type) return; // Already provided this feedback
    
    setFeedback(type);
    console.log('👤 ChatMessage: ✅ User feedback recorded:', type, 'for message:', messageId);
    
    // Track engagement with feedback
    await trackEngagement({
      type: 'feedback',
      messageId: messageId,
      feedback: type,
      timestamp: Date.now()
    });
  };

  const handleSourcesToggle = async () => {
    setShowSources(!showSources);
    
    if (!showSources) {
      console.log('👤 ChatMessage: ✅ Source exploration tracked for message:', messageId);
      
      // Track source exploration
      await trackEngagement({
        type: 'source_exploration',
        messageId: messageId,
        timestamp: Date.now()
      });
    }
  };

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        <ReactMarkdown components={markdownComponents}>{mainContent}</ReactMarkdown>
        {sourcesContent && (
          <div className="sources-container">
            <button 
              className="sources-toggle"
              onClick={handleSourcesToggle}
            >
              {showSources ? 'Hide Sources' : 'Show Sources'}
            </button>
            {showSources && (
              <ReactMarkdown components={markdownComponents}>{`**Sources:**${sourcesContent}`}</ReactMarkdown>
            )}
          </div>
        )}
        {followUpQuestions && followUpQuestions.length > 0 && (
            <div className="follow-up-container">
                <h4 className="follow-up-header">Suggested Follow-Up Questions:</h4>
                <div className="follow-up-questions">
                {followUpQuestions.map((question, index) => (
                    <button 
                        key={index} 
                        className="follow-up-question"
                        onClick={() => onFollowUpClick(question)}
                    >
                    {question}
                    </button>
                ))}
                </div>
            </div>
        )}
        
        {/* Feedback buttons for assistant responses */}
        {role === 'assistant' && (
          <div className="feedback-container">
            <button 
              className={`feedback-btn ${feedback === 'up' ? 'active' : ''}`}
              onClick={() => handleFeedback('up')}
              disabled={feedback === 'up'}
            >
              👍 {feedback === 'up' ? 'Thanks!' : 'Helpful'}
            </button>
            <button 
              className={`feedback-btn ${feedback === 'down' ? 'active' : ''}`}
              onClick={() => handleFeedback('down')}
              disabled={feedback === 'down'}
            >
              👎 {feedback === 'down' ? 'Noted' : 'Not helpful'}
            </button>
          </div>
        )}
      </div>
      
      {role === 'assistant' && routingInfo && (
        <div className="message-metadata">
          <button 
            className="routing-info-toggle"
            onClick={() => setShowRoutingInfo(!showRoutingInfo)}
          >
            {showRoutingInfo ? 'Hide Routing Info' : 'Show Routing Info'}
          </button>
          
          {showRoutingInfo && (
            <div className="routing-info">
              <div className="routing-info-item">
                <span className="routing-label">Module:</span> 
                <span className="routing-value">{routingInfo.decision || routingInfo.module_used}</span>
              </div>
              
              {routingInfo.reason && (
                <div className="routing-info-item">
                  <span className="routing-label">Reason:</span> 
                  <span className="routing-value">{routingInfo.reason}</span>
                </div>
              )}
              

              
              {routingInfo.model_used && (
                <div className="routing-info-item">
                  <span className="routing-label">Router Model:</span> 
                  <span className="routing-value">{routingInfo.model_used}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatMessage; 