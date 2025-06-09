import React, { useState, useEffect, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import ModelSelector from './ModelSelector';
import UserDropdown from './UserDropdown';
import UserProfile from './UserProfile';
import UserSelector from './UserSelector';
import { getModels, getCurrentUser } from '../services/api';
import { generateDisplayName } from '../utils/userUtils';
import '../styles/Navigation.css';

const Navigation = () => {
  const location = useLocation();
  const { 
    sessionId, 
    userDisplayName, 
    messages, 
    userId,
    personality,
    selectedModel,
    updateUserId,
    updateUserDisplayName,
    updatePersonality,
    updateMessages,
    updateSelectedModel
  } = useSession();

  // Chat-specific state (only used on chat page)
  const [models, setModels] = useState({});
  const [showUserSelector, setShowUserSelector] = useState(false);
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [profileUpdateTime, setProfileUpdateTime] = useState(0);

  const isOnChatPage = location.pathname === '/';

  // Load available models on component mount (for chat page)
  useEffect(() => {
    if (!isOnChatPage) return;
    
    const loadModels = async () => {
      try {
        const modelData = await getModels();
        setModels(modelData.models || {});
      } catch (error) {
        console.error('Error loading models:', error);
      }
    };
    
    loadModels();
  }, [isOnChatPage]);

  // Load user data when userId changes (for chat page)
  useEffect(() => {
    if (!isOnChatPage) return;
    
    const loadUserData = async () => {
      console.log('Loading user data for userId:', userId);
      
      if (!userId) {
        console.log('No userId, resetting personality and display name');
        updatePersonality(null);
        updateUserDisplayName('');
        return;
      }
      
      try {
        setIsLoading(true);
        const userData = await getCurrentUser();
        console.log('User data loaded:', userData);
        
        // Set personality with fallback to default values
        updatePersonality(userData?.personality || {
          style: 'helpful',
          tone: 'friendly'
        });
        
        // Set display name with fallback to user ID
        if (userData?.display_name) {
          console.log('Setting display name:', userData.display_name);
          updateUserDisplayName(userData.display_name);
        } else {
          const fallbackDisplayName = generateDisplayName(userId);
          console.log('No display name found, using generated name:', fallbackDisplayName);
          updateUserDisplayName(fallbackDisplayName);
        }
      } catch (error) {
        console.error('Error loading user data:', error);
        
        // If we get a 404, it means the user no longer exists
        if (error.response && error.response.status === 404) {
          console.log('User no longer exists, clearing localStorage and resetting state');
          localStorage.removeItem('user_id');
          updateUserId('');
          updateUserDisplayName('');
          updatePersonality(null);
          return;
        }
        
        // For other errors, set default values
        updatePersonality({
          style: 'helpful',
          tone: 'friendly'
        });
        
        const fallbackDisplayName = generateDisplayName(userId);
        updateUserDisplayName(fallbackDisplayName);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadUserData();
  }, [userId, isOnChatPage, updateUserId, updateUserDisplayName, updatePersonality]);

  const handleUserSelected = useCallback((selectedUserId, displayName) => {
    console.log('User selected:', selectedUserId, 'Display name:', displayName);

    if (selectedUserId) {
      updateUserId(selectedUserId);
      // Update display name if provided
      if (displayName) {
        updateUserDisplayName(displayName);
      }
    } else {
      updateUserId('');
      updateUserDisplayName('');
    }
    
    // Hide the user selector after selection
    setShowUserSelector(false);
  }, [updateUserId, updateUserDisplayName]);

  const handleToggleUserProfile = useCallback(() => {
    setShowUserProfile(prevState => {
      // If we're showing the profile, hide the user selector
      const newState = !prevState;
      if (newState) setShowUserSelector(false);
      return newState;
    });
  }, []);

  const handleProfileUpdated = useCallback((updatedPersonality) => {
    console.log('Profile updated with new personality:', updatedPersonality);
    
    // Update personality in state
    updatePersonality(updatedPersonality);
    
    // Trigger UserDropdown reload
    setProfileUpdateTime(Date.now());
    
    // Update the system message immediately
    const systemMessage = {
      role: 'system', 
      content: `You are a ${updatedPersonality.style || 'helpful'} assistant. Please respond in a ${updatedPersonality.tone || 'friendly'} tone.`
    };
    
    // Update the first message if it's a system message
    updateMessages(prevMessages => {
      if (prevMessages.length > 0 && prevMessages[0].role === 'system') {
        return [systemMessage, ...prevMessages.slice(1)];
      }
      return [systemMessage, ...prevMessages];
    });
  }, [updatePersonality, updateMessages]);



  return (
    <>
      <nav className="navigation">
        <div className="nav-container">
          <div className="nav-brand">
            <h2>AI Research Assistant</h2>
          </div>
          
          <div className="nav-center">
            <div className="nav-links">
              <Link 
                to="/" 
                className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
              >
                💬 Chat
              </Link>
              <Link 
                to="/topics" 
                className={`nav-link ${location.pathname === '/topics' ? 'active' : ''}`}
              >
                🔍 Research Topics
              </Link>
              <Link 
                to="/research-results" 
                className={`nav-link ${location.pathname === '/research-results' ? 'active' : ''}`}
              >
                📊 Research Results
              </Link>
            </div>
          </div>

          {isOnChatPage && (
            <div className="chat-controls">
              <ModelSelector 
                models={models} 
                selectedModel={selectedModel} 
                onSelectModel={updateSelectedModel} 
              />
              <UserDropdown 
                onUserSelected={handleUserSelected} 
                currentUserId={userId} 
                currentDisplayName={userDisplayName || 'Anonymous User'}
                profileUpdateTime={profileUpdateTime}
              />
              {userId && (
                <button 
                  className="profile-button"
                  onClick={handleToggleUserProfile}
                >
                  {showUserProfile ? 'Hide Settings' : 'User Settings'}
                </button>
              )}
            </div>
          )}
        </div>
      </nav>
      
      {isOnChatPage && showUserSelector && (
        <div className="selector-container">
          <UserSelector onUserSelected={handleUserSelected} />
        </div>
      )}
      
      {isOnChatPage && showUserProfile && userId && (
        <div className="profile-modal-overlay" onClick={handleToggleUserProfile}>
          <div className="profile-modal-content" onClick={(e) => e.stopPropagation()}>
            <UserProfile 
              userId={userId} 
              onProfileUpdated={handleProfileUpdated} 
            />
          </div>
        </div>
      )}
    </>
  );
};

export default Navigation; 