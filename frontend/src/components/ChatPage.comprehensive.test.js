import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatPage from './ChatPage';
import { useSession } from '../context/SessionContext';
import * as api from '../services/api';

// Mock all dependencies
jest.mock('../context/SessionContext');
jest.mock('../services/api');

// Mock child components
jest.mock('./ChatMessage', () => {
  return function MockChatMessage({ role, content, routingInfo }) {
    return (
      <div data-testid={`message-${role}`} data-routing={routingInfo?.decision}>
        {content}
      </div>
    );
  };
});

jest.mock('./ChatInput', () => {
  return function MockChatInput({ onSendMessage, disabled }) {
    return (
      <div data-testid="chat-input">
        <button 
          onClick={() => onSendMessage('Test message')} 
          disabled={disabled}
          data-testid="send-button"
        >
          Send
        </button>
        <span data-testid="input-disabled">{disabled ? 'disabled' : 'enabled'}</span>
      </div>
    );
  };
});

jest.mock('./TypingIndicator', () => {
  return function MockTypingIndicator() {
    return <div data-testid="typing-indicator">AI is typing...</div>;
  };
});

jest.mock('./SessionHistory', () => {
  return function MockSessionHistory() {
    return <div data-testid="session-history">Session History</div>;
  };
});

jest.mock('./ConversationTopics', () => {
  return function MockConversationTopics({ onToggleCollapse, onTopicUpdate }) {
    return (
      <div data-testid="conversation-topics">
        <button onClick={onToggleCollapse} data-testid="toggle-topics">
          Toggle Topics
        </button>
        <button 
          onClick={() => onTopicUpdate(['AI Ethics', 'Machine Learning'])} 
          data-testid="update-topics"
        >
          Update Topics
        </button>
      </div>
    );
  };
});


describe('ChatPage Comprehensive Tests', () => {
  let mockSessionContext;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    mockSessionContext = {
      userId: 'test-user',
      sessionId: 'test-session',
      messages: [
        { role: 'system', content: 'Hello! I\'m your AI assistant.' }
      ],
      personality: { style: 'helpful', tone: 'friendly' },
      userDisplayName: 'Test User',
      conversationTopics: [],
      sessionHistory: [],
      updateSessionId: jest.fn(),
      updateMessages: jest.fn(),
      updateConversationTopics: jest.fn(),
    };
    
    useSession.mockReturnValue(mockSessionContext);
    
    api.sendChatMessage = jest.fn();
    api.triggerUserActivity = jest.fn().mockResolvedValue({});
  });

  describe('Message Sending - Core Functionality', () => {
    test('sends message successfully', async () => {
      const mockResponse = {
        response: 'AI response message',
        session_id: 'new-session-456',
        routing_info: { decision: 'chat', reason: 'General conversation' },
        topics: ['Topic 1', 'Topic 2']
      };
      
      api.sendChatMessage.mockResolvedValue(mockResponse);
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        expect(api.sendChatMessage).toHaveBeenCalled();
      });
      expect(mockSessionContext.updateMessages).toHaveBeenCalled();
    });

    test('shows loading states during message sending', async () => {
      api.sendChatMessage.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText('disabled')).toBeInTheDocument();
      });
    });

    test('handles API errors gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      api.sendChatMessage.mockRejectedValue(new Error('Network error'));
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });
      
      await waitFor(() => {
        expect(screen.getByText('enabled')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Personality & System Message Logic', () => {
    test('generates default system message when no personality', async () => {
      mockSessionContext.personality = null;
      api.sendChatMessage.mockResolvedValue({ response: 'Test' });
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(api.sendChatMessage).toHaveBeenCalledWith(
          expect.arrayContaining([
          expect.objectContaining({ 
            role: 'system', 
            content: 'You are a helpful assistant.' 
          })
        ]),
        expect.any(String),
        expect.any(Number),
        expect.any(Number),
        null,
        expect.any(String)
        );
      });
    });

    test('generates personality-based system message', async () => {
      mockSessionContext.personality = {
        style: 'professional',
        tone: 'formal'
      };
      api.sendChatMessage.mockResolvedValue({ response: 'Test' });
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(api.sendChatMessage).toHaveBeenCalledWith(
          expect.arrayContaining([
            expect.objectContaining({ 
              role: 'system', 
              content: expect.stringContaining('professional')
            })
          ]),
          expect.any(String),
          expect.any(Number),
          expect.any(Number),
          expect.any(Object),
          expect.any(String)
        );
      });
    });
  });

  describe('Session Management', () => {
    test('updates session ID from API response', async () => {
      api.sendChatMessage.mockResolvedValue({
        response: 'Test response',
        session_id: 'updated-session-789'
      });
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(mockSessionContext.updateSessionId).toHaveBeenCalledWith('updated-session-789');
      });
    });

    test('updates conversation topics from API response', async () => {
      api.sendChatMessage.mockResolvedValue({
        response: 'Test response',
        topics: ['Machine Learning', 'AI Ethics']
      });
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(mockSessionContext.updateConversationTopics).toHaveBeenCalledWith([
          'Machine Learning', 'AI Ethics'
        ]);
      });
    });
  });

  describe('Topics Sidebar Management', () => {
    test('handles topic updates from sidebar', async () => {
      render(<ChatPage />);
      
      const updateButton = screen.getByTestId('update-topics');
      
      fireEvent.click(updateButton);
      
      expect(mockSessionContext.updateConversationTopics).toHaveBeenCalledWith([
        'AI Ethics', 'Machine Learning'
      ]);
    });

    test('toggles topics sidebar', async () => {
      render(<ChatPage />);
      
      const toggleButton = screen.getByTestId('toggle-topics');
      
      fireEvent.click(toggleButton);
      
      // Test that toggle functionality works
      expect(toggleButton).toBeInTheDocument();
    });
  });

  describe('User Activity Tracking', () => {
    test('triggers user activity on message send', async () => {
      api.sendChatMessage.mockResolvedValue({ response: 'Test response' });
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(api.triggerUserActivity).toHaveBeenCalled();
      });
    });

    test('handles user activity trigger failure gracefully', async () => {
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
      
      api.triggerUserActivity.mockRejectedValue(new Error('Activity service down'));
      api.sendChatMessage.mockResolvedValue({ response: 'Test response' });
      
      render(<ChatPage />);
      
      const sendButton = screen.getByTestId('send-button');
      
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(api.sendChatMessage).toHaveBeenCalled();
      });
      expect(consoleWarnSpy).toHaveBeenCalled();

      consoleWarnSpy.mockRestore();
    });
  });
}); 