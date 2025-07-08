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
  const [sessionHistory, setSessionHistory] = useState([]);
  const [messages, setMessages] = useState([
    { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
  ]);
  const [userDisplayName, setUserDisplayName] = useState('');
  const [personality, setPersonality] = useState(null);
  const [conversationTopics, setConversationTopics] = useState([]);
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');

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

    // Load stored session ID for this user
    const storedSession = localStorage.getItem(`session_id_${userId}`);
    
    // Always set the session ID (either stored or null)
    setSessionId(storedSession);

    // Load stored messages for this user's session
    const storedMessages = storedSession
      ? localStorage.getItem(`chat_messages_${userId}_${storedSession}`)
      : null;
    
    if (storedMessages) {
      try {
        setMessages(JSON.parse(storedMessages));
      } catch {
        // If parsing fails, reset to default
        setMessages([
          { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
        ]);
      }
    } else {
      // ✅ FIX: Always reset messages when no stored messages exist
      setMessages([
        { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
      ]);
    }

    // Load session history for this user
    const history = localStorage.getItem(`session_history_${userId}`);
    if (history) {
      try {
        setSessionHistory(JSON.parse(history));
      } catch {
        setSessionHistory([]);
      }
    } else {
      setSessionHistory([]);
    }
  }, [userId]);

  // Persist conversation to localStorage with better isolation
  useEffect(() => {
    // ✅ FIX: Add delay to prevent race conditions during user switching
    const persistMessages = setTimeout(() => {
      if (userId && sessionId && messages.length > 1) {
        // Only persist if messages aren't the default system message
        const isDefaultMessage = messages.length === 1 && 
          messages[0].role === 'system' && 
          messages[0].content === "Hello! I'm your AI assistant. How can I help you today?";
        
        if (!isDefaultMessage) {
          localStorage.setItem(
            `chat_messages_${userId}_${sessionId}`,
            JSON.stringify(messages)
          );
        }
      }
    }, 100); // Small delay to ensure user switching is complete

    return () => clearTimeout(persistMessages);
  }, [messages, userId, sessionId]);

  // Persist session ID
  useEffect(() => {
    if (userId && sessionId) {
      localStorage.setItem(`session_id_${userId}`, sessionId);
    }
  }, [sessionId, userId]);

  // Validate stored user ID on app startup and set guest user if none exists
  useEffect(() => {
    const validateStoredUserId = async () => {
      const storedUserId = localStorage.getItem('user_id');
      
      if (!storedUserId) {
        // No user selected, set guest user as default
        console.log('No user selected, using guest user as default');
        setUserId('guest');
        setUserDisplayName('Guest User');
        localStorage.setItem('user_id', 'guest');
        return;
      }
      
      try {
        const response = await fetch(`${API_URL}/user`, {
          headers: {
            'user-id': storedUserId
          }
        });
        
        if (response.status === 404) {
          console.log('Stored user ID is invalid, using guest user as default');
          localStorage.removeItem('user_id');
          setUserId('guest');
          setUserDisplayName('Guest User');
          localStorage.setItem('user_id', 'guest');
        }
      } catch (error) {
        console.error('Error validating stored user ID:', error);
        // On error, also fall back to guest user
        console.log('Error validating user, using guest user as default');
        setUserId('guest');
        setUserDisplayName('Guest User');
        localStorage.setItem('user_id', 'guest');
      }
    };
    
    validateStoredUserId();
  }, []);

  const updateUserId = useCallback((newUserId) => {
    if (newUserId) {
      // ✅ FIX: Clear state immediately when switching users to prevent data leakage
      if (newUserId !== userId) {
        // Reset state first to prevent showing previous user's data
        setMessages([
          { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
        ]);
        setSessionId(null);
        setConversationTopics([]);
        setSessionHistory([]);
        setUserDisplayName('');
        setPersonality(null);
      }
      
      setUserId(newUserId);
      localStorage.setItem('user_id', newUserId);
    } else {
      // Clear user data when switching to no user
      if (userId) {
        const history = localStorage.getItem(`session_history_${userId}`);
        if (history) {
          const sessions = JSON.parse(history);
          sessions.forEach((sid) => {
            localStorage.removeItem(`chat_messages_${userId}_${sid}`);
          });
        }
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

  const updateSessionId = useCallback(
    (newSessionId) => {
      setSessionId(newSessionId);
      if (newSessionId) {
        setSessionHistory((prev) => {
          if (prev.includes(newSessionId)) return prev;
          const updated = [...prev, newSessionId];
          if (userId) {
            localStorage.setItem(
              `session_history_${userId}`,
              JSON.stringify(updated)
            );
          }
          return updated;
        });
      }
    },
    [userId]
  );

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

  const updateSelectedModel = useCallback((model) => {
    setSelectedModel(model);
  }, []);

  const resetSession = useCallback(() => {
    setMessages([
      { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
    ]);
    setSessionId(null);
    setConversationTopics([]);
  }, []);

  const switchSession = useCallback(
    (sid) => {
      if (!userId) return;
      const stored = localStorage.getItem(`chat_messages_${userId}_${sid}`);
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
      setSessionId(sid);
    },
    [userId]
  );

  const startNewSession = useCallback(() => {
    if (!userId) return;

    // Generate a new session ID on the frontend to match the backend format
    const now = new Date();
    const year = now.getUTCFullYear();
    const month = String(now.getUTCMonth() + 1).padStart(2, '0');
    const day = String(now.getUTCDate()).padStart(2, '0');
    const hours = String(now.getUTCHours()).padStart(2, '0');
    const minutes = String(now.getUTCMinutes()).padStart(2, '0');
    const seconds = String(now.getUTCSeconds()).padStart(2, '0');
    // Mimic python's %f by padding milliseconds to 6 digits
    const microseconds = String(now.getUTCMilliseconds()).padStart(3, '0') + '000';

    const timestamp = `${year}${month}${day}_${hours}${minutes}${seconds}_${microseconds}`;
    const newSessionId = `${userId}-${timestamp}`;

    // Reset messages for the new session
    setMessages([
      { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" },
    ]);

    // Set the new session as active
    setSessionId(newSessionId);

    // Add to history and persist
    setSessionHistory((prev) => {
      if (prev.includes(newSessionId)) return prev;
      const updated = [...prev, newSessionId];
      localStorage.setItem(`session_history_${userId}`, JSON.stringify(updated));
      return updated;
    });
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
    selectedModel,

    // Actions
    updateUserId,
    updateSessionId,
    updateMessages,
    addMessage,
    updatePersonality,
    updateUserDisplayName,
    updateConversationTopics,
    updateSelectedModel,
    resetSession,
    switchSession,
    startNewSession,
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}; 