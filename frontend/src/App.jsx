import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { AdminProvider } from './context/AdminContext';
import Navigation from './components/Navigation';
import ChatPage from './components/ChatPage';
import TopicsDashboard from './components/TopicsDashboard';
import ResearchResultsDashboard from './components/ResearchResultsDashboard';
import AdminLogin from './components/admin/AdminLogin';
import AdminDashboard from './components/admin/AdminDashboard';
import ProtectedAdminRoute from './components/admin/ProtectedAdminRoute';
import './App.css';

function App() {
  return (
    <SessionProvider>
      <AdminProvider>
        <Router
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true
          }}
        >
          <div className="app">
            <Routes>
              {/* Admin routes - no navigation header */}
              <Route path="/admin/login" element={<AdminLogin />} />
              <Route path="/admin" element={
                <ProtectedAdminRoute>
                  <AdminDashboard />
                </ProtectedAdminRoute>
              } />
              
              {/* Main app routes - with navigation */}
              <Route path="/*" element={
                <>
                  <Navigation />
                  <main className="main-content">
                    <Routes>
                      <Route path="/" element={<ChatPage />} />
                      <Route path="/topics" element={<TopicsDashboard />} />
                      <Route path="/research-results" element={<ResearchResultsDashboard />} />
                    </Routes>
                  </main>
                </>
              } />
            </Routes>
          </div>
        </Router>
      </AdminProvider>
    </SessionProvider>
  );
}

export default App; 