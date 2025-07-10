import React from 'react';
import '../styles/ChatInput.css';

const ChatInput = ({ value, onChange, onSendMessage, disabled = false }) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() && !disabled) {
      onSendMessage(value);
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
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? "Processing..." : "Type your message here..."}
        rows={3}
        disabled={disabled}
      />
      <button 
        id="send-button" 
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className={disabled ? 'disabled' : ''}
      >
        {disabled ? 'Wait...' : 'Send'}
      </button>
    </div>
  );
};

export default ChatInput; 