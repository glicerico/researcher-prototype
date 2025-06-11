import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatPage from './ChatPage';
import { SessionProvider } from '../context/SessionContext';

// Mock necessary components and services
jest.mock('../services/api', () => ({
  sendMessage: jest.fn(() => Promise.resolve({ response: 'Mock response' })),
  getModels: jest.fn(() => Promise.resolve({ models: {} }))
}));

jest.mock('./Navigation', () => {
  return function MockNavigation() {
    return <div data-testid="navigation">Navigation</div>;
  };
});

jest.mock('./ChatInput', () => {
  return function MockChatInput() {
    return <div data-testid="chat-input">Chat Input</div>;
  };
});

jest.mock('./SessionHistory', () => {
  return function MockSessionHistory() {
    return <div data-testid="session-history">Session History</div>;
  };
});

jest.mock('./ConversationTopics', () => {
  return function MockConversationTopics() {
    return <div data-testid="conversation-topics">Topics</div>;
  };
});

const mockSessionContextValue = {
  currentSessionId: 'test-session',
  setCurrentSessionId: jest.fn(),
  messages: [],
  setMessages: jest.fn(),
  addMessage: jest.fn(),
  clearMessages: jest.fn()
};

describe('ChatPage Component', () => {
  test('renders without crashing', () => {
    render(
      <SessionProvider value={mockSessionContextValue}>
        <ChatPage />
      </SessionProvider>
    );
    
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('session-history')).toBeInTheDocument();
  });

  test('shows initial welcome message', () => {
    render(
      <SessionProvider value={mockSessionContextValue}>
        <ChatPage />
      </SessionProvider>
    );
    
    expect(screen.getByText(/Hello! I'm your AI assistant/)).toBeInTheDocument();
  });

  test('renders basic components correctly', () => {
    render(
      <SessionProvider value={mockSessionContextValue}>
        <ChatPage />
      </SessionProvider>
    );
    
    expect(screen.getByTestId('session-history')).toBeInTheDocument();
    expect(screen.getByTestId('conversation-topics')).toBeInTheDocument();
  });
}); 