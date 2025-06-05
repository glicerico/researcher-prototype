import React from 'react';
import { useSession } from '../context/SessionContext';
import '../styles/SessionHistorySidebar.css';

const SessionHistorySidebar = () => {
  const {
    userId,
    sessionHistory,
    sessionId,
    updateSessionId,
    updateMessages,
    resetSession,
  } = useSession();

  const loadSession = (sid) => {
    if (!userId) return;
    const stored = localStorage.getItem(`chat_messages_${userId}_${sid}`);
    if (stored) {
      try {
        updateMessages(JSON.parse(stored));
      } catch {
        updateMessages([
          { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" },
        ]);
      }
    } else {
      updateMessages([
        { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" },
      ]);
    }
    updateSessionId(sid);
  };

  const handleNewSession = () => {
    resetSession();
  };

  return (
    <div className="session-history-sidebar">
      <div className="sidebar-header">
        <h3>Sessions</h3>
        <button className="new-session-btn" onClick={handleNewSession} title="Start new session">
          +
        </button>
      </div>
      <ul className="session-list">
        {sessionHistory.map((sid) => (
          <li key={sid} className={sid === sessionId ? 'active' : ''}>
            <button onClick={() => loadSession(sid)}>{sid.slice(-8)}</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SessionHistorySidebar;
