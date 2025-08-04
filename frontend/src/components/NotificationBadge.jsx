import React from 'react';
import { useNotifications } from '../context/NotificationContext';
import '../styles/NotificationBadge.css';

const NotificationBadge = ({ className = '', onClick = null }) => {
  const { getUnreadCount } = useNotifications();
  const unreadCount = getUnreadCount();

  if (unreadCount === 0) return null;

  const displayCount = unreadCount > 99 ? '99+' : unreadCount.toString();

  return (
    <span 
      className={`notification-badge ${className}`}
      onClick={onClick}
      title={`${unreadCount} unread notification${unreadCount === 1 ? '' : 's'}`}
    >
      {displayCount}
    </span>
  );
};

export default NotificationBadge;