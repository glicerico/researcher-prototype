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
      config.headers['X-User-ID'] = userId;
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
export const sendChatMessage = async (messages, model, temperature = 0.7, maxTokens = 1000, conversationId = null) => {
  try {
    const headers = {};
    if (conversationId) {
      headers['conversation_id'] = conversationId;
    }
    
    const response = await api.post('/chat', {
      messages,
      model,
      temperature,
      max_tokens: maxTokens,
    }, { headers });
    
    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

// Debug endpoint
export const sendDebugRequest = async (messages, model) => {
  try {
    const response = await api.post('/debug', {
      messages,
      model,
      temperature: 0.7,
      max_tokens: 1000,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending debug request:', error);
    throw error;
  }
};

// User management functions
export const getUsers = async () => {
  try {
    const response = await api.get('/users');
    return response.data;
  } catch (error) {
    console.error('Error fetching users:', error);
    throw error;
  }
};

export const createUser = async (displayName) => {
  try {
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
    const response = await api.get('/users/me');
    return response.data;
  } catch (error) {
    console.error('Error fetching current user:', error);
    throw error;
  }
};

export const updateUserDisplayName = async (userId, displayName) => {
  try {
    const response = await api.patch(`/users/${userId}/display-name`, null, {
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
    const response = await api.patch('/users/me/personality', personality);
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

export default api; 