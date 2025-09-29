import React, { useState } from 'react';
import { createCustomTopic } from '../services/api';
import { trackEngagement } from '../utils/engagementTracker';
import '../styles/AddTopicForm.css';

const AddTopicForm = ({ isOpen, onClose, onTopicAdded }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    confidence_score: 0.8,
    enable_research: false
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  // Handle form field changes
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  // Validate form data
  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Topic name is required';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Topic name must be at least 2 characters';
    } else if (formData.name.trim().length > 100) {
      newErrors.name = 'Topic name must be less than 100 characters';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.trim().length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    } else if (formData.description.trim().length > 500) {
      newErrors.description = 'Description must be less than 500 characters';
    }

    const confidenceScore = parseFloat(formData.confidence_score);
    if (isNaN(confidenceScore) || confidenceScore < 0 || confidenceScore > 1) {
      newErrors.confidence_score = 'Confidence score must be between 0 and 1';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      setErrors({});

      const result = await createCustomTopic({
        name: formData.name.trim(),
        description: formData.description.trim(),
        confidence_score: parseFloat(formData.confidence_score),
        enable_research: formData.enable_research
      });

      if (result.success) {
        // Track research activation
        if (formData.enable_research) {
          console.log('👤 AddTopicForm: ✅ Research activation tracked for topic:', result.topic.name);
          trackEngagement({
            type: 'research_activation',
            topicId: result.topic.id,
            topicName: result.topic.name,
            activationType: 'manual_topic_creation',
            timestamp: Date.now()
          });
        }
        
        // Reset form
        setFormData({
          name: '',
          description: '',
          confidence_score: 0.8,
          enable_research: false
        });
        
        // Notify parent component
        if (onTopicAdded) {
          onTopicAdded(result.topic);
        }
        
        // Close modal
        onClose();
      } else {
        setErrors({ general: result.error || 'Failed to create topic' });
      }
    } catch (error) {
      console.error('Error creating topic:', error);
      
      // Handle specific error types
      if (error.response?.status === 409) {
        setErrors({ name: 'A topic with this name already exists' });
      } else if (error.response?.status === 400) {
        const errorDetail = error.response.data.detail;
        if (typeof errorDetail === 'object' && errorDetail.error) {
          // Handle structured error object (e.g., active topics limit)
          setErrors({ general: errorDetail.error });
        } else {
          // Handle simple string error
          setErrors({ general: errorDetail || 'Invalid input data' });
        }
      } else {
        setErrors({ general: 'Failed to create topic. Please try again.' });
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle modal close
  const handleClose = () => {
    if (!loading) {
      setFormData({
        name: '',
        description: '',
        confidence_score: 0.8,
        enable_research: false
      });
      setErrors({});
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="add-topic-modal-overlay" onClick={handleClose}>
      <div className="add-topic-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Custom Research Topic</h2>
          <button 
            className="close-button" 
            onClick={handleClose}
            disabled={loading}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="add-topic-form">
          {errors.general && (
            <div className="form-error-banner">
              <span className="error-icon">⚠️</span>
              <p>{errors.general}</p>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="topic-name">
              Topic Name <span className="required">*</span>
            </label>
            <input
              id="topic-name"
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g., Quantum Computing Advances"
              maxLength={100}
              className={errors.name ? 'error' : ''}
              disabled={loading}
            />
            {errors.name && <div className="error-text">{errors.name}</div>}
            <div className="char-count">
              {formData.name.length}/100 characters
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="topic-description">
              Description <span className="required">*</span>
            </label>
            <textarea
              id="topic-description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Describe what aspects of this topic you'd like to research. Include specific areas of interest, recent developments, or particular angles you want to explore."
              maxLength={500}
              rows={4}
              className={errors.description ? 'error' : ''}
              disabled={loading}
            />
            {errors.description && <div className="error-text">{errors.description}</div>}
            <div className="char-count">
              {formData.description.length}/500 characters
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="confidence-score">
              Confidence Score
              <span className="help-text">How research-worthy is this topic? (0.0 - 1.0)</span>
            </label>
            <div className="confidence-input-group">
              <input
                id="confidence-score"
                type="number"
                name="confidence_score"
                value={formData.confidence_score}
                onChange={handleChange}
                min="0"
                max="1"
                step="0.1"
                className={errors.confidence_score ? 'error' : ''}
                disabled={loading}
              />
              <div className="confidence-labels">
                <span className="confidence-label low">Low (0.0)</span>
                <span className="confidence-label high">High (1.0)</span>
              </div>
            </div>
            {errors.confidence_score && <div className="error-text">{errors.confidence_score}</div>}
          </div>

          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="enable_research"
                checked={formData.enable_research}
                onChange={handleChange}
                disabled={loading}
              />
              <span className="checkbox-text">
                Enable research immediately
                <span className="help-text">Start researching this topic right away</span>
              </span>
            </label>
          </div>

          <div className="form-actions">
            <button 
              type="button" 
              className="cancel-button"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="submit-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Creating...
                </>
              ) : (
                'Create Topic'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddTopicForm; 