import React, { useState, useEffect } from 'react';
import { getMotivationStatus, adjustMotivationDrives, updateMotivationConfig } from '../services/api';
import '../styles/EngineSettings.css';

const EngineSettings = ({ onClose }) => {
  const [settings, setSettings] = useState({
    boredom: 0,
    curiosity: 0,
    tiredness: 0,
    satisfaction: 0,
    threshold: 1.0,
    boredom_rate: 0.001,
    curiosity_decay: 0.0005,
    tiredness_decay: 0.0005,
    satisfaction_decay: 0.0005
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Calculate estimated research frequency
  const calculateResearchFrequency = () => {
    const { boredom_rate, threshold } = settings;
    if (boredom_rate <= 0) return { timeMinutes: '∞', frequency: 'never', color: '#6b7280' };
    
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
    aggressive: {
      name: 'Aggressive Research',
      description: 'Research every 1-2 minutes',
      settings: {
        threshold: 0.3,
        boredom_rate: 0.01,
        curiosity_decay: 0.005,
        tiredness_decay: 0.01,
        satisfaction_decay: 0.005
      }
    },
    balanced: {
      name: 'Balanced Research',
      description: 'Research every 10-15 minutes',
      settings: {
        threshold: 1.0,
        boredom_rate: 0.001,
        curiosity_decay: 0.0005,
        tiredness_decay: 0.0005,
        satisfaction_decay: 0.0005
      }
    },
    conservative: {
      name: 'Conservative Research',
      description: 'Research every 30-60 minutes',
      settings: {
        threshold: 2.0,
        boredom_rate: 0.0005,
        curiosity_decay: 0.0002,
        tiredness_decay: 0.0002,
        satisfaction_decay: 0.0002
      }
    },
    patient: {
      name: 'Very Patient',
      description: 'Research only when highly motivated',
      settings: {
        threshold: 5.0,
        boredom_rate: 0.0002,
        curiosity_decay: 0.0001,
        tiredness_decay: 0.0001,
        satisfaction_decay: 0.0001
      }
    }
  };

  const applyPreset = (presetKey) => {
    const preset = presets[presetKey];
    setSettings(prev => ({
      ...prev,
      ...preset.settings
    }));
    setSuccess(false);
    setError(null);
  };

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const response = await getMotivationStatus();
        const motivation = response.motivation_system;
        const driveRates = response.drive_rates;
        
        setSettings({
          boredom: motivation.boredom,
          curiosity: motivation.curiosity,
          tiredness: motivation.tiredness,
          satisfaction: motivation.satisfaction,
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

  const handleInputChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: parseFloat(value) || 0
    }));
    setSuccess(false);
    setError(null);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      
      // Update configuration parameters
      await updateMotivationConfig({
        threshold: settings.threshold,
        boredom_rate: settings.boredom_rate,
        curiosity_decay: settings.curiosity_decay,
        tiredness_decay: settings.tiredness_decay,
        satisfaction_decay: settings.satisfaction_decay
      });
      
      // Adjust current drive values
      await adjustMotivationDrives({
        boredom: settings.boredom,
        curiosity: settings.curiosity,
        tiredness: settings.tiredness,
        satisfaction: settings.satisfaction
      });
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Error saving settings:', err);
      setError('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      const response = await getMotivationStatus();
      const motivation = response.motivation_system;
      
      setSettings(prev => ({
        ...prev,
        boredom: motivation.boredom,
        curiosity: motivation.curiosity,
        tiredness: motivation.tiredness,
        satisfaction: motivation.satisfaction
      }));
      setSuccess(false);
      setError(null);
    } catch (err) {
      console.error('Error resetting values:', err);
      setError('Failed to reset values. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
                  >
                    Apply
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <h4>Current Motivation Drives</h4>
            <p className="section-description">
              Adjust the current motivation levels (0.0 - 1.0)
            </p>
            
            <div className="setting-group">
              <label>
                Boredom (drives autonomous research)
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={settings.boredom.toFixed(2)}
                  onChange={(e) => handleInputChange('boredom', e.target.value)}
                />
                <div className="drive-bar">
                  <div 
                    className="drive-fill boredom"
                    style={{ width: `${settings.boredom * 100}%` }}
                  ></div>
                </div>
              </label>
            </div>

            <div className="setting-group">
              <label>
                Curiosity (increases with user activity)
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={settings.curiosity.toFixed(2)}
                  onChange={(e) => handleInputChange('curiosity', e.target.value)}
                />
                <div className="drive-bar">
                  <div 
                    className="drive-fill curiosity"
                    style={{ width: `${settings.curiosity * 100}%` }}
                  ></div>
                </div>
              </label>
            </div>

            <div className="setting-group">
              <label>
                Tiredness (reduces after research)
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={settings.tiredness.toFixed(2)}
                  onChange={(e) => handleInputChange('tiredness', e.target.value)}
                />
                <div className="drive-bar">
                  <div 
                    className="drive-fill tiredness"
                    style={{ width: `${settings.tiredness * 100}%` }}
                  ></div>
                </div>
              </label>
            </div>

            <div className="setting-group">
              <label>
                Satisfaction (gained from good research)
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={settings.satisfaction.toFixed(2)}
                  onChange={(e) => handleInputChange('satisfaction', e.target.value)}
                />
                <div className="drive-bar">
                  <div 
                    className="drive-fill satisfaction"
                    style={{ width: `${settings.satisfaction * 100}%` }}
                  ></div>
                </div>
              </label>
            </div>
          </div>

          <div className="settings-section">
            <h4>System Configuration</h4>
            <p className="section-description">
              Adjust system parameters that control motivation behavior
            </p>
            
            <div className="setting-group">
              <label>
                Research Threshold
                <input
                  type="number"
                  min="0.1"
                  max="10.0"
                  step="0.1"
                  value={settings.threshold.toFixed(2)}
                  onChange={(e) => handleInputChange('threshold', e.target.value)}
                />
                <small>Research triggers when impetus exceeds this value</small>
              </label>
            </div>

            <div className="config-grid">
              <div className="config-item editable">
                <label>
                  Boredom Rate (/sec)
                  <input
                    type="number"
                    min="0"
                    max="0.1"
                    step="0.001"
                    value={settings.boredom_rate.toFixed(4)}
                    onChange={(e) => handleInputChange('boredom_rate', e.target.value)}
                  />
                  <small>How fast boredom increases over time</small>
                </label>
              </div>
              <div className="config-item editable">
                <label>
                  Curiosity Decay (/sec)
                  <input
                    type="number"
                    min="0"
                    max="0.1"
                    step="0.001"
                    value={settings.curiosity_decay.toFixed(4)}
                    onChange={(e) => handleInputChange('curiosity_decay', e.target.value)}
                  />
                  <small>How fast curiosity decreases over time</small>
                </label>
              </div>
              <div className="config-item editable">
                <label>
                  Tiredness Decay (/sec)
                  <input
                    type="number"
                    min="0"
                    max="0.1"
                    step="0.001"
                    value={settings.tiredness_decay.toFixed(4)}
                    onChange={(e) => handleInputChange('tiredness_decay', e.target.value)}
                  />
                  <small>How fast tiredness decreases over time</small>
                </label>
              </div>
              <div className="config-item editable">
                <label>
                  Satisfaction Decay (/sec)
                  <input
                    type="number"
                    min="0"
                    max="0.1"
                    step="0.001"
                    value={settings.satisfaction_decay.toFixed(4)}
                    onChange={(e) => handleInputChange('satisfaction_decay', e.target.value)}
                  />
                  <small>How fast satisfaction decreases over time</small>
                </label>
              </div>
            </div>
          </div>

          <div className="impetus-section">
            <h4>Current Impetus</h4>
            <div className="impetus-value">
              {(settings.boredom + settings.curiosity + 0.5 * settings.satisfaction - settings.tiredness).toFixed(2)} / {settings.threshold}
            </div>
            <small>
              Formula: Boredom + Curiosity + (0.5 × Satisfaction) - Tiredness
            </small>
          </div>
        </div>

        <div className="settings-footer">
          <button 
            className="reset-btn" 
            onClick={handleReset}
            disabled={saving}
          >
            Reset to Current
          </button>
          <button 
            className="save-btn" 
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Apply Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EngineSettings; 