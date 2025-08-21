import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { AdminProvider } from './context/AdminContext';
import { NotificationProvider } from './context/NotificationContext';
import ChatPage from './components/ChatPage';
import TopicsDashboard from './components/TopicsDashboard';
import ResearchResultsDashboard from './components/ResearchResultsDashboard';
import AdminLogin from './components/admin/AdminLogin';
import AdminDashboard from './components/admin/AdminDashboard';
import ProtectedAdminRoute from './components/admin/ProtectedAdminRoute';
import ToastNotifications from './components/ToastNotifications';
import Layout from './components/Layout';
import './utils/testDataIsolation'; // Import test utilities for debugging
import './App.css';

function App() {
  return (
    <SessionProvider>
      <AdminProvider>
        <NotificationProvider>
          <Router>
            <div className="app">
              <Routes>
                {/* Admin routes - no navigation header */}
                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin" element={
                  <ProtectedAdminRoute>
                    <AdminDashboard />
                  </ProtectedAdminRoute>
                } />

                {/* Main app routes - with navigation via Layout */}
                <Route element={<Layout />}>
                  <Route index element={<ChatPage />} />
                  <Route path="topics" element={<TopicsDashboard />} />
                  <Route path="research-results" element={<ResearchResultsDashboard />} />
                </Route>
              </Routes>
              <ToastNotifications />
            </div>
          </Router>
        </NotificationProvider>
      </AdminProvider>
    </SessionProvider>
  );
}

export default App; 
