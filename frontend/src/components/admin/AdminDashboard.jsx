import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllPrompts, getAdminStatus } from '../../services/adminApi';
import { useAdmin } from '../../context/AdminContext';
import PromptEditor from './PromptEditor';
import FlowVisualization from './FlowVisualization';
import '../../styles/Admin.css';

const AdminDashboard = () => {
  const [prompts, setPrompts] = useState({});
  const [categories, setCategories] = useState({});
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  
  const { logout, user } = useAdmin();
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [promptsData, statusData] = await Promise.all([
        getAllPrompts(),
        getAdminStatus()
      ]);
      
      setPrompts(promptsData.prompts);
      setCategories(promptsData.categories);
      setStatus(statusData);
    } catch (error) {
      console.error('Error loading data:', error);
      setError('Failed to load admin data. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  const handlePromptSelect = (promptName) => {
    setSelectedPrompt(promptName);
    setActiveTab('editor');
  };

  const handlePromptUpdated = () => {
    // Refresh data after prompt update
    loadData();
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading admin dashboard...</p>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <header className="admin-header">
        <div className="admin-header-left">
          <h1>🛠️ Admin Panel</h1>
          <span className="admin-subtitle">Prompt Management System</span>
        </div>
        <div className="admin-header-right">
          <span className="admin-user">👤 {user?.username}</span>
          <button onClick={() => navigate('/')} className="btn-secondary">
            🏠 Back to Chat
          </button>
          <button onClick={handleLogout} className="btn-danger">
            🚪 Logout
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          {error}
          <button onClick={() => setError('')} className="error-close">×</button>
        </div>
      )}

      <div className="admin-tabs">
        <button
          className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 Overview
        </button>
        <button
          className={`tab-button ${activeTab === 'flows' ? 'active' : ''}`}
          onClick={() => setActiveTab('flows')}
        >
          🔄 Flow Visualization
        </button>
        <button
          className={`tab-button ${activeTab === 'editor' ? 'active' : ''}`}
          onClick={() => setActiveTab('editor')}
        >
          ✏️ Prompt Editor
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'overview' && (
          <div className="overview-tab">
            {status && (
              <div className="status-section">
                <h2>📈 System Status</h2>
                <div className="status-grid">
                  <div className="status-card">
                    <div className="status-number">{status.prompts_loaded}</div>
                    <div className="status-label">Prompts Loaded</div>
                  </div>
                  <div className="status-card">
                    <div className="status-number">{status.backup_files}</div>
                    <div className="status-label">Backup Files</div>
                  </div>
                  <div className="status-card">
                    <div className="status-number">{status.categories?.length || 0}</div>
                    <div className="status-label">Categories</div>
                  </div>
                  <div className="status-card success">
                    <div className="status-number">✓</div>
                    <div className="status-label">System Healthy</div>
                  </div>
                </div>
              </div>
            )}

            <div className="prompts-section">
              <h2>📝 Prompt Categories</h2>
              <div className="categories-grid">
                {Object.entries(categories).map(([category, categoryPrompts]) => (
                  <div key={category} className="category-card">
                    <div className="category-header">
                      <h3>{getCategoryIcon(category)} {category}</h3>
                      <span className="prompt-count">{categoryPrompts.length} prompts</span>
                    </div>
                    <div className="category-prompts">
                      {categoryPrompts.map((prompt) => (
                        <div key={prompt.name} className="prompt-item">
                          <div className="prompt-info">
                            <div className="prompt-name">{prompt.name}</div>
                            <div className="prompt-description">{prompt.description}</div>
                            <div className="prompt-meta">
                              {prompt.variables.length > 0 && (
                                <span className="variables-count">
                                  🔤 {prompt.variables.length} variables
                                </span>
                              )}
                              <span className="content-length">
                                📏 {prompt.content_length} chars
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handlePromptSelect(prompt.name)}
                            className="btn-primary btn-small"
                          >
                            Edit
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'flows' && (
          <div className="flows-tab">
            <FlowVisualization onEditPrompt={handlePromptSelect} />
          </div>
        )}

        {activeTab === 'editor' && (
          <div className="editor-tab">
            {selectedPrompt ? (
              <PromptEditor
                promptName={selectedPrompt}
                onBack={() => setActiveTab('overview')}
                onPromptUpdated={handlePromptUpdated}
              />
            ) : (
              <div className="no-prompt-selected">
                <h3>📝 No Prompt Selected</h3>
                <p>Select a prompt from the Overview tab to start editing.</p>
                <button
                  onClick={() => setActiveTab('overview')}
                  className="btn-primary"
                >
                  Go to Overview
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper function to get category icons
const getCategoryIcon = (category) => {
  const icons = {
    'Router': '🚦',
    'Search': '🔍',
    'Analysis': '🔬',
    'Integrator': '🔗',
    'Response': '💬',
    'Research': '📚',
    'Topic Extraction': '🏷️',
    'Context': '🧠',
    'Other': '📄'
  };
  return icons[category] || '📄';
};

export default AdminDashboard; 