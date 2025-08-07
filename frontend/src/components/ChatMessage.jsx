import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import '../styles/ChatMessage.css';

const ChatMessage = ({ role, content, routingInfo, followUpQuestions, onFollowUpClick }) => {
  const [showRoutingInfo, setShowRoutingInfo] = useState(false);
  const [showSources, setShowSources] = useState(false);

  // Custom link renderer to open external links in new tab
  const LinkRenderer = ({ href, children, ...props }) => {
    // Check if it's an external link
    const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
    
    if (isExternal) {
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
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

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        <ReactMarkdown components={markdownComponents}>{mainContent}</ReactMarkdown>
        {sourcesContent && (
          <div className="sources-container">
            <button 
              className="sources-toggle"
              onClick={() => setShowSources(!showSources)}
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
              
              {routingInfo.complexity && (
                <div className="routing-info-item">
                  <span className="routing-label">Complexity:</span> 
                  <span className="routing-value">{routingInfo.complexity}/10</span>
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