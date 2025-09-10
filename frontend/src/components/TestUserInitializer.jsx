import React, { useState, useEffect } from 'react';
import { createUser, getCurrentUser } from '../services/api';

const TestUserInitializer = ({ onInitialized }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // If a user_id already exists, try to fetch and proceed
    const existingUserId = localStorage.getItem('user_id');
    if (existingUserId) {
      (async () => {
        try {
          await getCurrentUser();
          onInitialized(existingUserId);
        } catch (e) {
          // If not found, clear it and stay on initializer
          if (e?.response?.status === 404) {
            localStorage.removeItem('user_id');
          }
        }
      })();
    }
  }, [onInitialized]);

  const continueAsGuest = async () => {
    try {
      setLoading(true);
      setError(null);
      // Guest user is handled by the backend when no header is present.
      localStorage.setItem('user_id', 'guest');
      onInitialized('guest');
    } catch (e) {
      setError('Failed to continue as guest');
    } finally {
      setLoading(false);
    }
  };

  const createUserWithOptionalEmail = async () => {
    try {
      setLoading(true);
      setError(null);
      const payload = {};
      if (email && email.trim()) {
        payload.email = email.trim();
      }
      const result = await createUser(payload);
      if (result?.user_id) {
        localStorage.setItem('user_id', result.user_id);
        onInitialized(result.user_id, result.display_name || result.user_id);
      } else {
        setError('Failed to create user');
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Error creating user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="test-user-initializer">
      <div className="initializer-card">
        <h3>Set up your test user</h3>
        <p>Enter an email (optional) or continue as guest.</p>
        <input
          type="email"
          placeholder="Email (optional)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
        />
        {error && <div className="initializer-error">{error}</div>}
        <div className="initializer-actions">
          <button onClick={createUserWithOptionalEmail} disabled={loading}>
            {loading ? 'Creating…' : 'Create User'}
          </button>
          <button onClick={continueAsGuest} disabled={loading}>
            Continue as Guest
          </button>
        </div>
      </div>
    </div>
  );
};

export default TestUserInitializer;


