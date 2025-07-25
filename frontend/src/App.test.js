import { render, screen } from '@testing-library/react';
import App from './App';

// Mock the api module
jest.mock('./services/api', () => ({
  getModels: jest.fn().mockResolvedValue({ 
    models: { 'gpt-4o-mini': { name: 'GPT-4o Mini', provider: 'OpenAI' } },
    default_model: 'gpt-4o-mini'
  }),
  getUsers: jest.fn().mockResolvedValue([]),
  getUserProfile: jest.fn().mockResolvedValue(null),
}));

describe('App Component (Unit Tests)', () => {
  test('renders AI Research Assistant heading', () => {
    render(<App />);
    const heading = screen.getByText(/AI Research Assistant/i);
    expect(heading).toBeInTheDocument();
  });

  test('renders navigation with correct links', () => {
    render(<App />);
    expect(screen.getByText(/💬 Chat/i)).toBeInTheDocument();
    expect(screen.getByText(/🔍 Research Topics/i)).toBeInTheDocument();
    expect(screen.getByText(/📊 Research Results/i)).toBeInTheDocument();
  });

  test('renders chat interface by default', () => {
    render(<App />);
    expect(screen.getByText(/AI Chatbot/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Type your message here/i)).toBeInTheDocument();
  });
});
