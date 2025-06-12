import React, { createContext, useContext, useState, useEffect } from 'react';
import { isAuthenticated, verifyToken, adminLogout } from '../services/adminApi';

const AdminContext = createContext();

export const useAdmin = () => {
  const context = useContext(AdminContext);
  if (!context) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
};

export const AdminProvider = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      if (isAuthenticated()) {
        // Verify token with server
        await verifyToken();
        setIsLoggedIn(true);
        setUser({ username: 'admin' }); // Simple user object
      } else {
        setIsLoggedIn(false);
        setUser(null);
      }
    } catch (error) {
      console.error('Auth verification failed:', error);
      setIsLoggedIn(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = (tokenData) => {
    setIsLoggedIn(true);
    setUser({ username: 'admin' });
  };

  const logout = () => {
    adminLogout();
    setIsLoggedIn(false);
    setUser(null);
  };

  const value = {
    isLoggedIn,
    loading,
    user,
    login,
    logout,
    checkAuthStatus
  };

  return (
    <AdminContext.Provider value={value}>
      {children}
    </AdminContext.Provider>
  );
}; 