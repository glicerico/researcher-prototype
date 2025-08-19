import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSession } from '../context/SessionContext';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import TypingIndicator from './TypingIndicator';
import SessionHistory from './SessionHistory';
import ConversationTopics from './ConversationTopics';
import { sendChatMessage, triggerUserActivity, API_URL } from '../services/api';
import { useEngagementTracking } from '../utils/engagementTracker';
import '../App.css';

const ChatPage = () => {
  // Use SessionContext for shared state
  const {
    sessionId,
    messages,
    personality,
    userId,
    updateSessionId,
    updateMessages,
    updateConversationTopics,
  } = useSession();

  const { trackSessionContinuation } = useEngagementTracking();

  // Local state for UI components
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [chatInputValue, setChatInputValue] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  
  // Topics sidebar state
  const [isTopicsSidebarCollapsed, setIsTopicsSidebarCollapsed] = useState(false);
  
  const messagesEndRef = useRef(null);



  // Subscribe to backend status updates via SSE
  useEffect(() => {
    if (!sessionId) return;
    const es = new EventSource(`${API_URL}/status/${sessionId}`);
    es.onmessage = (e) => {
      const message = e.data;
      setStatusMessage(message);
      
      // Note: Status is now cleared immediately when response is displayed,
      // so we don't need to handle "Complete" messages specially here
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [sessionId]);

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
    setChatInputValue(''); // Clear the input after sending
    
    // Show typing indicator and start timing
    setIsTyping(true);
    setIsLoading(true);
    
    try {
      // Trigger user activity for motivation system (fire and forget)
      triggerUserActivity().catch(err => {
        console.warn('Failed to trigger user activity for motivation system:', err);
      });

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
      
      // Combine routing_analysis (detailed metrics) with module_used (fallback)
      const routingInfo = {
        ...(response.routing_analysis || {}),
        module_used: response.module_used || (response.routing_analysis ? response.routing_analysis.decision : undefined),
      };

      // Add assistant response to messages
      const assistantMessage = { 
        role: 'assistant', 
        content: response.response,
        routingInfo,
        follow_up_questions: response.follow_up_questions || [],
      };
      
      updateMessages(prev => [...prev, assistantMessage]);
      
      // Track session continuation (user continuing conversation)
      if (sessionId && messages.length > 0) {
        trackSessionContinuation(sessionId, 'new_message');
      }
      
      // Clear status message immediately when response is displayed
      setStatusMessage('');
      
      // Update conversation topics if they exist in the response
      if (response.topics && response.topics.length > 0) {
        updateConversationTopics(response.topics);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Clear status message on error
      setStatusMessage('');
      
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

  const handleFollowUpClick = (question) => {
    setChatInputValue(question);
    // Optional: focus the input field
    document.getElementById('user-input')?.focus();
  };

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
              followUpQuestions={msg.follow_up_questions}
              onFollowUpClick={handleFollowUpClick}
              messageId={`${sessionId}_${index}`}
            />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
          {statusMessage && (
            <div className="status-update" role="status">{statusMessage}</div>
          )}

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
          value={chatInputValue}
          onChange={setChatInputValue}
          onSendMessage={handleSendMessage} 
          disabled={isLoading}
        />

        {isTopicsSidebarCollapsed && <div className="sidebar-placeholder" />}

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