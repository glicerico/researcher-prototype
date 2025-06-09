import React from 'react';
import { useSession } from '../context/SessionContext';
import '../styles/SessionHistory.css';

const SessionHistory = () => {
  const { sessionHistory, sessionId, switchSession, startNewSession } = useSession();

  return (
    <div className="session-history">
      <h3>Sessions</h3>
      <ul>
        {sessionHistory.map((id) => (
          <li key={id} className={id === sessionId ? 'active' : ''}>
            <button type="button" onClick={() => switchSession(id)}>
              {id.slice(-8)}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="new-session" onClick={startNewSession}>
        + New Session
      </button>
    </div>
  );
};

export default SessionHistory;
