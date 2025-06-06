import React, { useEffect, useState } from 'react';
import { getMotivationStatus } from '../services/api';
import '../styles/MotivationStats.css';

const MotivationStats = ({ onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await getMotivationStatus();
        setData(response.motivation_system);
      } catch (err) {
        console.error('Error loading motivation status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, []);

  const drives = ['boredom', 'curiosity', 'tiredness', 'satisfaction'];

  return (
    <div className="profile-modal-overlay" onClick={onClose}>
      <div className="profile-modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>Motivation</h3>
        {loading && <p>Loading...</p>}
        {!loading && !data && <p>Error loading status.</p>}
        {!loading && data && (
          <>
            {drives.map((drive) => (
              <div key={drive} className="drive-row">
                <span className="drive-label">
                  {drive.charAt(0).toUpperCase() + drive.slice(1)}
                </span>
                <div className="drive-bar">
                  <div
                    className="drive-fill"
                    style={{ width: `${Math.round(data[drive] * 100)}%` }}
                  ></div>
                </div>
              </div>
            ))}
            <div className="impetus-info">
              Impetus: {data.impetus} / {data.threshold}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MotivationStats;
