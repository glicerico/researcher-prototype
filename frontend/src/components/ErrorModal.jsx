import React from 'react';
import '../styles/ErrorModal.css';

const ErrorModal = ({ isOpen, message, onClose }) => {
  if (!isOpen || !message) return null;

  return (
    <div className="error-modal-overlay" onClick={onClose}>
      <div className="error-modal" onClick={(e) => e.stopPropagation()}>
        <div className="error-modal-header">
          <div className="error-icon">⚠️</div>
          <h3>Unable to Activate Topic</h3>
          <button 
            className="error-modal-close" 
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="error-modal-body">
          <p>{message}</p>
        </div>
        <div className="error-modal-footer">
          <button className="error-modal-dismiss" onClick={onClose}>
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorModal;
