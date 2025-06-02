import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import ChatPage from './components/ChatPage';
import TopicsDashboard from './components/TopicsDashboard';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Navigation />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/topics" element={<TopicsDashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App; 