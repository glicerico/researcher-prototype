import React, { useState, useEffect } from 'react';
import { getCurrentUser, updateUserPersonality, getPersonalityPresets } from '../services/api';
import '../styles/UserProfile.css';

const UserProfile = ({ userId, onProfileUpdated }) => {
  const [profile, setProfile] = useState(null);
  const [presets, setPresets] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedStyle, setEditedStyle] = useState('');
  const [editedTone, setEditedTone] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        
        // Load user profile and personality presets in parallel
        const [userData, presetsData] = await Promise.all([
          getCurrentUser(),
          getPersonalityPresets()
        ]);
        
        setProfile(userData);
        setPresets(presetsData.presets || {});
        
        // Initialize editing form with current values
        setEditedStyle(userData.personality.style);
        setEditedTone(userData.personality.tone);
      } catch (error) {
        console.error('Error loading user profile:', error);
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
      setEditedStyle(preset.style);
      setEditedTone(preset.tone);
    }
  };

  const handleSaveChanges = async () => {
    try {
      const updatedPersonality = {
        style: editedStyle,
        tone: editedTone,
        additional_traits: profile.personality.additional_traits || {}
      };
      
      await updateUserPersonality(updatedPersonality);
      
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
      console.error('Error updating personality:', error);
      alert('Failed to update personality settings');
    }
  };

  if (isLoading) {
    return <div className="user-profile-loading">Loading profile...</div>;
  }

  if (!profile) {
    return <div className="user-profile-error">User profile not found</div>;
  }

  return (
    <div className="user-profile">
      <div className="user-profile-header">
        <h3>User Settings</h3>
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
            }}
          >
            Cancel
          </button>
        )}
      </div>
      
      <div className="user-profile-content">
        {isEditing ? (
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
              onClick={handleSaveChanges}
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
    </div>
  );
};

export default UserProfile; 