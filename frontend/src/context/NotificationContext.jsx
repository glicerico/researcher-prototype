import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const NotificationContext = createContext();

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [newResearchCount, setNewResearchCount] = useState(0);
  // Removed unused lastSeenTimestamp state
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second

  // Get user ID from localStorage (matches the pattern used in api.js)
  const getUserId = () => {
    return localStorage.getItem('user_id') || 'anonymous';
  };

  const connectWebSocket = () => {
    const userId = getUserId();
    
    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = process.env.NODE_ENV === 'production' ? '' : ':8000';
    const wsUrl = `${protocol}//${host}${port}/ws/notifications?user-id=${userId}`;
    
    console.log('📡 Connecting to notifications WebSocket:', wsUrl);
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('📡 Notifications WebSocket connected');
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('📡 Received notification:', message);
          
          handleNotificationMessage(message);
        } catch (error) {
          console.error('📡 Error parsing notification message:', error);
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('📡 Notifications WebSocket closed:', event.code, event.reason);
        setConnectionStatus('disconnected');
        
        // Attempt to reconnect unless it was a deliberate close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          scheduleReconnect();
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('📡 Notifications WebSocket error:', error);
        setConnectionStatus('error');
      };
      
    } catch (error) {
      console.error('📡 Error creating WebSocket connection:', error);
      setConnectionStatus('error');
      scheduleReconnect();
    }
  };

  const scheduleReconnect = () => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.log('📡 Max reconnection attempts reached');
      setConnectionStatus('failed');
      return;
    }
    
    const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts.current);
    reconnectAttempts.current++;
    
    console.log(`📡 Scheduling reconnect attempt ${reconnectAttempts.current} in ${delay}ms`);
    setConnectionStatus('reconnecting');
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connectWebSocket();
    }, delay);
  };

  const handleNotificationMessage = (message) => {
    const { type, data } = message;
    
    switch (type) {
      case 'connection_established':
        console.log('📡 Connection established for user:', data.user_id);
        break;
        
      case 'heartbeat':
        // Just acknowledge heartbeat, no action needed
        break;
        
      case 'new_research':
        handleNewResearchNotification(data);
        break;
        
      case 'research_complete':
        handleResearchCompleteNotification(data);
        break;
        
      case 'system_status':
        handleSystemStatusNotification(data);
        break;
        
      default:
        console.log('📡 Unknown notification type:', type);
    }
  };

  const handleNewResearchNotification = (data) => {
    const { topic_id, result_id, topic_name, timestamp } = data;
    
    // Add to notifications list
    const notification = {
      id: `research_${result_id}`,
      type: 'new_research',
      title: 'New Research Available',
      message: `New findings for "${topic_name || topic_id}"`,
      timestamp: new Date(timestamp),
      data: { topic_id, result_id, topic_name },
      read: false
    };
    
    setNotifications(prev => [notification, ...prev.slice(0, 49)]); // Keep max 50 notifications
    setNewResearchCount(prev => prev + 1);
    
    // Show toast notification
    showToast(notification);
  };

  const handleResearchCompleteNotification = (data) => {
    const { topic_id, results_count, topic_name, timestamp } = data;
    
    const notification = {
      id: `complete_${topic_id}_${timestamp}`,
      type: 'research_complete',
      title: 'Research Cycle Complete',
      message: `Found ${results_count} new results for "${topic_name || topic_id}"`,
      timestamp: new Date(timestamp),
      data: { topic_id, results_count, topic_name },
      read: false
    };
    
    setNotifications(prev => [notification, ...prev.slice(0, 49)]);
    showToast(notification);
  };

  const handleSystemStatusNotification = (data) => {
    const { status, details, timestamp } = data;
    
    const notification = {
      id: `system_${timestamp}`,
      type: 'system_status',
      title: 'System Update',
      message: `System status: ${status}`,
      timestamp: new Date(timestamp),
      data: { status, details },
      read: false
    };
    
    setNotifications(prev => [notification, ...prev.slice(0, 49)]);
    
    // Only show toast for important system notifications
    if (status === 'maintenance' || status === 'error') {
      showToast(notification);
    }
  };

  const showToast = (notification) => {
    // This will be handled by the toast component
    // For now, we'll dispatch a custom event
    window.dispatchEvent(new CustomEvent('showToast', { 
      detail: notification 
    }));
  };

  const markNotificationRead = (notificationId) => {
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === notificationId 
          ? { ...notif, read: true }
          : notif
      )
    );
  };

  const markAllRead = () => {
    setNotifications(prev => 
      prev.map(notif => ({ ...notif, read: true }))
    );
    setNewResearchCount(0);
  };

  const markResearchNotificationsRead = () => {
    setNotifications(prev => 
      prev.map(notif => 
        (notif.type === 'new_research' || notif.type === 'research_complete')
          ? { ...notif, read: true }
          : notif
      )
    );
    // Recalculate unread count
    setNewResearchCount(prev => {
      const researchNotifs = notifications.filter(n => 
        (n.type === 'new_research' || n.type === 'research_complete') && !n.read
      );
      return Math.max(0, prev - researchNotifs.length);
    });
  };

  const clearNotifications = () => {
    setNotifications([]);
    setNewResearchCount(0);
  };

  const getUnreadCount = () => {
    return notifications.filter(notif => !notif.read).length;
  };

  // Connect on mount and cleanup on unmount
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connectWebSocket]);

  // Send periodic heartbeat to keep connection alive
  useEffect(() => {
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(heartbeatInterval);
  }, []);

  const value = {
    notifications,
    connectionStatus,
    newResearchCount,
    getUnreadCount,
    markNotificationRead,
    markAllRead,
    markResearchNotificationsRead,
    clearNotifications,
    reconnect: connectWebSocket
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};