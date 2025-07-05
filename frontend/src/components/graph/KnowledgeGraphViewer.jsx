/**
 * Knowledge Graph Viewer Component
 * Allows users to view their Zep knowledge graph
 */
import React, { useState, useCallback, useEffect } from 'react';
import GraphVisualization from './GraphVisualization';
import { graphApi } from '../../services/api';
import '../../styles/Graph.css';

const KnowledgeGraphViewer = ({ userId, userName = 'User', onClose }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [graphData, setGraphData] = useState(null);
  
  // If onClose is provided, we're being controlled externally
  const isControlled = !!onClose;

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    if (!userId) {
      setError('No user ID available');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await graphApi.fetchGraphData('user', userId);
      setGraphData(response);
    } catch (err) {
      console.error('Failed to fetch graph data:', err);
      setError(err.response?.data?.detail || 'Failed to load knowledge graph');
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // Open the graph view
  const handleOpen = () => {
    setIsOpen(true);
    if (!graphData) {
      fetchGraphData();
    }
  };

  // Close the graph view
  const handleClose = () => {
    if (isControlled && onClose) {
      onClose();
    } else {
      setIsOpen(false);
    }
  };

  // Retry loading graph data
  const handleRetry = () => {
    fetchGraphData();
  };

  // Test graph connectivity (for debugging)
  const testConnectivity = async () => {
    try {
      const result = await graphApi.testGraphConnectivity(userId);
      console.log('Graph connectivity test:', result);
    } catch (err) {
      console.error('Connectivity test failed:', err);
    }
  };

  // Auto-refresh data when modal is opened or when controlled externally
  useEffect(() => {
    if ((isOpen || isControlled) && !graphData && !isLoading && !error) {
      fetchGraphData();
    }
  }, [isOpen, isControlled, graphData, isLoading, error, fetchGraphData]);

  return (
    <>
      {/* Trigger Button - only show if not controlled externally */}
      {!isControlled && (
        <button
          className="graph-view-trigger-button"
          onClick={handleOpen}
          title="View your knowledge graph"
        >
          <svg 
            width="20" 
            height="20" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="3" />
            <circle cx="4" cy="8" r="2" />
            <circle cx="20" cy="8" r="2" />
            <circle cx="8" cy="20" r="2" />
            <circle cx="16" cy="20" r="2" />
            <line x1="12" y1="12" x2="4" y2="8" />
            <line x1="12" y1="12" x2="20" y2="8" />
            <line x1="12" y1="12" x2="8" y2="20" />
            <line x1="12" y1="12" x2="16" y2="20" />
          </svg>
          Knowledge Graph
        </button>
      )}

      {/* Graph View Modal - show if opened internally OR if controlled externally */}
      {(isOpen || isControlled) && (
        <div className="graph-view-modal">
          <div className="graph-view-header">
            <div className="graph-view-title">
              <h2>Knowledge Graph</h2>
              <span className="graph-view-info">
                {userName} • {graphData ? `${graphData.node_count} nodes, ${graphData.edge_count} edges` : 'Loading...'}
              </span>
            </div>
            <button className="graph-view-close" onClick={handleClose}>
              Close
            </button>
          </div>

          <div className="graph-view-body">
            {isLoading && (
              <div className="graph-loading">
                <div className="graph-spinner" />
                <p>Loading your knowledge graph...</p>
              </div>
            )}

            {error && (
              <div className="graph-error">
                <svg 
                  width="48" 
                  height="48" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <p className="graph-error-message">{error}</p>
                <button className="graph-retry-button" onClick={handleRetry}>
                  Try Again
                </button>
              </div>
            )}

            {!isLoading && !error && graphData && (
              <GraphVisualization
                triplets={graphData.triplets}
                width={window.innerWidth}
                height={window.innerHeight - 80} // Account for header
                zoomOnMount={true}
                className=""
              />
            )}
          </div>
        </div>
      )}

      {/* Hidden debug button */}
      {process.env.REACT_APP_DEBUG === 'true' && (
        <button
          onClick={testConnectivity}
          style={{ display: 'none' }}
          aria-hidden="true"
        >
          Test Connectivity
        </button>
      )}
    </>
  );
};

export default KnowledgeGraphViewer; 