import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Create an axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add interceptor to add user ID to headers if available
api.interceptors.request.use(
  (config) => {
    const userId = localStorage.getItem('user_id');
    if (userId) {
      config.headers['user-id'] = userId;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Get available models
export const getModels = async () => {
  try {
    const response = await api.get('/models');
    return response.data;
  } catch (error) {
    console.error('Error fetching models:', error);
    throw error;
  }
};

// Send a chat message
export const sendChatMessage = async (messages, model, temperature = 0.7, maxTokens = 1000, personality = null, sessionId = null) => {
  try {
    const payload = {
      messages,
      model,
      temperature,
      max_tokens: maxTokens,
    };
    
    // Include personality if available
    if (personality) {
      payload.personality = personality;
    }
    
    // Include session_id if available
    if (sessionId) {
      payload.session_id = sessionId;
    }
    
    const response = await api.post('/chat', payload);
    
    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

// User management functions
export const getUsers = async () => {
  try {
    console.log('Fetching users...');
    const response = await api.get('/users');
    console.log('Users response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching users:', error);
    // Log detailed error information
    if (error.response) {
      console.error('Error response:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('No response received from server');
    }
    throw error;
  }
};

export const createUser = async (userData) => {
  try {
    const displayName = userData.display_name;
    const response = await api.post('/users', null, {
      params: { display_name: displayName }
    });
    return response.data;
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
};

export const getCurrentUser = async () => {
  try {
    console.log('Fetching current user data...');
    const userId = localStorage.getItem('user_id');
    console.log('Current user ID from localStorage:', userId);
    
    const response = await api.get('/user');
    console.log('Current user response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching current user:', error);
    // Log detailed error information
    if (error.response) {
      console.error('Error response:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('No response received from server');
    }
    throw error;
  }
};

export const updateUserDisplayName = async (displayName) => {
  try {
    const response = await api.put('/user/display-name', null, {
      params: { display_name: displayName }
    });
    return response.data;
  } catch (error) {
    console.error('Error updating user display name:', error);
    throw error;
  }
};

export const updateUserPersonality = async (personality) => {
  try {
    const response = await api.put('/user/personality', personality);
    return response.data;
  } catch (error) {
    console.error('Error updating user personality:', error);
    throw error;
  }
};

export const getPersonalityPresets = async () => {
  try {
    const response = await api.get('/personality-presets');
    return response.data;
  } catch (error) {
    console.error('Error fetching personality presets:', error);
    throw error;
  }
};

// Topic management functions
export const getAllTopicSuggestions = async () => {
  try {
    const response = await api.get('/topics/suggestions');
    return response.data;
  } catch (error) {
    console.error('Error fetching topic suggestions:', error);
    throw error;
  }
};

export const getSessionTopicSuggestions = async (sessionId) => {
  try {
    const response = await api.get(`/topics/suggestions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching session topic suggestions:', error);
    throw error;
  }
};

export const getTopicStatistics = async () => {
  try {
    const response = await api.get('/topics/stats');
    return response.data;
  } catch (error) {
    console.error('Error fetching topic statistics:', error);
    throw error;
  }
};

export const deleteSessionTopics = async (sessionId) => {
  try {
    const response = await api.delete(`/topics/session/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting session topics:', error);
    throw error;
  }
};

export const cleanupTopics = async () => {
  try {
    const response = await api.delete('/topics/cleanup');
    return response.data;
  } catch (error) {
    console.error('Error cleaning up topics:', error);
    throw error;
  }
};

export const getTopicProcessingStatus = async (sessionId) => {
  try {
    const response = await api.get(`/topics/status/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error checking topic processing status:', error);
    throw error;
  }
};

// Conversation topics sidebar functions
export const getTopSessionTopics = async (sessionId, limit = 3) => {
  try {
    const response = await api.get(`/topics/session/${sessionId}/top`, {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching top session topics:', error);
    throw error;
  }
};

export const deleteIndividualTopic = async (sessionId, topicIndex) => {
  try {
    const response = await api.delete(`/topics/session/${sessionId}/topic/${topicIndex}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting individual topic:', error);
    throw error;
  }
};

export const enableTopicResearch = async (sessionId, topicIndex) => {
  try {
    const response = await api.post(`/topics/session/${sessionId}/topic/${topicIndex}/enable-research`);
    return response.data;
  } catch (error) {
    console.error('Error enabling topic research:', error);
    throw error;
  }
};

export const disableTopicResearch = async (sessionId, topicIndex) => {
  try {
    const response = await api.delete(`/topics/session/${sessionId}/topic/${topicIndex}/disable-research`);
    return response.data;
  } catch (error) {
    console.error('Error disabling topic research:', error);
    throw error;
  }
};

export default api; 