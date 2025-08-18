import React, { useState, useEffect } from 'react';
import { 
  getCurrentUser, 
  updateUserPersonality, 
  getPersonalityPresets,
  getUserPreferences,
  updateUserPreferences,
  getUserPersonalizationData 
} from '../services/api';
import PersonalizationDashboard from './PersonalizationDashboard';
import '../styles/UserProfile.css';

const UserProfile = ({ userId, onProfileUpdated }) => {
  const [profile, setProfile] = useState(null);
  const [presets, setPresets] = useState({});
  const [preferences, setPreferences] = useState(null);
  const [personalizationData, setPersonalizationData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('personality');
  const [editedStyle, setEditedStyle] = useState('');
  const [editedTone, setEditedTone] = useState('');
  const [editedPreferences, setEditedPreferences] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        
        // Load user profile, preferences, and personalization data in parallel
        const [userData, presetsData, preferencesData, personalizationDataResponse] = await Promise.all([
          getCurrentUser(),
          getPersonalityPresets(),
          getUserPreferences().catch(() => null),
          getUserPersonalizationData().catch(() => null)
        ]);
        
        setProfile(userData);
        setPresets(presetsData.presets || {});
        setPreferences(preferencesData);
        setPersonalizationData(personalizationDataResponse);
        
        // Initialize editing form with current values
        setEditedStyle(userData.personality.style);
        setEditedTone(userData.personality.tone);
        setEditedPreferences(preferencesData);
      } catch (error) {
        console.error('👤 UserProfile: ❌ Error loading user profile:', error);
        console.error('👤 UserProfile: ❌ Failed to load data for user:', userId);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (userId) {
      loadData();
    }
  }, [userId]);

  const handleApplyPreset = (presetKey) => {
    const preset = presets[presetKey];
    if (preset) {
      console.log('👤 UserProfile: Applying personality preset:', presetKey);
      console.log('👤 UserProfile: Preset details:', preset);
      setEditedStyle(preset.style);
      setEditedTone(preset.tone);
    } else {
      console.warn('👤 UserProfile: ⚠️ Preset not found:', presetKey);
    }
  };

  const handleSavePersonality = async () => {
    try {
      console.log('👤 UserProfile: Saving personality changes for user:', userId);
      
      const updatedPersonality = {
        style: editedStyle,
        tone: editedTone,
        additional_traits: profile.personality.additional_traits || {}
      };
      
      console.log('👤 UserProfile: Updated personality data:', updatedPersonality);
      
      await updateUserPersonality(updatedPersonality);
      
      console.log('👤 UserProfile: ✅ Successfully saved personality changes for user:', userId);
      
      // Update local state
      setProfile({
        ...profile,
        personality: updatedPersonality
      });
      
      setIsEditing(false);
      
      // Notify parent component
      if (onProfileUpdated) {
        onProfileUpdated(updatedPersonality);
      }
    } catch (error) {
      console.error('👤 UserProfile: ❌ Error updating personality for user:', userId, error);
      console.error('👤 UserProfile: ❌ Failed personality update data:', { editedStyle, editedTone });
      alert('Failed to update personality settings');
    }
  };

  const handleSavePreferences = async () => {
    try {
      console.log('👤 UserProfile: Saving preferences for user:', userId);
      console.log('👤 UserProfile: New preferences data:', editedPreferences);
      
      await updateUserPreferences(editedPreferences);
      
      console.log('👤 UserProfile: ✅ Successfully saved preferences for user:', userId);
      
      // Update local state
      setPreferences(editedPreferences);
      setIsEditing(false);
      
      // Reload personalization data to show updates
      const newPersonalizationData = await getUserPersonalizationData().catch(() => null);
      setPersonalizationData(newPersonalizationData);
      
      if (newPersonalizationData) {
        console.log('👤 UserProfile: 🔄 Refreshed personalization data after preference update');
      }
      
    } catch (error) {
      console.error('👤 UserProfile: ❌ Error updating preferences for user:', userId, error);
      console.error('👤 UserProfile: ❌ Failed preferences update data:', editedPreferences);
      alert('Failed to update preferences');
    }
  };

  const handlePreferenceChange = (category, key, value) => {
    console.log('👤 UserProfile: Preference change:', { category, key, value, userId });
    setEditedPreferences(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  const handleSourceTypeChange = (sourceType, value) => {
    console.log('👤 UserProfile: Source type preference change:', { sourceType, value, userId });
    setEditedPreferences(prev => ({
      ...prev,
      content_preferences: {
        ...prev.content_preferences,
        source_types: {
          ...prev.content_preferences.source_types,
          [sourceType]: parseFloat(value)
        }
      }
    }));
  };

  if (isLoading) {
    return <div className="user-profile-loading">Loading profile...</div>;
  }

  if (!profile) {
    return <div className="user-profile-error">User profile not found</div>;
  }

  const renderPersonalityTab = () => (
    <div className="tab-content">
      {isEditing && activeTab === 'personality' ? (
        <div className="profile-edit-form">
          <div className="form-group">
            <label>Communication Style:</label>
            <select 
              value={editedStyle}
              onChange={(e) => setEditedStyle(e.target.value)}
            >
              <option value="helpful">Helpful</option>
              <option value="concise">Concise</option>
              <option value="expert">Expert</option>
              <option value="creative">Creative</option>
              <option value="friendly">Friendly</option>
            </select>
          </div>
          
          <div className="form-group">
            <label>Tone:</label>
            <select 
              value={editedTone}
              onChange={(e) => setEditedTone(e.target.value)}
            >
              <option value="friendly">Friendly</option>
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="enthusiastic">Enthusiastic</option>
              <option value="direct">Direct</option>
            </select>
          </div>
          
          <div className="preset-buttons">
            <label>Quick Presets:</label>
            <div className="presets">
              {Object.keys(presets).map(key => (
                <button 
                  key={key} 
                  onClick={() => handleApplyPreset(key)}
                  className="preset-btn"
                >
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </button>
              ))}
            </div>
          </div>
          
          <button 
            className="save-profile-btn"
            onClick={handleSavePersonality}
          >
            Save Changes
          </button>
        </div>
      ) : (
        <div className="profile-summary">
          <div className="profile-info-item">
            <span className="profile-info-label">Communication Style:</span>
            <span className="profile-info-value">{profile.personality.style}</span>
          </div>
          
          <div className="profile-info-item">
            <span className="profile-info-label">Tone:</span>
            <span className="profile-info-value">{profile.personality.tone}</span>
          </div>
        </div>
      )}
    </div>
  );

  const renderPreferencesTab = () => {
    if (!preferences) {
      return <div className="tab-content">Loading preferences...</div>;
    }

    return (
      <div className="tab-content">
        {isEditing && activeTab === 'preferences' ? (
          <div className="preferences-edit-form">
            <div className="preferences-section">
              <h4>Content Preferences</h4>
              
              <div className="form-group">
                <label>Research Depth:</label>
                <select
                  value={editedPreferences?.content_preferences?.research_depth || 'balanced'}
                  onChange={(e) => handlePreferenceChange('content_preferences', 'research_depth', e.target.value)}
                >
                  <option value="quick">Quick</option>
                  <option value="balanced">Balanced</option>
                  <option value="detailed">Detailed</option>
                </select>
              </div>

              <div className="source-preferences">
                <h5>Source Type Preferences</h5>
                {Object.entries(editedPreferences?.content_preferences?.source_types || {}).map(([sourceType, value]) => (
                  <div key={sourceType} className="source-slider">
                    <label>{sourceType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={value}
                      onChange={(e) => handleSourceTypeChange(sourceType, e.target.value)}
                    />
                    <span className="slider-value">{Math.round(value * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="preferences-section">
              <h4>Format Preferences</h4>
              
              <div className="form-group">
                <label>Response Length:</label>
                <select
                  value={editedPreferences?.format_preferences?.response_length || 'medium'}
                  onChange={(e) => handlePreferenceChange('format_preferences', 'response_length', e.target.value)}
                >
                  <option value="short">Short</option>
                  <option value="medium">Medium</option>
                  <option value="long">Long</option>
                </select>
              </div>

              <div className="form-group">
                <label>Detail Level:</label>
                <select
                  value={editedPreferences?.format_preferences?.detail_level || 'balanced'}
                  onChange={(e) => handlePreferenceChange('format_preferences', 'detail_level', e.target.value)}
                >
                  <option value="concise">Concise</option>
                  <option value="balanced">Balanced</option>
                  <option value="comprehensive">Comprehensive</option>
                </select>
              </div>

              

              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={editedPreferences?.format_preferences?.use_bullet_points || false}
                    onChange={(e) => handlePreferenceChange('format_preferences', 'use_bullet_points', e.target.checked)}
                  />
                  Use bullet points for lists
                </label>
              </div>

              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={editedPreferences?.format_preferences?.include_key_insights || false}
                    onChange={(e) => handlePreferenceChange('format_preferences', 'include_key_insights', e.target.checked)}
                  />
                  Include key insights section
                </label>
              </div>
            </div>

            <button 
              className="save-profile-btn"
              onClick={handleSavePreferences}
            >
              Save Preferences
            </button>
          </div>
        ) : (
          <div className="preferences-summary">
            <div className="preferences-section">
              <h4>Content Preferences</h4>
              <div className="profile-info-item">
                <span className="profile-info-label">Research Depth:</span>
                <span className="profile-info-value">{preferences.content_preferences?.research_depth}</span>
              </div>
              
              <div className="source-preferences-display">
                <h5>Source Type Preferences</h5>
                {Object.entries(preferences.content_preferences?.source_types || {}).map(([sourceType, value]) => (
                  <div key={sourceType} className="source-preference-item">
                    <span className="source-name">{sourceType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    <span className="source-value">{Math.round(value * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="preferences-section">
              <h4>Format Preferences</h4>
              <div className="profile-info-item">
                <span className="profile-info-label">Response Length:</span>
                <span className="profile-info-value">{preferences.format_preferences?.response_length}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Detail Level:</span>
                <span className="profile-info-value">{preferences.format_preferences?.detail_level}</span>
              </div>
              
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="user-profile">
      <div className="user-profile-header">
        <h3>User Settings</h3>
        <div className="header-actions">
          {!isEditing ? (
            <button 
              className="edit-profile-btn"
              onClick={() => setIsEditing(true)}
            >
              Edit
            </button>
          ) : (
            <button 
              className="cancel-edit-btn"
              onClick={() => {
                setIsEditing(false);
                setEditedStyle(profile.personality.style);
                setEditedTone(profile.personality.tone);
                setEditedPreferences(preferences);
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="user-profile-tabs">
        <button 
          className={`tab-button ${activeTab === 'personality' ? 'active' : ''}`}
          onClick={() => setActiveTab('personality')}
        >
          Personality
        </button>
        <button 
          className={`tab-button ${activeTab === 'preferences' ? 'active' : ''}`}
          onClick={() => setActiveTab('preferences')}
        >
          Content Preferences
        </button>
        <button 
          className={`tab-button ${activeTab === 'learned' ? 'active' : ''}`}
          onClick={() => setActiveTab('learned')}
        >
          What I've Learned
        </button>
      </div>
      
      <div className="user-profile-content">
        {activeTab === 'personality' && renderPersonalityTab()}
        {activeTab === 'preferences' && renderPreferencesTab()}
        {activeTab === 'learned' && (
          <PersonalizationDashboard 
            personalizationData={personalizationData}
            onDataUpdate={setPersonalizationData}
          />
        )}
      </div>
    </div>
  );
};

export default UserProfile; 