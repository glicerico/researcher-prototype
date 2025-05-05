import React from 'react';
import { sendDebugRequest } from '../services/api';
import '../styles/DebugButton.css';

const DebugButton = ({ messages, selectedModel, onDebugInfo }) => {
  const handleDebugClick = async () => {
    try {
      // Add a test message if there are no user messages
      const messagesCopy = [...messages];
      if (!messagesCopy.some(m => m.role === 'user')) {
        messagesCopy.push({ role: 'user', content: 'Test message' });
      }

      const data = await sendDebugRequest(messagesCopy, selectedModel);
      
      // Display debug info in console
      console.log('Debug info:', data);
      
      // Pass debug info to parent component
      onDebugInfo(data);
    } catch (error) {
      console.error('Debug error:', error);
      alert(`Debug error: ${error.message}`);
    }
  };

  return (
    <button className="debug-button" onClick={handleDebugClick}>
      Debug
    </button>
  );
};

export default DebugButton; 