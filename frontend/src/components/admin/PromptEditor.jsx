import React, { useState, useEffect } from 'react';
import { getPrompt, updatePrompt, testPrompt, getPromptHistory, restorePrompt } from '../../services/adminApi';
import '../../styles/Admin.css';

const PromptEditor = ({ promptName, onBack, onPromptUpdated }) => {
  const [prompt, setPrompt] = useState(null);
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  
  // Test variables state
  const [testVariables, setTestVariables] = useState({});
  const [testResult, setTestResult] = useState(null);
  
  // History state
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    loadPrompt();
  }, [promptName]);

  useEffect(() => {
    setHasChanges(content !== originalContent);
  }, [content, originalContent]);

  const loadPrompt = async () => {
    try {
      setLoading(true);
      const promptData = await getPrompt(promptName);
      setPrompt(promptData);
      setContent(promptData.content);
      setOriginalContent(promptData.content);
      
      // Initialize test variables with empty values
      const initialTestVars = {};
      promptData.variables.forEach(variable => {
        initialTestVars[variable] = getDefaultValueForVariable(variable);
      });
      setTestVariables(initialTestVars);
      
    } catch (error) {
      console.error('Error loading prompt:', error);
      setError('Failed to load prompt. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const historyData = await getPromptHistory(promptName);
      setHistory(historyData.history);
      setShowHistory(true);
    } catch (error) {
      console.error('Error loading history:', error);
      setError('Failed to load prompt history.');
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');
      
      await updatePrompt(promptName, content);
      setOriginalContent(content);
      setSuccess('Prompt saved successfully! ✅');
      onPromptUpdated();
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000);
      
    } catch (error) {
      console.error('Error saving prompt:', error);
      setError('Failed to save prompt. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setError('');
      
      const result = await testPrompt(promptName, testVariables);
      setTestResult(result.test_result);
      
    } catch (error) {
      console.error('Error testing prompt:', error);
      setError('Failed to test prompt. Please try again.');
    } finally {
      setTesting(false);
    }
  };

  const handleRestore = async (backupFilename) => {
    if (!window.confirm('Are you sure you want to restore this version? Current changes will be lost.')) {
      return;
    }

    try {
      await restorePrompt(promptName, backupFilename);
      setSuccess('Prompt restored successfully! ✅');
      loadPrompt(); // Reload the prompt
      setShowHistory(false);
      onPromptUpdated();
      
    } catch (error) {
      console.error('Error restoring prompt:', error);
      setError('Failed to restore prompt. Please try again.');
    }
  };

  const handleVariableChange = (variable, value) => {
    setTestVariables(prev => ({
      ...prev,
      [variable]: value
    }));
  };

  // Helper function to get default values for variables
  const getDefaultValueForVariable = (variable) => {
    const defaults = {
      'current_time': new Date().toISOString(),
      'topic_name': 'Artificial Intelligence',
      'topic_description': 'Recent developments in AI technology',
      'user_query': 'What are the latest AI trends?',
      'search_result_text': 'AI technology continues to advance rapidly...',
      'analysis_result_text': 'Based on the analysis, key findings include...',
      'memory_context': 'Previous conversation about AI developments',
      'style': 'helpful',
      'tone': 'friendly',
      'module_used': 'search'
    };
    return defaults[variable] || `Sample ${variable}`;
  };

  if (loading) {
    return (
      <div className="prompt-editor-loading">
        <div className="loading-spinner"></div>
        <p>Loading prompt editor...</p>
      </div>
    );
  }

  if (!prompt) {
    return (
      <div className="prompt-editor-error">
        <h3>❌ Prompt Not Found</h3>
        <p>The requested prompt could not be loaded.</p>
        <button onClick={onBack} className="btn-secondary">
          ← Back to Overview
        </button>
      </div>
    );
  }

  return (
    <div className="prompt-editor">
      <div className="prompt-editor-header">
        <div className="prompt-editor-title">
          <button onClick={onBack} className="back-button">
            ← Back
          </button>
          <div>
            <h2>✏️ {prompt.name}</h2>
            <p className="prompt-description">{prompt.description}</p>
            <div className="prompt-meta">
              <span className="category-badge">{prompt.category}</span>
              {prompt.variables.length > 0 && (
                <span className="variables-badge">
                  🔤 {prompt.variables.length} variables
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="prompt-editor-actions">
          <button
            onClick={loadHistory}
            className="btn-secondary"
            title="View version history"
          >
            🕒 History
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className="btn-secondary"
            title="Test prompt with sample data"
          >
            {testing ? '🔄 Testing...' : '🧪 Test'}
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="btn-primary"
          >
            {saving ? '💾 Saving...' : '💾 Save'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
          <button onClick={() => setError('')} className="error-close">×</button>
        </div>
      )}

      {success && (
        <div className="success-message">
          <span className="success-icon">✅</span>
          {success}
        </div>
      )}

      <div className="prompt-editor-content">
        <div className="editor-section">
          <div className="section-header">
            <h3>📝 Prompt Content</h3>
            {hasChanges && <span className="changes-indicator">● Unsaved changes</span>}
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="prompt-textarea"
            placeholder="Enter your prompt content here..."
            rows={20}
          />
          <div className="editor-info">
            <span>Characters: {content.length}</span>
            <span>Lines: {content.split('\n').length}</span>
          </div>
        </div>

        {prompt.variables.length > 0 && (
          <div className="test-section">
            <h3>🧪 Test Variables</h3>
            <div className="test-variables">
              {prompt.variables.map((variable) => (
                <div key={variable} className="variable-input">
                  <label>{variable}:</label>
                  <input
                    type="text"
                    value={testVariables[variable] || ''}
                    onChange={(e) => handleVariableChange(variable, e.target.value)}
                    placeholder={`Enter value for {${variable}}`}
                  />
                </div>
              ))}
            </div>
            
            {testResult && (
              <div className="test-result">
                <h4>🔍 Test Result</h4>
                {testResult.success ? (
                  <div className="test-success">
                    <h5>✅ Formatted Prompt:</h5>
                    <pre className="formatted-prompt">{testResult.formatted_prompt}</pre>
                  </div>
                ) : (
                  <div className="test-error">
                    <h5>❌ Error:</h5>
                    <p>{testResult.error}</p>
                    {testResult.missing_variables && (
                      <div>
                        <strong>Missing variables:</strong> {testResult.missing_variables.join(', ')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {showHistory && (
        <div className="history-modal">
          <div className="history-modal-content">
            <div className="history-header">
              <h3>🕒 Version History</h3>
              <button
                onClick={() => setShowHistory(false)}
                className="close-button"
              >
                ×
              </button>
            </div>
            <div className="history-list">
              {history.length === 0 ? (
                <p>No version history available.</p>
              ) : (
                history.map((version, index) => (
                  <div key={index} className="history-item">
                    <div className="history-info">
                      <div className="history-timestamp">
                        📅 {new Date(version.timestamp).toLocaleString()}
                      </div>
                      <div className="history-user">
                        👤 {version.admin_user}
                      </div>
                      <div className="history-preview">
                        {version.content.substring(0, 100)}...
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestore(version.backup_file)}
                      className="btn-secondary btn-small"
                    >
                      🔄 Restore
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PromptEditor; 