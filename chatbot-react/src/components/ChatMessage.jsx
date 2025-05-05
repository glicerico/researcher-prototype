import React from 'react';
import '../styles/ChatMessage.css';

const ChatMessage = ({ role, content }) => {
  return (
    <div className={`message ${role}`}>
      <div className="message-content">{content}</div>
    </div>
  );
};

export default ChatMessage; 