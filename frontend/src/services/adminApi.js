import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance for admin requests
const adminApi = axios.create({
  baseURL: `${API_BASE_URL}/admin`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
class TokenManager {
  constructor() {
    this.token = localStorage.getItem('admin_token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('admin_token', token);
    this.updateHeaders();
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('admin_token');
    this.updateHeaders();
  }

  getToken() {
    return this.token;
  }

  updateHeaders() {
    if (this.token) {
      adminApi.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
    } else {
      delete adminApi.defaults.headers.common['Authorization'];
    }
  }
}

const tokenManager = new TokenManager();
tokenManager.updateHeaders(); // Set initial headers

// Request interceptor to add token
adminApi.interceptors.request.use(
  (config) => {
    const token = tokenManager.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token expiration
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      tokenManager.clearToken();
      // Redirect to login or show login modal
      window.location.href = '/admin/login';
    }
    return Promise.reject(error);
  }
);

// Authentication APIs
export const adminLogin = async (password) => {
  try {
    const response = await adminApi.post('/login', { password });
    const { access_token } = response.data;
    tokenManager.setToken(access_token);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const verifyToken = async () => {
  try {
    const response = await adminApi.get('/verify');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const adminLogout = () => {
  tokenManager.clearToken();
};

// Prompt management APIs
export const getAllPrompts = async () => {
  try {
    const response = await adminApi.get('/prompts');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPrompt = async (promptName) => {
  try {
    const response = await adminApi.get(`/prompts/${promptName}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const updatePrompt = async (promptName, content) => {
  try {
    const response = await adminApi.put(`/prompts/${promptName}`, { content });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPromptHistory = async (promptName) => {
  try {
    const response = await adminApi.get(`/prompts/${promptName}/history`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const restorePrompt = async (promptName, backupFilename) => {
  try {
    const response = await adminApi.post(`/prompts/${promptName}/restore`, {
      backup_filename: backupFilename
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const testPrompt = async (promptName, variables) => {
  try {
    const response = await adminApi.post(`/prompts/${promptName}/test`, {
      variables
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getAdminStatus = async () => {
  try {
    const response = await adminApi.get('/status');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Flow visualization APIs
export const getFlowSummary = async () => {
  try {
    const response = await adminApi.get('/flows');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getFlowData = async (graphType) => {
  try {
    const response = await adminApi.get(`/flows/${graphType}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getNodeInfo = async (nodeId) => {
  try {
    const response = await adminApi.get(`/flows/nodes/${nodeId}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const generateFlowDiagrams = async () => {
  try {
    const response = await adminApi.post('/flows/diagrams/generate');
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getPromptUsageMap = async () => {
  try {
    const response = await adminApi.get('/flows/prompt-usage');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Utility functions
export const isAuthenticated = () => {
  return !!tokenManager.getToken();
};

export const getAuthHeaders = () => {
  const token = tokenManager.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}; 