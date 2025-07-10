import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import '../styles/ChatMessage.css';

const ChatMessage = ({ role, content, routingInfo }) => {
  const [showRoutingInfo, setShowRoutingInfo] = useState(false);
  const [showSources, setShowSources] = useState(false);

  // Split content into main response and sources
  const parts = content.split('\n\n**Sources:**');
  const mainContent = parts[0];
  const sourcesContent = parts.length > 1 ? parts[1] : null;

  return (
    <div className={`message ${role}`}>
      <div className="message-content">
        <ReactMarkdown>{mainContent}</ReactMarkdown>
        {sourcesContent && (
          <div className="sources-container">
            <button 
              className="sources-toggle"
              onClick={() => setShowSources(!showSources)}
            >
              {showSources ? 'Hide Sources' : 'Show Sources'}
            </button>
            {showSources && (
              <ReactMarkdown>{`**Sources:**${sourcesContent}`}</ReactMarkdown>
            )}
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