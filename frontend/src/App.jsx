import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import Navigation from './components/Navigation';
import ChatPage from './components/ChatPage';
import TopicsDashboard from './components/TopicsDashboard';
import ResearchResultsDashboard from './components/ResearchResultsDashboard';
import './utils/testDataIsolation'; // Import test utilities for debugging
import './App.css';

function App() {
  return (
    <SessionProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true
        }}
      >
        <div className="app">
          <Navigation />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<ChatPage />} />
              <Route path="/topics" element={<TopicsDashboard />} />
              <Route path="/research-results" element={<ResearchResultsDashboard />} />
            </Routes>
          </main>
        </div>
      </Router>
    </SessionProvider>
  );
}

export default App; 