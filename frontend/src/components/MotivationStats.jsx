import React, { useEffect, useState } from 'react';
import { getMotivationStatus } from '../services/api';
import '../styles/MotivationStats.css';

const MotivationStats = ({ onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      const response = await getMotivationStatus();
      setData({
        ...response.motivation_system,
        engine_running: response.research_engine?.running || false
      });
    } catch (err) {
      console.error('Error loading motivation status:', err);
    } finally {
      if (isRefresh) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchStatus();
    
    // Set up auto-refresh every 5 seconds
    const interval = setInterval(() => {
      fetchStatus(true);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Drive configuration with icons, colors, and descriptions
  const driveConfig = {
    boredom: {
      icon: '😴',
      color: '#ef4444',
      colorLight: '#fef2f2',
      description: 'Need for new stimulation',
      unit: 'restlessness'
    },
    curiosity: {
      icon: '🔍',
      color: '#3b82f6',
      colorLight: '#eff6ff',
      description: 'Drive to explore and learn',
      unit: 'inquisitiveness'
    },
    tiredness: {
      icon: '💤',
      color: '#f59e0b',
      colorLight: '#fffbeb',
      description: 'Need for rest and reflection',
      unit: 'fatigue'
    },
    satisfaction: {
      icon: '✨',
      color: '#10b981',
      colorLight: '#f0fdf4',
      description: 'Contentment with current state',
      unit: 'fulfillment'
    }
  };

  const drives = ['boredom', 'curiosity', 'tiredness', 'satisfaction'];

  // Calculate impetus percentage
  const impetusPercentage = data ? Math.round((data.impetus / data.threshold) * 100) : 0;
  const impetusLevel = impetusPercentage >= 80 ? 'critical' : impetusPercentage >= 60 ? 'high' : impetusPercentage >= 40 ? 'medium' : 'low';

  return (
    <div className="profile-modal-overlay" onClick={onClose}>
      <div className="motivation-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="motivation-header">
          <h3>🧠 AI Motivation Drives</h3>
          <div className="header-controls">
            {refreshing && <div className="refresh-indicator">🔄</div>}
            <button className="close-btn" onClick={onClose}>✕</button>
          </div>
        </div>
        
        {loading && (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Analyzing motivation state...</p>
          </div>
        )}
        
        {!loading && !data && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <p>Error loading motivation data.</p>
          </div>
        )}
        
        {!loading && data && (
          <div className="motivation-content">
            {/* Impetus Section - Central Focus */}
            <div className={`impetus-display ${impetusLevel}`}>
              <div className="impetus-circle">
                <div className="impetus-inner">
                  <div className="impetus-value">{data.impetus.toFixed(1)}</div>
                  <div className="impetus-threshold">/ {data.threshold}</div>
                </div>
                <svg className="impetus-ring" viewBox="0 0 100 100">
                  <circle
                    className="impetus-background"
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    opacity="0.2"
                  />
                  <circle
                    className="impetus-progress"
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={`${2 * Math.PI * 45}`}
                    strokeDashoffset={`${2 * Math.PI * 45 * (1 - impetusPercentage / 100)}`}
                    transform="rotate(-90 50 50)"
                  />
                </svg>
              </div>
              <div className="impetus-info">
                <div className="impetus-label">Research Impetus</div>
                <div className="impetus-percentage">{impetusPercentage}%</div>
                <div className="impetus-description">
                  {impetusLevel === 'critical' && '🚨 Research urgently needed!'}
                  {impetusLevel === 'high' && '🔥 Strong motivation to research'}
                  {impetusLevel === 'medium' && '⚡ Moderate research drive'}
                  {impetusLevel === 'low' && '😌 Relaxed state'}
                </div>
              </div>
            </div>

            {/* Drive Cards Grid */}
            <div className="drives-grid">
              {drives.map((drive) => {
                const config = driveConfig[drive];
                const value = data[drive];
                const percentage = Math.round(value * 100);
                const intensity = percentage >= 80 ? 'very-high' : percentage >= 60 ? 'high' : percentage >= 40 ? 'medium' : percentage >= 20 ? 'low' : 'very-low';
                
                return (
                  <div key={drive} className={`drive-card ${intensity}`} style={{ '--drive-color': config.color, '--drive-color-light': config.colorLight }}>
                    <div className="drive-header">
                      <div className="drive-icon">{config.icon}</div>
                      <div className="drive-title">
                        <span className="drive-name">{drive.charAt(0).toUpperCase() + drive.slice(1)}</span>
                        <span className="drive-percentage">{percentage}%</span>
                      </div>
                    </div>
                    
                    <div className="drive-visualization">
                      {/* Circular Progress */}
                      <div className="drive-circle">
                        <svg viewBox="0 0 60 60" className="drive-svg">
                          <circle
                            cx="30"
                            cy="30"
                            r="25"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                            opacity="0.2"
                          />
                          <circle
                            cx="30"
                            cy="30"
                            r="25"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="4"
                            strokeDasharray={`${2 * Math.PI * 25}`}
                            strokeDashoffset={`${2 * Math.PI * 25 * (1 - percentage / 100)}`}
                            transform="rotate(-90 30 30)"
                            className="drive-progress"
                          />
                        </svg>
                        <div className="drive-center-value">
                          {percentage}
                        </div>
                      </div>
                      
                      {/* Wave/Liquid Effect */}
                      <div className="drive-wave-container">
                        <div className="drive-wave" style={{ height: `${percentage}%` }}>
                          <div className="wave-surface"></div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="drive-description">
                      <div className="drive-subtitle">{config.description}</div>
                      <div className="drive-intensity-label">
                        {intensity === 'very-high' && '🔥 Extremely high'}
                        {intensity === 'high' && '⚡ High'}
                        {intensity === 'medium' && '📊 Moderate'}
                        {intensity === 'low' && '📉 Low'}
                        {intensity === 'very-low' && '💤 Minimal'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Engine Status */}
            <div className={`engine-status ${data.engine_running ? 'running' : 'stopped'}`}>
              <div className="status-indicator">
                <div className="status-dot"></div>
                <span className="status-text">
                  Research Engine: {data.engine_running ? 'Active' : 'Inactive'}
                </span>
              </div>
              {!data.engine_running && (
                <div className="freeze-notice">
                  <span className="freeze-icon">❄️</span>
                  <span>Drives frozen while engine is stopped</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MotivationStats;
