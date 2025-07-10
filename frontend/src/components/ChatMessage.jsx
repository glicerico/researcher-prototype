import React, { useState } from 'react';
import '../styles/ChatMessage.css';

const linkify = (text) => {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return text.split(urlRegex).map((part, i) => {
    if (part.match(urlRegex)) {
      return <a key={i} href={part} target="_blank" rel="noopener noreferrer">{part}</a>;
    }
    return part;
  });
};

const ChatMessage = ({ role, content, routingInfo }) => {
  const [showRoutingInfo, setShowRoutingInfo] = useState(false);
  
  const linkedContent = linkify(content);

  return (
    <div className={`message ${role}`}>
      <div className="message-content">{linkedContent}</div>
      
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