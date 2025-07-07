/**
 * Graph Popovers Component
 * Handles popups for nodes and edges in the graph
 * Converted to use plain React instead of Radix UI
 */
import React from 'react';
import { getNodeColor } from '../../utils/graph/nodeColors';

/**
 * Simple Modal component to replace Radix UI Dialog
 */
const Modal = ({ isOpen, onClose, children, title }) => {
  // Handle ESC key to close modal
  React.useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    // Add event listener when modal is open
    document.addEventListener('keydown', handleKeyDown);

    // Cleanup event listener when modal closes or component unmounts
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="graph-modal-overlay" onClick={onClose}>
      <div className="graph-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="graph-modal-header">
          <h3>{title}</h3>
          <button className="graph-modal-close" onClick={onClose}>×</button>
        </div>
        <div className="graph-modal-body">
          {children}
        </div>
      </div>
    </div>
  );
};

/**
 * Format a date string for display
 */
const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
};

/**
 * Node Details Component
 */
const NodeDetails = ({ node, labelColorMap }) => {
  const isDarkMode = document.body.classList.contains('dark');
  const primaryLabel = node.primaryLabel || (node.labels && node.labels[0]) || 'Entity';
  const nodeColor = getNodeColor(primaryLabel, isDarkMode, labelColorMap);

  return (
    <div className="graph-node-details">
      <div className="graph-detail-header">
        <div 
          className="graph-color-indicator"
          style={{ backgroundColor: nodeColor }}
        />
        <h4>{node.name}</h4>
      </div>

      {node.summary && (
        <div className="graph-detail-section">
          <strong>Summary:</strong>
          <p>{node.summary}</p>
        </div>
      )}

      {node.labels && node.labels.length > 0 && (
        <div className="graph-detail-section">
          <strong>Labels:</strong>
          <div className="graph-labels">
            {node.labels.map((label, idx) => (
              <span key={idx} className="graph-label-tag">{label}</span>
            ))}
          </div>
        </div>
      )}

      {node.attributes && Object.keys(node.attributes).length > 0 && (
        <div className="graph-detail-section">
          <strong>Attributes:</strong>
          <div className="graph-attributes">
            {Object.entries(node.attributes).map(([key, value]) => (
              <div key={key} className="graph-attribute">
                <span className="graph-attribute-key">{key}:</span>
                <span className="graph-attribute-value">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="graph-detail-section graph-timestamps">
        <div>
          <strong>Created:</strong> {formatDate(node.created_at)}
        </div>
        <div>
          <strong>Updated:</strong> {formatDate(node.updated_at)}
        </div>
      </div>
    </div>
  );
};

/**
 * Edge Details Component
 */
const EdgeDetails = ({ source, target, relation, labelColorMap }) => {
  const isDarkMode = document.body.classList.contains('dark');
  const sourcePrimaryLabel = source.primaryLabel || (source.labels && source.labels[0]) || 'Entity';
  const targetPrimaryLabel = target.primaryLabel || (target.labels && target.labels[0]) || 'Entity';
  const sourceColor = getNodeColor(sourcePrimaryLabel, isDarkMode, labelColorMap);
  const targetColor = getNodeColor(targetPrimaryLabel, isDarkMode, labelColorMap);

  return (
    <div className="graph-edge-details">
      <div className="graph-edge-nodes">
        <div className="graph-edge-node">
          <div 
            className="graph-color-indicator"
            style={{ backgroundColor: sourceColor }}
          />
          <span>{source.name}</span>
        </div>
        <div className="graph-edge-arrow">→</div>
        <div className="graph-edge-node">
          <div 
            className="graph-color-indicator"
            style={{ backgroundColor: targetColor }}
          />
          <span>{target.name}</span>
        </div>
      </div>

      <div className="graph-detail-section">
        <strong>Relation Type:</strong> {relation.type}
      </div>

      {relation.fact && (
        <div className="graph-detail-section">
          <strong>Fact:</strong>
          <p>{relation.fact}</p>
        </div>
      )}

      {relation.episodes && relation.episodes.length > 0 && (
        <div className="graph-detail-section">
          <strong>Episodes:</strong>
          <ul className="graph-episodes">
            {relation.episodes.map((episode, idx) => (
              <li key={idx}>{episode}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="graph-detail-section graph-timestamps">
        <div>
          <strong>Created:</strong> {formatDate(relation.created_at)}
        </div>
        <div>
          <strong>Updated:</strong> {formatDate(relation.updated_at)}
        </div>
        {relation.valid_at && (
          <div>
            <strong>Valid At:</strong> {formatDate(relation.valid_at)}
          </div>
        )}
        {relation.expired_at && (
          <div>
            <strong>Expired At:</strong> {formatDate(relation.expired_at)}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Main GraphPopovers Component
 */
export const GraphPopovers = ({
  showNodePopup,
  showEdgePopup,
  nodePopupContent,
  edgePopupContent,
  onOpenChange,
  labelColorMap
}) => {
  return (
    <>
      {/* Node Popup */}
      <Modal
        isOpen={showNodePopup}
        onClose={() => onOpenChange(false)}
        title="Node Details"
      >
        {nodePopupContent && (
          <NodeDetails 
            node={nodePopupContent.node} 
            labelColorMap={labelColorMap}
          />
        )}
      </Modal>

      {/* Edge Popup */}
      <Modal
        isOpen={showEdgePopup}
        onClose={() => onOpenChange(false)}
        title="Edge Details"
      >
        {edgePopupContent && (
          <EdgeDetails
            source={edgePopupContent.source}
            target={edgePopupContent.target}
            relation={edgePopupContent.relation}
            labelColorMap={labelColorMap}
          />
        )}
      </Modal>
    </>
  );
};

export default GraphPopovers; 