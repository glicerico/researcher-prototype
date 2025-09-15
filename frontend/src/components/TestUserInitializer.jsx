import React, { useState, useEffect } from 'react';
import { createUser, getCurrentUser } from '../services/api';
import '../styles/TestUserInitializer.css';

const TestUserInitializer = ({ onInitialized }) => {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
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
    // Pre-fill a random username
    if (!username) {
      const rand = Math.random().toString(36).slice(2, 6);
      setUsername(`user-${rand}`);
    }
  }, [onInitialized]);

  const createUserWithOptionalEmail = async () => {
    try {
      setLoading(true);
      setError(null);
      if (!username || !username.trim()) {
        setError('Please provide a username');
        setLoading(false);
        return;
      }
      const payload = { display_name: username.trim() };
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
        <p>Choose a username and optionally add an email to continue.</p>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={loading}
        />
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
        </div>
      </div>
    </div>
  );
};

export default TestUserInitializer;


