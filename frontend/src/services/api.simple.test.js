import { getModels } from './api';

// Mock the axios module
jest.mock('axios', () => ({
  create: () => ({
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: {
        use: jest.fn()
      }
    }
  })
}));

describe('API Service Basic Tests', () => {
  test('getModels function exists', () => {
    expect(typeof getModels).toBe('function');
  });

  test('can import API functions', () => {
    expect(getModels).toBeDefined();
  });
}); 