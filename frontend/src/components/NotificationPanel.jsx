import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';
import '../styles/NotificationPanel.css';

const NotificationPanel = () => {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef(null);
  const navigate = useNavigate();
  const { 
    notifications, 
    getUnreadCount, 
    markNotificationRead, 
    markAllRead, 
    clearNotifications,
    connectionStatus 
  } = useNotifications();

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const togglePanel = () => {
    setIsOpen(prev => !prev);
  };

  const handleNotificationClick = (notification) => {
    if (!notification.read) {
      markNotificationRead(notification.id);
    }
    
    // Close the panel first
    setIsOpen(false);
    
    // Navigate to relevant page based on notification type
    if (notification.type === 'new_research' || notification.type === 'research_complete') {
      // Small delay to ensure panel closes smoothly before navigation
      setTimeout(() => {
        navigate('/research-results');
      }, 100);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;
    
    return date.toLocaleDateString();
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'new_research':
        return '🔬';
      case 'research_complete':
        return '✅';
      case 'system_status':
        return '⚙️';
      default:
        return '📢';
    }
  };

  const unreadCount = getUnreadCount();

  return (
    <div className="notification-panel" ref={panelRef}>
      <button 
        className={`notification-trigger ${isOpen ? 'active' : ''}`}
        onClick={togglePanel}
        title="Notifications"
      >
        <span className="notification-icon">🔔</span>
        {unreadCount > 0 && (
          <span className="notification-count">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
        <span className={`connection-status ${connectionStatus}`} 
              title={`WebSocket: ${connectionStatus}`}>
        </span>
      </button>

      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notifications</h3>
            <div className="notification-actions">
              {unreadCount > 0 && (
                <button 
                  className="mark-all-read"
                  onClick={markAllRead}
                  title="Mark all as read"
                >
                  ✓
                </button>
              )}
              {notifications.length > 0 && (
                <button 
                  className="clear-all"
                  onClick={clearNotifications}
                  title="Clear all notifications"
                >
                  🗑️
                </button>
              )}
            </div>
          </div>

          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="no-notifications">
                <span className="no-notifications-icon">🔕</span>
                <p>No notifications yet</p>
                <small>You'll see research updates here</small>
              </div>
            ) : (
              notifications.map(notification => (
                <div 
                  key={notification.id}
                  className={`notification-item ${notification.read ? 'read' : 'unread'}`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="notification-content">
                    <div className="notification-icon-wrapper">
                      <span className="notification-type-icon">
                        {getNotificationIcon(notification.type)}
                      </span>
                      {!notification.read && <span className="unread-dot"></span>}
                    </div>
                    
                    <div className="notification-text">
                      <div className="notification-title">{notification.title}</div>
                      <div className="notification-message">{notification.message}</div>
                      <div className="notification-time">
                        {formatTimestamp(notification.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {notifications.length > 5 && (
            <div className="notification-footer">
              <small>Showing recent notifications</small>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationPanel;