import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import TypingIndicator from './components/TypingIndicator';
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
  const [profileUpdateTime, setProfileUpdateTime] = useState(0);
  
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
        personality // Include personality in the request
      );
      
      console.log('Chat response:', response);
      
      // Add assistant response with routing info
      setMessages([
        ...updatedMessages, 
        { 
          role: 'assistant', 
          content: response.response,
          routingInfo: response.routing_analysis || { module_used: response.module_used }
        }
      ]);
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
    console.log('Profile updated with new personality:', updatedPersonality);
    
    // Update personality in state
    setPersonality(updatedPersonality);
    
    // Trigger UserDropdown reload
    setProfileUpdateTime(Date.now());
    
    // Update the system message immediately
    const systemMessage = {
      role: 'system', 
      content: `You are a ${updatedPersonality.style || 'helpful'} assistant. Please respond in a ${updatedPersonality.tone || 'friendly'} tone.`
    };
    
    // Update the first message if it's a system message
    setMessages(prevMessages => {
      if (prevMessages.length > 0 && prevMessages[0].role === 'system') {
        return [systemMessage, ...prevMessages.slice(1)];
      }
      return [systemMessage, ...prevMessages];
    });
  }, []);

  // Add a ref to track user scroll position
  const chatContainerRef = useRef(null);
  // Add state to track if user is manually scrolling
  const [userScrolling, setUserScrolling] = useState(false);

  // Add scroll event listener to detect manual scrolling
  useEffect(() => {
    // Reference to chat container
    const chatContainer = document.getElementById('chat-messages');
    if (!chatContainer) return;
    
    // Scroll tracking variables
    let isUserScrolling = false;
    let userScrollingTimeout = null;
    
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatContainer;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 30;
      
      // If user scrolls up (away from bottom), mark as user scrolling
      if (!isAtBottom) {
        isUserScrolling = true;
        setUserScrolling(true);
        
        // Clear existing timeout if any
        if (userScrollingTimeout) {
          clearTimeout(userScrollingTimeout);
        }
        
        // Reset after a period of inactivity (3 seconds)
        userScrollingTimeout = setTimeout(() => {
          const currentPos = chatContainer.scrollTop;
          const currentMax = chatContainer.scrollHeight - chatContainer.clientHeight;
          const currentIsAtBottom = (currentMax - currentPos) < 30;
          
          // Only reset if user has scrolled back to bottom
          if (currentIsAtBottom) {
            isUserScrolling = false;
            setUserScrolling(false);
          }
        }, 3000);
      } else {
        // User manually scrolled to bottom, reset the tracking
        isUserScrolling = false;
        setUserScrolling(false);
        
        if (userScrollingTimeout) {
          clearTimeout(userScrollingTimeout);
          userScrollingTimeout = null;
        }
      }
    };
    
    chatContainer.addEventListener('scroll', handleScroll);
    
    // Cleanup function
    return () => {
      chatContainer.removeEventListener('scroll', handleScroll);
      if (userScrollingTimeout) {
        clearTimeout(userScrollingTimeout);
      }
    };
  }, []); // No dependencies so it only runs once on mount

  // Scroll to bottom when messages change, respecting user scrolling
  useEffect(() => {
    // Don't auto-scroll if user is manually scrolling
    if (!userScrolling && messagesEndRef.current) {
      // Brief delay to ensure content has rendered
      setTimeout(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    }
  }, [messages, userScrolling]);

  // Handle manual scrolling to latest message
  const scrollToLatest = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      // Will be reset automatically by the scroll handler
    }
  };

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
      
      <div className="chat-messages" id="chat-messages" ref={chatContainerRef}>
        {messages.map((msg, index) => (
          <ChatMessage 
            key={index} 
            role={msg.role} 
            content={msg.content} 
            routingInfo={msg.routingInfo}
          />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
        
        {userScrolling && (
          <button 
            className="scroll-to-latest-button"
            onClick={scrollToLatest}
          >
            ↓ Latest Messages
          </button>
        )}
      </div>
      
      <ChatInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading}
      />
    </div>
  );
}

export default App; 