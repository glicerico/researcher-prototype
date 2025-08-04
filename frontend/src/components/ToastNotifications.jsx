import React, { useState, useEffect } from 'react';
import '../styles/ToastNotifications.css';

const ToastNotifications = () => {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const handleShowToast = (event) => {
      const notification = event.detail;
      
      const toast = {
        id: `toast_${Date.now()}_${Math.random()}`,
        notification,
        timestamp: Date.now()
      };
      
      setToasts(prev => [...prev, toast]);
      
      // Auto-remove toast after 5 seconds
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, 5000);
    };

    window.addEventListener('showToast', handleShowToast);
    
    return () => {
      window.removeEventListener('showToast', handleShowToast);
    };
  }, []);

  const removeToast = (toastId) => {
    setToasts(prev => prev.filter(t => t.id !== toastId));
  };

  const getToastIcon = (type) => {
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

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map(toast => (
        <div 
          key={toast.id} 
          className={`toast toast-${toast.notification.type}`}
          onClick={() => removeToast(toast.id)}
        >
          <div className="toast-content">
            <div className="toast-icon">
              {getToastIcon(toast.notification.type)}
            </div>
            <div className="toast-text">
              <div className="toast-title">{toast.notification.title}</div>
              <div className="toast-message">{toast.notification.message}</div>
            </div>
            <button 
              className="toast-close"
              onClick={(e) => {
                e.stopPropagation();
                removeToast(toast.id);
              }}
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ToastNotifications;