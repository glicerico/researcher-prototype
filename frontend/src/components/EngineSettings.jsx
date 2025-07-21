import React, { useState, useEffect } from 'react';
import { getMotivationStatus, updateMotivationConfig } from '../services/api';
import '../styles/EngineSettings.css';

const EngineSettings = ({ onClose }) => {
  const [settings, setSettings] = useState({
    threshold: 2.0,
    boredom_rate: 0.0005,
    curiosity_decay: 0.0002,
    tiredness_decay: 0.0002,
    satisfaction_decay: 0.0002
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Calculate estimated research frequency
  const calculateResearchFrequency = () => {
    const { boredom_rate, threshold } = settings;
    
    // Return loading state if values aren't loaded yet
    if (!boredom_rate || !threshold || boredom_rate <= 0) {
      return { timeMinutes: '...', frequency: 'loading', color: '#6b7280' };
    }
    
    // Simplified estimation: time for boredom alone to reach threshold
    const timeSeconds = threshold / boredom_rate;
    const timeMinutes = timeSeconds / 60;
    
    let frequency, color;
    if (timeMinutes < 1) {
      frequency = 'very frequent';
      color = '#ef4444'; // red
    } else if (timeMinutes < 5) {
      frequency = 'frequent';
      color = '#f59e0b'; // orange
    } else if (timeMinutes < 15) {
      frequency = 'moderate';
      color = '#10b981'; // green
    } else if (timeMinutes < 60) {
      frequency = 'infrequent';
      color = '#3b82f6'; // blue
    } else {
      frequency = 'rare';
      color = '#6b7280'; // gray
    }
    
    return { 
      timeMinutes: timeMinutes < 1 ? '<1' : Math.round(timeMinutes).toString(),
      frequency,
      color
    };
  };

  // Preset configurations
  const presets = {
    balanced: {
      name: 'Balanced Research',
      description: 'Research every 10-15 minutes',
      threshold: 1.0,
      boredom_rate: 0.001,
      curiosity_decay: 0.0005,
      tiredness_decay: 0.0005,
      satisfaction_decay: 0.0005
    },
    conservative: {
      name: 'Conservative Research',
      description: 'Research every 30-60 minutes',
      threshold: 2.0,
      boredom_rate: 0.0005,
      curiosity_decay: 0.0002,
      tiredness_decay: 0.0002,
      satisfaction_decay: 0.0002
    },
    patient: {
      name: 'Very Patient',
      description: 'Research only when highly motivated',
      threshold: 5.0,
      boredom_rate: 0.0002,
      curiosity_decay: 0.0001,
      tiredness_decay: 0.0001,
      satisfaction_decay: 0.0001
    }
  };

  const applyPreset = async (presetKey) => {
    const preset = presets[presetKey];
    try {
      setSaving(true);
      setError(null);
      
      // Apply the preset configuration directly (send all parameters to completely replace config)
      await updateMotivationConfig(preset);
      
      // Update local state for frequency calculation
      setSettings({
        threshold: preset.threshold,
        boredom_rate: preset.boredom_rate,
        curiosity_decay: preset.curiosity_decay,
        tiredness_decay: preset.tiredness_decay,
        satisfaction_decay: preset.satisfaction_decay
      });
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Error applying preset:', err);
      setError('Failed to apply preset. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const response = await getMotivationStatus();
        const motivation = response.motivation_system;
        const driveRates = response.drive_rates;
        
        setSettings({
          threshold: motivation.threshold,
          boredom_rate: driveRates.boredom_rate,
          curiosity_decay: driveRates.curiosity_decay,
          tiredness_decay: driveRates.tiredness_decay,
          satisfaction_decay: driveRates.satisfaction_decay
        });
      } catch (err) {
        console.error('Error loading settings:', err);
        setError('Failed to load settings. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);



  if (loading) {
    return (
      <div className="profile-modal-overlay" onClick={onClose}>
        <div className="engine-settings-modal" onClick={(e) => e.stopPropagation()}>
          <div className="settings-header">
            <h3>Research Engine Settings</h3>
            <button className="close-btn" onClick={onClose}>✕</button>
          </div>
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading settings...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-modal-overlay" onClick={onClose}>
      <div className="engine-settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h3>Research Engine Settings</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        
        <div className="settings-content">
          {error && (
            <div className="error-message">
              <p>{error}</p>
            </div>
          )}
          
          {success && (
            <div className="success-message">
              <p>Settings saved successfully!</p>
            </div>
          )}

          {/* Research Frequency Estimator */}
          <div className="frequency-estimator">
            <h4>Estimated Research Frequency</h4>
            {(() => {
              const freq = calculateResearchFrequency();
              return (
                <div className="frequency-display">
                  <div className="frequency-time">
                    ~{freq.timeMinutes} minutes
                  </div>
                  <div 
                    className="frequency-label"
                    style={{ color: freq.color }}
                  >
                    {freq.frequency}
                  </div>
                  <small>Based on boredom rate reaching threshold</small>
                </div>
              );
            })()}
            
            <div className="behavior-note">
              <small>
                📌 <strong>Note:</strong> Motivation only evolves when the research engine is running. 
                When stopped, all motivation parameters freeze at their current values.
              </small>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="settings-section">
            <h4>Quick Presets</h4>
            <p className="section-description">
              Apply common research behavior configurations
            </p>
            <div className="presets-grid">
              {Object.entries(presets).map(([key, preset]) => (
                <div key={key} className="preset-card">
                  <h5>{preset.name}</h5>
                  <p>{preset.description}</p>
                  <button
                    className="preset-btn"
                    onClick={() => applyPreset(key)}
                    disabled={saving}
                  >
                    {saving ? 'Applying...' : 'Apply'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        
        </div>

        <div className="settings-footer">
          <button className="close-btn-alt" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default EngineSettings; 