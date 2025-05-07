import React, { useState } from 'react';
import '../styles/ChatInput.css';

const ChatInput = ({ onSendMessage, disabled = false }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !disabled) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className={`chat-input-container ${disabled ? 'disabled' : ''}`}>
      <textarea
        id="user-input"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? "Processing..." : "Type your message here..."}
        rows={3}
        disabled={disabled}
      />
      <button 
        id="send-button" 
        onClick={handleSubmit}
        disabled={disabled || !message.trim()}
        className={disabled ? 'disabled' : ''}
      >
        {disabled ? 'Wait...' : 'Send'}
      </button>
    </div>
  );
};

export default ChatInput; 