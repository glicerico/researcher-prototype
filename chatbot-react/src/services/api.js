import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Create an axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
export const sendChatMessage = async (messages, model, temperature = 0.7, maxTokens = 1000) => {
  try {
    const response = await api.post('/chat', {
      messages,
      model,
      temperature,
      max_tokens: maxTokens,
    });
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

export default api; 