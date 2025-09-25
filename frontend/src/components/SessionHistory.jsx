import React from 'react';
import { useSession } from '../context/SessionContext';
import '../styles/SessionHistory.css';

const formatSessionId = (id) => {
  if (!id) return 'New Session';

  const idParts = id.split('-');
  // Fallback for old UUIDs or unexpected formats
  if (idParts.length < 2) {
    return id.slice(-8);
  }

  const timestamp = idParts[idParts.length - 1];
  const [datePart, timePart] = timestamp.split('_');

  if (!datePart || !timePart || datePart.length !== 8 || timePart.length < 6) {
    return id.slice(-8); // Fallback if format is not as expected
  }

  const year = datePart.substring(0, 4);
  const month = datePart.substring(4, 6);
  const day = datePart.substring(6, 8);

  const hours = timePart.substring(0, 2);
  const minutes = timePart.substring(2, 4);
  const seconds = timePart.substring(4, 6);

  return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
};

const SessionHistory = () => {
  const { sessionHistory, sessionId, switchSession, startNewSession, sessionTitles } = useSession();

  return (
    <div className="session-history">
      <h3>Sessions</h3>
      <ul>
        {sessionHistory.map((id) => (
          <li key={id} className={id === sessionId ? 'active' : ''}>
            <button type="button" onClick={() => switchSession(id)}>
              {sessionTitles?.[id] || formatSessionId(id)}
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
