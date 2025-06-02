import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../styles/Navigation.css';

const Navigation = () => {
  const location = useLocation();

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <h2>AI Research Assistant</h2>
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
        </div>
      </div>
    </nav>
  );
};

export default Navigation; 