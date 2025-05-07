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
export const sendChatMessage = async (messages, model, temperature = 0.7, maxTokens = 1000, conversationId = null, personality = null) => {
  try {
    const headers = {};
    if (conversationId) {
      headers['conversation_id'] = conversationId;
    }
    
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
    
    const response = await api.post('/chat', payload, { headers });
    
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
    
    const response = await api.get('/users/me');
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