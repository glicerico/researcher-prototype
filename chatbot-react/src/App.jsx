import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import TypingIndicator from './components/TypingIndicator';
import DebugButton from './components/DebugButton';
import UserSelector from './components/UserSelector';
import UserProfile from './components/UserProfile';
import { getModels, sendChatMessage } from './services/api';
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

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
      
      // Send message to API
      const response = await sendChatMessage(apiMessages, selectedModel);
      
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
  const handleUserSelected = useCallback((newUserId) => {
    if (newUserId !== userId) {
      setUserId(newUserId);
      // Reset conversation when user changes
      setMessages([
        { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
      ]);
    }
  }, [userId]);

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
          <DebugButton 
            messages={messages}
            selectedModel={selectedModel}
            onDebugInfo={handleDebugInfo}
          />
          <button 
            className="user-button"
            onClick={handleToggleUserSelector}
            disabled={isLoading && !showUserSelector}
          >
            {showUserSelector ? 'Hide Users' : 'Select User'}
          </button>
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