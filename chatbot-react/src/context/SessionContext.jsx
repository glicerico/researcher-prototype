import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getCurrentUser } from '../services/api';

// Get API URL from environment variables with fallback for development
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const SessionContext = createContext();

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};

export const SessionProvider = ({ children }) => {
  const [userId, setUserId] = useState(localStorage.getItem('user_id') || '');
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([
    { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
  ]);
  const [userDisplayName, setUserDisplayName] = useState('');
  const [personality, setPersonality] = useState(null);
  const [conversationTopics, setConversationTopics] = useState([]);

  // Load stored conversation and session when user changes
  useEffect(() => {
    if (!userId) {
      setMessages([
        { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
      ]);
      setSessionId(null);
      setConversationTopics([]);
      return;
    }

    // Load stored messages
    const storedMessages = localStorage.getItem(`chat_messages_${userId}`);
    if (storedMessages) {
      try {
        setMessages(JSON.parse(storedMessages));
      } catch {
        // ignore parse errors
      }
    }

    // Load stored session ID
    const storedSession = localStorage.getItem(`session_id_${userId}`);
    if (storedSession) {
      setSessionId(storedSession);
    }
  }, [userId]);

  // Persist conversation to localStorage
  useEffect(() => {
    if (userId && messages.length > 1) { // Only persist if there are actual messages
      localStorage.setItem(`chat_messages_${userId}`, JSON.stringify(messages));
    }
  }, [messages, userId]);

  // Persist session ID
  useEffect(() => {
    if (userId && sessionId) {
      localStorage.setItem(`session_id_${userId}`, sessionId);
    }
  }, [sessionId, userId]);

  // Validate stored user ID on app startup
  useEffect(() => {
    const validateStoredUserId = async () => {
      const storedUserId = localStorage.getItem('user_id');
      if (!storedUserId) return;
      
      try {
        const response = await fetch(`${API_URL}/user`, {
          headers: {
            'user-id': storedUserId
          }
        });
        
        if (response.status === 404) {
          console.log('Stored user ID is invalid, clearing localStorage');
          localStorage.removeItem('user_id');
          setUserId('');
          setUserDisplayName('');
        }
      } catch (error) {
        console.error('Error validating stored user ID:', error);
      }
    };
    
    validateStoredUserId();
  }, []);

  const updateUserId = useCallback((newUserId) => {
    if (newUserId) {
      setUserId(newUserId);
      localStorage.setItem('user_id', newUserId);
    } else {
      // Clear user data when switching to no user
      if (userId) {
        localStorage.removeItem(`chat_messages_${userId}`);
        localStorage.removeItem(`session_id_${userId}`);
      }
      setUserId('');
      localStorage.removeItem('user_id');
      setUserDisplayName('');
      setPersonality(null);
      setMessages([
        { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
      ]);
      setSessionId(null);
      setConversationTopics([]);
    }
  }, [userId]);

  const updateSessionId = useCallback((newSessionId) => {
    setSessionId(newSessionId);
  }, []);

  const updateMessages = useCallback((newMessages) => {
    setMessages(newMessages);
  }, []);

  const addMessage = useCallback((message) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const updatePersonality = useCallback((newPersonality) => {
    setPersonality(newPersonality);
  }, []);

  const updateUserDisplayName = useCallback((newDisplayName) => {
    setUserDisplayName(newDisplayName);
  }, []);

  const updateConversationTopics = useCallback((topics) => {
    setConversationTopics(topics);
  }, []);

  const resetSession = useCallback(() => {
    setMessages([
      { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
    ]);
    setSessionId(null);
    setConversationTopics([]);
    
    if (userId) {
      localStorage.removeItem(`chat_messages_${userId}`);
      localStorage.removeItem(`session_id_${userId}`);
    }
  }, [userId]);

  const value = {
    // State
    userId,
    sessionId,
    messages,
    userDisplayName,
    personality,
    conversationTopics,
    
    // Actions
    updateUserId,
    updateSessionId,
    updateMessages,
    addMessage,
    updatePersonality,
    updateUserDisplayName,
    updateConversationTopics,
    resetSession,
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}; 