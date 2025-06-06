// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Suppress console.log during tests but keep errors for debugging
const originalConsole = global.console;
global.console = {
  ...console,
  log: jest.fn(), // Suppress debug logs
  // Keep error and warn for important issues, but filter out expected test errors
  error: (...args) => {
    const message = args[0]?.toString() || '';
    // Suppress expected network errors during testing
    if (message.includes('Network Error') || message.includes('ECONNREFUSED')) {
      return;
    }
    originalConsole.error(...args);
  }
};
