import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import '../styles/Navigation.css';

const Navigation = () => {
  const location = useLocation();
  const { sessionId, userDisplayName, messages } = useSession();

  const getMessageCount = () => {
    // Count non-system messages
    return messages.filter(msg => msg.role !== 'system').length;
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <h2>AI Research Assistant</h2>
          {sessionId && (
            <div className="session-info">
              {userDisplayName && <span className="user-name">👤 {userDisplayName}</span>}
              <span className="session-indicator">
                💬 Session: {sessionId.slice(-8)} 
                {getMessageCount() > 0 && ` (${getMessageCount()} messages)`}
              </span>
            </div>
          )}
        </div>
        
        <div className="nav-links">
          <Link 
            to="/" 
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            💬 Chat
          </Link>
          <Link 
            to="/topics" 
            className={`nav-link ${location.pathname === '/topics' ? 'active' : ''}`}
          >
            🔍 Research Topics
          </Link>
          <Link 
            to="/research-results" 
            className={`nav-link ${location.pathname === '/research-results' ? 'active' : ''}`}
          >
            📊 Research Results
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navigation; 