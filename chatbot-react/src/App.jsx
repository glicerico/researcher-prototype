import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import TypingIndicator from './components/TypingIndicator';
import DebugButton from './components/DebugButton';
import UserSelector from './components/UserSelector';
import UserProfile from './components/UserProfile';
import UserDropdown from './components/UserDropdown';
import { getModels, sendChatMessage, getCurrentUser } from './services/api';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
  ]);
  const [models, setModels] = useState({});
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [isTyping, setIsTyping] = useState(false);
  const [userId, setUserId] = useState(localStorage.getItem('user_id') || '');
  const [showUserSelector, setShowUserSelector] = useState(false);
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [personality, setPersonality] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userDisplayName, setUserDisplayName] = useState('');
  
  const messagesEndRef = useRef(null);

  // Load available models on component mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const modelData = await getModels();
        setModels(modelData.models || {});
      } catch (error) {
        console.error('Error loading models:', error);
      }
    };
    
    loadModels();
  }, []);

  // Load user data when userId changes
  useEffect(() => {
    const loadUserData = async () => {
      console.log('Loading user data for userId:', userId);
      
      if (!userId) {
        console.log('No userId, resetting personality and display name');
        setPersonality(null);
        setUserDisplayName('');
        return;
      }
      
      try {
        setIsLoading(true);
        const userData = await getCurrentUser();
        console.log('User data loaded:', userData);
        
        // Set personality with fallback to default values
        setPersonality(userData?.personality || {
          style: 'helpful',
          tone: 'friendly'
        });
        
        // Set display name with fallback to user ID
        if (userData?.display_name) {
          console.log('Setting display name:', userData.display_name);
          setUserDisplayName(userData.display_name);
        } else {
          const shortId = userId.substring(userId.length - 6);
          console.log('No display name found, using ID fragment:', shortId);
          setUserDisplayName(`User ${shortId}`);
        }
      } catch (error) {
        console.error('Error loading user data:', error);
        // Set default values on error
        setPersonality({
          style: 'helpful',
          tone: 'friendly'
        });
        
        const shortId = userId.substring(userId.length - 6);
        setUserDisplayName(`User ${shortId}`);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadUserData();
  }, [userId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Generate a system message based on personality
  const getSystemMessage = useCallback(() => {
    if (!personality) {
      return { role: 'system', content: "You are a helpful assistant." };
    }
    
    const { style, tone, additional_traits } = personality;
    let content = `You are a ${style || 'helpful'} assistant. Please respond in a ${tone || 'friendly'} tone.`;
    
    // Add any additional traits if available
    if (additional_traits && Object.keys(additional_traits).length > 0) {
      const traits = Object.entries(additional_traits)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ');
        
      content += ` Additional traits: ${traits}.`;
    }
    
    return { role: 'system', content };
  }, [personality]);

  const handleSendMessage = async (message) => {
    if (isLoading) return; // Prevent sending when already loading
    
    // Add user message to chat
    const updatedMessages = [...messages, { role: 'user', content: message }];
    setMessages(updatedMessages);
    
    // Show typing indicator
    setIsTyping(true);
    setIsLoading(true);
    
    try {
      // Prepare messages for API
      const apiMessages = updatedMessages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      // Create or update system message
      const systemMessage = getSystemMessage();
      
      // Replace the first system message or add it if none exists
      const systemIndex = apiMessages.findIndex(msg => msg.role === 'system');
      if (systemIndex !== -1) {
        apiMessages[systemIndex] = systemMessage;
      } else {
        apiMessages.unshift(systemMessage);
      }
      
      // Send message to API with user ID
      const response = await sendChatMessage(
        apiMessages, 
        selectedModel,
        0.7,  // temperature
        1000,  // max tokens
        null,  // conversation ID
        personality // Include personality in the request
      );
      
      // Add assistant response
      setMessages([...updatedMessages, { role: 'assistant', content: response.response }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages([
        ...updatedMessages, 
        { role: 'system', content: `Sorry, there was an error: ${error.message}` }
      ]);
    } finally {
      setIsTyping(false);
      setIsLoading(false);
    }
  };

  const handleDebugInfo = (debugData) => {
    // Add debug info to messages
    setMessages([
      ...messages,
      { 
        role: 'system', 
        content: `
          Debug Info:
          API Key Set: ${debugData.api_key_set}
          Model: ${debugData.model}
          Messages: ${debugData.state.messages.length}
          ${JSON.stringify(debugData, null, 2)}
        `
      }
    ]);
  };

  // Use useCallback to avoid unnecessary re-creation of this function
  const handleUserSelected = useCallback((newUserId, displayName) => {
    console.log('User selected:', newUserId, 'Display name:', displayName);
    
    if (newUserId === userId) {
      console.log('Same user selected, no changes needed');
      return;
    }
    
    // Update user ID and store in localStorage
    setUserId(newUserId);
    localStorage.setItem('user_id', newUserId);
    
    // Set initial display name (may be updated when user data loads)
    setUserDisplayName(displayName || `User ${newUserId.substring(newUserId.length - 6)}`);
    
    // Reset conversation
    setMessages([
      { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
    ]);
    
    // User data will be loaded by the useEffect that depends on userId
    // No need to duplicate that logic here
  }, [userId]);

  // Update the system message when personality changes
  useEffect(() => {
    if (personality && messages.length > 0 && messages[0].role === 'system') {
      const systemMessage = getSystemMessage();
      setMessages(prevMessages => [
        { role: 'system', content: systemMessage.content },
        ...prevMessages.slice(1)
      ]);
    }
  }, [personality, getSystemMessage, messages]);

  const handleToggleUserSelector = useCallback(() => {
    setShowUserSelector(prevState => {
      // If we're currently showing and about to hide, don't change state if we're in the middle of an operation
      if (prevState && isLoading) return prevState;
      
      // Otherwise toggle the state
      const newState = !prevState;
      
      // If we're showing the user selector, hide the profile
      if (newState) setShowUserProfile(false);
      
      return newState;
    });
  }, [isLoading]);

  const handleToggleUserProfile = useCallback(() => {
    setShowUserProfile(prevState => {
      // If we're showing the profile, hide the user selector
      const newState = !prevState;
      if (newState) setShowUserSelector(false);
      return newState;
    });
  }, []);

  const handleProfileUpdated = useCallback((updatedPersonality) => {
    setPersonality(updatedPersonality);
  }, []);

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>AI Chatbot</h1>
        <div className="header-controls">
          <ModelSelector 
            models={models} 
            selectedModel={selectedModel} 
            onSelectModel={setSelectedModel} 
          />
          <UserDropdown 
            onUserSelected={handleUserSelected} 
            currentUserId={userId} 
            currentDisplayName={userDisplayName || 'Anonymous User'}
          />
          <DebugButton 
            messages={messages}
            selectedModel={selectedModel}
            onDebugInfo={handleDebugInfo}
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
      </div>
      
      {showUserSelector && (
        <div className="selector-container">
          <UserSelector onUserSelected={handleUserSelected} />
        </div>
      )}
      
      {showUserProfile && userId && (
        <div className="profile-container">
          <UserProfile 
            userId={userId} 
            onProfileUpdated={handleProfileUpdated} 
          />
        </div>
      )}
      
      <div className="chat-messages" id="chat-messages">
        {messages.map((msg, index) => (
          <ChatMessage key={index} role={msg.role} content={msg.content} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>
      
      <ChatInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading}
      />
    </div>
  );
}

export default App; 