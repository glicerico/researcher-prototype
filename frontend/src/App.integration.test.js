import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

// Integration tests - these test against the real backend
describe('App Integration Tests', () => {
  // These tests only run if the backend is available
  const isBackendAvailable = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      return response.ok;
    } catch (error) {
      return false;
    }
  };

  beforeAll(async () => {
    const backendUp = await isBackendAvailable();
    if (!backendUp) {
      console.warn('⚠️  Backend not available - skipping integration tests');
      console.warn('   Start backend with: cd backend && python app.py');
    }
  });

  test('loads models from real backend', async () => {
    const backendUp = await isBackendAvailable();
    if (!backendUp) {
      pending('Backend not available');
      return;
    }

    render(<App />);
    
    // Wait for models to load
    await waitFor(() => {
      const modelSelect = screen.getByDisplayValue(/gpt-4o-mini/i);
      expect(modelSelect).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  test('handles backend connection errors gracefully', async () => {
    // This test runs even if backend is down
    render(<App />);
    
    // App should still render even if backend calls fail
    expect(screen.getByText(/AI Research Assistant/i)).toBeInTheDocument();
    
    // Should show default model option even if loading fails
    expect(screen.getByText(/GPT-4o-mini/i)).toBeInTheDocument();
  });
});

// Helper to skip tests when backend is not available
function pending(message) {
  console.log(`⏸️  Test skipped: ${message}`);
} 