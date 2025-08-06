import React, { useState, useEffect } from 'react';
import { overrideLearnedBehavior, getUserPersonalizationData } from '../services/api';
import '../styles/PersonalizationDashboard.css';

const PersonalizationDashboard = ({ personalizationData, onDataUpdate }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState(new Set(['learned_behaviors']));

  const toggleSection = (sectionId) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const handleOverride = async (preferenceType, currentValue, disableLearning = false) => {
    try {
      setIsLoading(true);
      
      const newValue = prompt(
        `Override ${preferenceType.replace(/_/g, ' ')}\nCurrent value: ${currentValue}\nEnter new value:`,
        currentValue
      );
      
      if (newValue !== null && newValue !== currentValue) {
        const parsedValue = isNaN(newValue) ? newValue : parseFloat(newValue);
        
        await overrideLearnedBehavior(preferenceType, parsedValue, disableLearning);
        
        // Refresh personalization data
        const updatedData = await getUserPersonalizationData();
        onDataUpdate(updatedData);
        
        alert(`Successfully overrode ${preferenceType.replace(/_/g, ' ')}`);
      }
    } catch (error) {
      console.error('Error overriding behavior:', error);
      alert('Failed to override behavior. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisableLearning = async (preferenceType, currentValue) => {
    try {
      setIsLoading(true);
      
      const confirmed = window.confirm(
        `Disable automatic learning for ${preferenceType.replace(/_/g, ' ')}?\n\n` +
        `Current value: ${currentValue}\n\n` +
        'The system will stop automatically adjusting this preference based on your behavior.'
      );
      
      if (confirmed) {
        await overrideLearnedBehavior(preferenceType, currentValue, true);
        
        // Refresh personalization data
        const updatedData = await getUserPersonalizationData();
        onDataUpdate(updatedData);
        
        alert(`Disabled learning for ${preferenceType.replace(/_/g, ' ')}`);
      }
    } catch (error) {
      console.error('Error disabling learning:', error);
      alert('Failed to disable learning. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const formatPreferenceName = (name) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (!personalizationData) {
    return (
      <div className="personalization-dashboard">
        <div className="dashboard-loading">
          <p>Loading personalization data...</p>
        </div>
      </div>
    );
  }

  const { learned_behaviors, adaptation_history, user_overrides, learning_stats } = personalizationData;

  return (
    <div className="personalization-dashboard">
      <div className="dashboard-header">
        <h3>What I've Learned About You</h3>
        <p className="dashboard-subtitle">
          Transparent view of all learned preferences and behaviors. You can override or disable any of these.
        </p>
      </div>

      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Updating preferences...</p>
        </div>
      )}

      <div className="dashboard-stats">
        <div className="stat-item">
          <span className="stat-label">Total Adaptations:</span>
          <span className="stat-value">{learning_stats?.total_adaptations || 0}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Recent Activity (7 days):</span>
          <span className="stat-value">{learning_stats?.recent_activity || 0}</span>
        </div>
      </div>

      {/* Learned Source Preferences */}
      <div className="dashboard-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('source_preferences')}
        >
          <h4>Source Type Preferences (Learned)</h4>
          <span className={`expand-icon ${expandedSections.has('source_preferences') ? 'expanded' : ''}`}>
            ▼
          </span>
        </div>
        
        {expandedSections.has('source_preferences') && (
          <div className="section-content">
            {Object.entries(learned_behaviors?.source_preferences || {}).map(([sourceType, value]) => (
              <div key={sourceType} className="preference-item">
                <div className="preference-info">
                  <span className="preference-name">{formatPreferenceName(sourceType)}</span>
                  <span className="preference-value">{Math.round(value * 100)}%</span>
                  {user_overrides?.[`source_preference_${sourceType}`] && (
                    <span className="override-badge">User Override</span>
                  )}
                </div>
                <div className="preference-actions">
                  <button
                    className="action-btn override-btn"
                    onClick={() => handleOverride(`source_preference_${sourceType}`, value)}
                    disabled={isLoading}
                  >
                    Override
                  </button>
                  <button
                    className="action-btn disable-btn"
                    onClick={() => handleDisableLearning(`source_preference_${sourceType}`, value)}
                    disabled={isLoading}
                  >
                    Disable Learning
                  </button>
                </div>
              </div>
            ))}
            
            {(!learned_behaviors?.source_preferences || Object.keys(learned_behaviors.source_preferences).length === 0) && (
              <div className="no-data">
                <p>No source preferences learned yet. Interact with research findings to help the system learn your preferences.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Format Optimizations */}
      <div className="dashboard-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('format_optimizations')}
        >
          <h4>Format Optimizations (Learned)</h4>
          <span className={`expand-icon ${expandedSections.has('format_optimizations') ? 'expanded' : ''}`}>
            ▼
          </span>
        </div>
        
        {expandedSections.has('format_optimizations') && (
          <div className="section-content">
            {learned_behaviors?.format_optimizations?.optimal_response_length && (
              <div className="preference-item">
                <div className="preference-info">
                  <span className="preference-name">Optimal Response Length</span>
                  <span className="preference-value">{learned_behaviors.format_optimizations.optimal_response_length} characters</span>
                </div>
                <div className="preference-actions">
                  <button
                    className="action-btn override-btn"
                    onClick={() => handleOverride('optimal_response_length', learned_behaviors.format_optimizations.optimal_response_length)}
                    disabled={isLoading}
                  >
                    Override
                  </button>
                  <button
                    className="action-btn disable-btn"
                    onClick={() => handleDisableLearning('optimal_response_length', learned_behaviors.format_optimizations.optimal_response_length)}
                    disabled={isLoading}
                  >
                    Disable Learning
                  </button>
                </div>
              </div>
            )}

            {learned_behaviors?.format_optimizations?.prefers_structured_responses !== null && (
              <div className="preference-item">
                <div className="preference-info">
                  <span className="preference-name">Prefers Structured Responses</span>
                  <span className="preference-value">{learned_behaviors.format_optimizations.prefers_structured_responses ? 'Yes' : 'No'}</span>
                </div>
                <div className="preference-actions">
                  <button
                    className="action-btn override-btn"
                    onClick={() => handleOverride('prefers_structured_responses', learned_behaviors.format_optimizations.prefers_structured_responses)}
                    disabled={isLoading}
                  >
                    Override
                  </button>
                  <button
                    className="action-btn disable-btn"
                    onClick={() => handleDisableLearning('prefers_structured_responses', learned_behaviors.format_optimizations.prefers_structured_responses)}
                    disabled={isLoading}
                  >
                    Disable Learning
                  </button>
                </div>
              </div>
            )}

            {(!learned_behaviors?.format_optimizations?.optimal_response_length && 
              learned_behaviors?.format_optimizations?.prefers_structured_responses === null) && (
              <div className="no-data">
                <p>No format optimizations learned yet. Continue using the system to help it learn your preferences.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Engagement Patterns */}
      <div className="dashboard-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('engagement_patterns')}
        >
          <h4>Engagement Patterns</h4>
          <span className={`expand-icon ${expandedSections.has('engagement_patterns') ? 'expanded' : ''}`}>
            ▼
          </span>
        </div>
        
        {expandedSections.has('engagement_patterns') && (
          <div className="section-content">
            <div className="engagement-stats">
              <div className="engagement-item">
                <span className="engagement-label">Average Completion Rate (Research):</span>
                <span className="engagement-value">
                  {Math.round((learned_behaviors?.engagement_patterns?.avg_completion_rate || 0) * 100)}%
                </span>
              </div>
              
              <div className="engagement-item">
                <span className="engagement-label">Follow-up Question Frequency:</span>
                <span className="engagement-value">
                  {Math.round((learned_behaviors?.engagement_patterns?.follow_up_frequency || 0) * 100)}%
                </span>
              </div>

              {learned_behaviors?.engagement_patterns?.preferred_sources?.length > 0 && (
                <div className="engagement-item">
                  <span className="engagement-label">Most Engaged Sources:</span>
                  <span className="engagement-value">
                    {learned_behaviors.engagement_patterns.preferred_sources.slice(0, 3).join(', ')}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Recent Adaptations */}
      <div className="dashboard-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('recent_adaptations')}
        >
          <h4>Recent Adaptations</h4>
          <span className={`expand-icon ${expandedSections.has('recent_adaptations') ? 'expanded' : ''}`}>
            ▼
          </span>
        </div>
        
        {expandedSections.has('recent_adaptations') && (
          <div className="section-content">
            {adaptation_history && adaptation_history.length > 0 ? (
              <div className="adaptations-list">
                {adaptation_history.slice(0, 10).map((adaptation, index) => (
                  <div key={index} className="adaptation-item">
                    <div className="adaptation-header">
                      <span className="adaptation-type">{formatPreferenceName(adaptation.adaptation_type)}</span>
                      <span className="adaptation-time">{formatTimestamp(adaptation.timestamp)}</span>
                    </div>
                    <div className="adaptation-description">
                      {adaptation.change_made}
                    </div>
                    {adaptation.effectiveness_score && (
                      <div className="adaptation-effectiveness">
                        Effectiveness: {Math.round(adaptation.effectiveness_score * 100)}%
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-data">
                <p>No adaptations recorded yet. The system will learn and adapt as you use it.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* User Overrides */}
      {user_overrides && Object.keys(user_overrides).length > 0 && (
        <div className="dashboard-section">
          <div 
            className="section-header"
            onClick={() => toggleSection('user_overrides')}
          >
            <h4>Your Overrides</h4>
            <span className={`expand-icon ${expandedSections.has('user_overrides') ? 'expanded' : ''}`}>
              ▼
            </span>
          </div>
          
          {expandedSections.has('user_overrides') && (
            <div className="section-content">
              <div className="overrides-list">
                {Object.entries(user_overrides).map(([overrideType, overrideData]) => (
                  <div key={overrideType} className="override-item">
                    <div className="override-info">
                      <span className="override-name">{formatPreferenceName(overrideType)}</span>
                      <span className="override-value">{String(overrideData.value)}</span>
                      {overrideData.learning_disabled && (
                        <span className="learning-disabled-badge">Learning Disabled</span>
                      )}
                    </div>
                    <div className="override-time">
                      Overridden: {formatTimestamp(overrideData.timestamp)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="dashboard-footer">
        <div className="privacy-note">
          <h5>Privacy Note</h5>
          <p>
            All personalization data is stored locally on your device. Nothing is sent to external servers. 
            You have complete control over what the system learns and can override or disable any behavior.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PersonalizationDashboard;