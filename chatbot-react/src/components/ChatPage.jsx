import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSession } from '../context/SessionContext';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ModelSelector from './ModelSelector';
import TypingIndicator from './TypingIndicator';
import UserSelector from './UserSelector';
import UserProfile from './UserProfile';
import UserDropdown from './UserDropdown';
import ConversationTopics from './ConversationTopics';
import SessionHistory from './SessionHistory';
import { getModels, sendChatMessage, getCurrentUser } from '../services/api';
import { generateDisplayName } from '../utils/userUtils';
import '../App.css';

const ChatPage = () => {
  // Use SessionContext for shared state
  const {
    userId,
    sessionId,
    messages,
    userDisplayName,
    personality,
    updateUserId,
    updateSessionId,
    updateMessages,
    updatePersonality,
    updateUserDisplayName,
    updateConversationTopics,
  } = useSession();

  // Local state for UI components
  const [models, setModels] = useState({});
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [isTyping, setIsTyping] = useState(false);
  const [showUserSelector, setShowUserSelector] = useState(false);
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [profileUpdateTime, setProfileUpdateTime] = useState(0);
  
  // Topics sidebar state
  const [isTopicsSidebarCollapsed, setIsTopicsSidebarCollapsed] = useState(false);
  
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
  }, [userId, updateUserId, updateUserDisplayName, updatePersonality]);

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
    updateMessages(updatedMessages);
    
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
        personality, // Include personality in the request
        sessionId // Include session ID in the request
      );
      
      console.log('Chat response:', response);
      
      // Store session ID for conversation continuity
      if (response.session_id) {
        updateSessionId(response.session_id);
      }
      
      // Add assistant response to messages
      const assistantMessage = { 
        role: 'assistant', 
        content: response.response,
        routingInfo: response.routing_info
      };
      
      updateMessages(prev => [...prev, assistantMessage]);
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to chat
      const errorMessage = { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error while processing your message. Please try again.' 
      };
      updateMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
      setIsLoading(false);
    }
  };

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
    let userScrollingTimeout = null;
    
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatContainer;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 30;
      
      // If user scrolls up (away from bottom), mark as user scrolling
      if (!isAtBottom) {
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
            setUserScrolling(false);
          }
        }, 3000);
      } else {
        // User manually scrolled to bottom, reset the tracking
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

  // Topics sidebar handlers
  const handleToggleTopicsSidebar = useCallback(() => {
    setIsTopicsSidebarCollapsed(prev => !prev);
  }, []);

  const handleTopicUpdate = useCallback((topics) => {
    updateConversationTopics(topics);
  }, [updateConversationTopics]);

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
      
      <SessionHistory />

      <div
        className={`chat-content ${!isTopicsSidebarCollapsed ? 'with-sidebar' : ''} with-left-panel`}
      >
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

      {/* Conversation Topics Sidebar */}
      <ConversationTopics
        sessionId={sessionId}
        isCollapsed={isTopicsSidebarCollapsed}
        onToggleCollapse={handleToggleTopicsSidebar}
        onTopicUpdate={handleTopicUpdate}
      />
    </div>
  );
};

export default ChatPage; 