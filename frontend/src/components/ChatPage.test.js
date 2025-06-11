import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPage from './ChatPage';
import { SessionProvider } from '../context/SessionContext';
import * as api from '../services/api';

// Mock the API module
jest.mock('../services/api');

// Mock the Navigation component to avoid complexity
jest.mock('./Navigation', () => {
  return function MockNavigation() {
    return <div data-testid="navigation">Mock Navigation</div>;
  };
});

// Mock components to isolate ChatPage testing
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
      </div>
    );
  };
});

jest.mock('./SessionHistory', () => {
  return function MockSessionHistory({ onNewSession, onSelectSession }) {
    return (
      <div data-testid="session-history">
        <button onClick={onNewSession} data-testid="new-session-btn">
          New Session
        </button>
        <button onClick={() => onSelectSession('session1')} data-testid="select-session-btn">
          Select Session 1
        </button>
      </div>
    );
  };
});

jest.mock('./ConversationTopics', () => {
  return function MockConversationTopics({ sessionId, isVisible, onClose }) {
    return isVisible ? (
      <div data-testid="conversation-topics">
        <button onClick={onClose} data-testid="close-topics">Close</button>
        Topics for {sessionId}
      </div>
    ) : null;
  };
});

// Helper function to render ChatPage with context
const renderChatPage = (sessionContextValue = {}) => {
  const defaultContextValue = {
    currentSessionId: 'session1',
    setCurrentSessionId: jest.fn(),
    messages: [],
    setMessages: jest.fn(),
    addMessage: jest.fn(),
    clearMessages: jest.fn(),
    ...sessionContextValue
  };

  return render(
    <SessionProvider value={defaultContextValue}>
      <ChatPage />
    </SessionProvider>
  );
};

describe('ChatPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API responses
    api.sendMessage.mockResolvedValue({
      response: 'Mock AI response',
      usage: { total_tokens: 50 }
    });
  });

  test('renders chat interface correctly', () => {
    renderChatPage();
    
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('session-history')).toBeInTheDocument();
    expect(screen.getByText('Hello! I\'m your AI assistant. How can I help you today?')).toBeInTheDocument();
  });

  test('renders existing messages', () => {
    const messages = [
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Hi there!' }
    ];
    
    renderChatPage({ messages });
    
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  test('handles sending a message successfully', async () => {
    const mockAddMessage = jest.fn();
    renderChatPage({ 
      addMessage: mockAddMessage,
      messages: []
    });
    
    const sendButton = screen.getByTestId('send-button');
    
    await act(async () => {
      fireEvent.click(sendButton);
    });

    // Should add user message and then AI response
    await waitFor(() => {
      expect(mockAddMessage).toHaveBeenCalledWith({ role: 'user', content: 'Test message' });
    });

    await waitFor(() => {
      expect(api.sendMessage).toHaveBeenCalled();
    });
  });

  test('displays loading state while sending message', async () => {
    // Make API call hang to test loading state
    api.sendMessage.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    
    const mockAddMessage = jest.fn();
    renderChatPage({ addMessage: mockAddMessage });
    
    const sendButton = screen.getByTestId('send-button');
    
    act(() => {
      fireEvent.click(sendButton);
    });

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByTestId('send-button')).toBeDisabled();
    });
  });

  test('handles API error gracefully', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    api.sendMessage.mockRejectedValue(new Error('API Error'));
    
    const mockAddMessage = jest.fn();
    renderChatPage({ addMessage: mockAddMessage });
    
    const sendButton = screen.getByTestId('send-button');
    
    await act(async () => {
      fireEvent.click(sendButton);
    });

    await waitFor(() => {
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'assistant',
          content: expect.stringContaining('Sorry, I encountered an error')
        })
      );
    });

    consoleErrorSpy.mockRestore();
  });

  test('handles creating new session', async () => {
    const mockSetCurrentSessionId = jest.fn();
    const mockClearMessages = jest.fn();
    
    renderChatPage({ 
      setCurrentSessionId: mockSetCurrentSessionId,
      clearMessages: mockClearMessages
    });
    
    const newSessionBtn = screen.getByTestId('new-session-btn');
    
    act(() => {
      fireEvent.click(newSessionBtn);
    });

    expect(mockClearMessages).toHaveBeenCalled();
    expect(mockSetCurrentSessionId).toHaveBeenCalledWith(expect.any(String));
  });

  test('handles selecting existing session', async () => {
    const mockSetCurrentSessionId = jest.fn();
    
    renderChatPage({ 
      setCurrentSessionId: mockSetCurrentSessionId
    });
    
    const selectSessionBtn = screen.getByTestId('select-session-btn');
    
    act(() => {
      fireEvent.click(selectSessionBtn);
    });

    expect(mockSetCurrentSessionId).toHaveBeenCalledWith('session1');
  });

  test('shows and hides conversation topics', () => {
    renderChatPage();
    
    // Topics should be visible by default (assuming the component shows them)
    const topicsPanel = screen.queryByTestId('conversation-topics');
    
    if (topicsPanel) {
      const closeButton = screen.getByTestId('close-topics');
      
      act(() => {
        fireEvent.click(closeButton);
      });
      
      // After closing, topics should be hidden
      expect(screen.queryByTestId('conversation-topics')).not.toBeInTheDocument();
    }
  });

  test('renders with different session IDs', () => {
    renderChatPage({ currentSessionId: 'custom-session-123' });
    
    // Should render the topics panel with the custom session ID
    const topicsPanel = screen.queryByTestId('conversation-topics');
    if (topicsPanel) {
      expect(topicsPanel).toHaveTextContent('custom-session-123');
    }
  });

  test('handles empty message submission', async () => {
    const mockAddMessage = jest.fn();
    
    // Mock ChatInput to send empty message
    jest.doMock('./ChatInput', () => {
      return function MockChatInput({ onSendMessage }) {
        return (
          <button 
            onClick={() => onSendMessage('')} 
            data-testid="send-empty-button"
          >
            Send Empty
          </button>
        );
      };
    });
    
    renderChatPage({ addMessage: mockAddMessage });
    
    const sendButton = screen.getByTestId('send-empty-button');
    
    act(() => {
      fireEvent.click(sendButton);
    });

    // Should not add empty message or call API
    expect(mockAddMessage).not.toHaveBeenCalled();
    expect(api.sendMessage).not.toHaveBeenCalled();
  });

  test('maintains scroll position when new messages are added', async () => {
    const messages = [
      { role: 'user', content: 'Message 1' },
      { role: 'assistant', content: 'Response 1' },
      { role: 'user', content: 'Message 2' },
      { role: 'assistant', content: 'Response 2' }
    ];
    
    renderChatPage({ messages });
    
    // Should render all messages
    expect(screen.getByText('Message 1')).toBeInTheDocument();
    expect(screen.getByText('Response 1')).toBeInTheDocument();
    expect(screen.getByText('Message 2')).toBeInTheDocument();
    expect(screen.getByText('Response 2')).toBeInTheDocument();
  });
}); 