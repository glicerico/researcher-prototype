import axios from 'axios';

// Get API URL from environment variables with fallback for development
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Optional: Log the API URL in development for debugging
if (process.env.REACT_APP_DEBUG === 'true') {
  console.log('🔗 API URL:', API_URL);
}

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

// NEW: ID-based topic deletion (SAFE - no index mismatch)
export const deleteTopicById = async (topicId) => {
  try {
    const response = await api.delete(`/topics/topic/${topicId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting topic by ID:', error);
    throw error;
  }
};

// NEW: Delete all non-activated research topics
export const deleteNonActivatedTopics = async () => {
  try {
    const response = await api.delete('/topics/non-activated');
    return response.data;
  } catch (error) {
    console.error('Error deleting non-activated topics:', error);
    throw error;
  }
};

// NEW: Create custom research topic
export const createCustomTopic = async (topicData) => {
  try {
    const response = await api.post('/topics/custom', topicData);
    return response.data;
  } catch (error) {
    console.error('Error creating custom topic:', error);
    throw error;
  }
};

// NEW: ID-based topic research functions (SAFE - no index mismatch)
export const enableTopicResearchById = async (topicId) => {
  try {
    const response = await api.put(`/topics/topic/${topicId}/research`, null, {
      params: { enable: true }
    });
    return response.data;
  } catch (error) {
    console.error('Error enabling topic research by ID:', error);
    throw error;
  }
};

export const disableTopicResearchById = async (topicId) => {
  try {
    const response = await api.put(`/topics/topic/${topicId}/research`, null, {
      params: { enable: false }
    });
    return response.data;
  } catch (error) {
    console.error('Error disabling topic research by ID:', error);
    throw error;
  }
};

// Research findings functions
export const getResearchFindings = async (userId, topicName = null, unreadOnly = false) => {
  try {
    const params = {};
    if (topicName) params.topic_name = topicName;
    if (unreadOnly) params.unread_only = unreadOnly;

    const response = await api.get(`/research/findings/${userId}`, { params });
    console.log('Research findings response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching research findings:', error);
    throw error;
  }
};

export const markFindingAsRead = async (findingId) => {
  try {
    const response = await api.post(`/research/findings/${findingId}/mark_read`);
    return response.data;
  } catch (error) {
    console.error('Error marking finding as read:', error);
    throw error;
  }
};

// Delete research findings functions
export const deleteResearchFinding = async (findingId) => {
  try {
    const response = await api.delete(`/research/findings/${findingId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting research finding:', error);
    throw error;
  }
};

export const deleteAllTopicFindings = async (topicName) => {
  try {
    const response = await api.delete(`/research/findings/topic/${encodeURIComponent(topicName)}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting all topic findings:', error);
    throw error;
  }
};

export const getResearchEngineStatus = async () => {
  try {
    const response = await api.get('/research/status');
    return response.data;
  } catch (error) {
    console.error('Error fetching research engine status:', error);
    throw error;
  }
};

export const getMotivationStatus = async () => {
  try {
    const response = await api.get('/research/debug/motivation');
    return response.data;
  } catch (error) {
    console.error('Error fetching motivation status:', error);
    throw error;
  }
};

export const adjustMotivationDrives = async (drives) => {
  try {
    const response = await api.post('/research/debug/adjust-drives', drives);
    return response.data;
  } catch (error) {
    console.error('Error adjusting motivation drives:', error);
    throw error;
  }
};

export const updateMotivationConfig = async (config) => {
  try {
    const response = await api.post('/research/debug/update-config', config);
    return response.data;
  } catch (error) {
    console.error('Error updating motivation config:', error);
    throw error;
  }
};

export const triggerUserActivity = async () => {
  try {
    const response = await api.post('/research/debug/trigger-user-activity');
    return response.data;
  } catch (error) {
    console.error('Error triggering user activity:', error);
    throw error;
  }
};

export const simulateResearchCompletion = async (qualityScore = 0.7) => {
  try {
    const response = await api.post('/research/debug/simulate-research-completion', null, {
      params: { quality_score: qualityScore }
    });
    return response.data;
  } catch (error) {
    console.error('Error simulating research completion:', error);
    throw error;
  }
};

export const getActiveResearchTopics = async (userId) => {
  try {
    const response = await api.get(`/topics/user/${userId}/research`);
    return response.data;
  } catch (error) {
    console.error('Error fetching active research topics:', error);
    throw error;
  }
};

export const triggerManualResearch = async (userId) => {
  try {
    const response = await api.post(`/research/trigger/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Error triggering manual research:', error);
    throw error;
  }
};

// Research engine control functions
export const startResearchEngine = async () => {
  try {
    const response = await api.post('/research/control/start');
    return response.data;
  } catch (error) {
    console.error('Error starting research engine:', error);
    throw error;
  }
};

export const stopResearchEngine = async () => {
  try {
    const response = await api.post('/research/control/stop');
    return response.data;
  } catch (error) {
    console.error('Error stopping research engine:', error);
    throw error;
  }
};

export const restartResearchEngine = async () => {
  try {
    const response = await api.post('/research/control/restart');
    return response.data;
  } catch (error) {
    console.error('Error restarting research engine:', error);
    throw error;
  }
};

// Graph API functions
export const graphApi = {
  /**
   * Fetch graph data for a user or group
   * @param {string} type - "user" or "group"
   * @param {string} id - The user or group ID
   * @returns {Promise} The graph data response
   */
  fetchGraphData: async (type, id) => {
    try {
      const response = await api.post('/api/graph/fetch', {
        type,
        id
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching graph data:', error);
      throw error;
    }
  },

  /**
   * Test graph connectivity for a user
   * @param {string} userId - The user ID
   * @returns {Promise} The test result
   */
  testGraphConnectivity: async (userId) => {
    try {
      const response = await api.get(`/api/graph/test/${userId}`);
      return response.data;
    } catch (error) {
      console.error('Error testing graph connectivity:', error);
      throw error;
    }
  }
};

export default api; 