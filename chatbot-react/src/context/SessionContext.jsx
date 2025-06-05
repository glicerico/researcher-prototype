import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

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
  const [sessionHistory, setSessionHistory] = useState([]);
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
      setSessionHistory([]);
      return;
    }

    // Load stored messages
    const storedHistory = localStorage.getItem(`session_history_${userId}`);
    if (storedHistory) {
      try {
        setSessionHistory(JSON.parse(storedHistory));
      } catch {
        setSessionHistory([]);
      }
    } else {
      setSessionHistory([]);
    }

    setMessages([
      { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
    ]);

    // Load stored session ID
    const storedSession = localStorage.getItem(`session_id_${userId}`);
    if (storedSession) {
      setSessionId(storedSession);
    }
  }, [userId, sessionHistory]);

  // Persist conversation to localStorage
  useEffect(() => {
    if (userId && sessionId && messages.length > 0) {
      localStorage.setItem(
        `chat_messages_${userId}_${sessionId}`,
        JSON.stringify(messages)
      );
    }
  }, [messages, userId, sessionId]);

  // Persist session ID
  useEffect(() => {
    if (userId && sessionId) {
      localStorage.setItem(`session_id_${userId}`, sessionId);
      setSessionHistory(prev => {
        const updated = prev.includes(sessionId) ? prev : [...prev, sessionId];
        localStorage.setItem(`session_history_${userId}`, JSON.stringify(updated));
        return updated;
      });
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
        sessionHistory.forEach((sid) => {
          localStorage.removeItem(`chat_messages_${userId}_${sid}`);
        });
        localStorage.removeItem(`session_history_${userId}`);
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
    if (userId && sessionId) {
      localStorage.setItem(
        `chat_messages_${userId}_${sessionId}`,
        JSON.stringify(newMessages)
      );
    }
  }, [userId, sessionId]);

  const addMessage = useCallback((message) => {
    setMessages(prev => {
      const updated = [...prev, message];
      if (userId && sessionId) {
        localStorage.setItem(
          `chat_messages_${userId}_${sessionId}`,
          JSON.stringify(updated)
        );
      }
      return updated;
    });
  }, [userId, sessionId]);

  const updatePersonality = useCallback((newPersonality) => {
    setPersonality(newPersonality);
  }, []);

  const updateUserDisplayName = useCallback((newDisplayName) => {
    setUserDisplayName(newDisplayName);
  }, []);

  const updateConversationTopics = useCallback((topics) => {
    setConversationTopics(topics);
  }, []);

  // Load messages when session changes
  useEffect(() => {
    if (userId && sessionId) {
      const stored = localStorage.getItem(`chat_messages_${userId}_${sessionId}`);
      if (stored) {
        try {
          setMessages(JSON.parse(stored));
        } catch {
          setMessages([
            { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
          ]);
        }
      } else {
        setMessages([
          { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
        ]);
      }
    }
  }, [sessionId, userId]);

  const resetSession = useCallback(() => {
    setMessages([
      { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
    ]);
    setSessionId(null);
    setConversationTopics([]);

    if (userId) {
      if (sessionId) {
        localStorage.removeItem(`chat_messages_${userId}_${sessionId}`);
      }
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
    sessionHistory,
    
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