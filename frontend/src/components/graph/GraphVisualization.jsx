/**
 * Graph Visualization Component
 * Main wrapper that manages the graph state and interactions
 */
import React, { useState, useMemo, forwardRef, useImperativeHandle } from "react";
import Graph from "./Graph";
import GraphPopovers from "./GraphPopovers";
import { toGraphTriplets } from "../../utils/graph/graphUtils";
import { createLabelColorMap, getNodeColor } from "../../utils/graph/nodeColors";

// Entity Types Legend Component
const EntityTypesLegend = ({ allLabels, sharedLabelColorMap }) => {
  const [showLegend, setShowLegend] = useState(false);
  const isDarkMode = document.body.classList.contains('dark');

  return (
    <div className="graph-legend-container">
      <button
        className="graph-legend-button"
        onMouseEnter={() => setShowLegend(true)}
        onMouseLeave={() => setShowLegend(false)}
      >
        Entity Types
      </button>
      
      {showLegend && (
        <div className="graph-legend-dropdown">
          <div className="graph-legend-content">
            {allLabels.map((label) => (
              <div key={label} className="graph-legend-item">
                <div
                  className="graph-legend-color"
                  style={{
                    backgroundColor: getNodeColor(
                      label,
                      isDarkMode,
                      sharedLabelColorMap
                    ),
                  }}
                />
                <span className="graph-legend-label">{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// eslint-disable-next-line react/display-name
export const GraphVisualization = forwardRef(
  (
    {
      triplets,
      width = window.innerWidth * 0.85,
      height = window.innerHeight * 0.85,
      zoomOnMount = true,
      className = "graph-visualization-container",
    },
    ref
  ) => {
    // Graph state for popovers
    const [showNodePopup, setShowNodePopup] = useState(false);
    const [showEdgePopup, setShowEdgePopup] = useState(false);
    const [nodePopupContent, setNodePopupContent] = useState(null);
    const [edgePopupContent, setEdgePopupContent] = useState(null);

    // Create a ref to forward to the Graph component
    const graphRef = React.useRef(null);

    // Forward the ref
    useImperativeHandle(ref, () => graphRef.current);

    // Convert raw triplets to graph triplets
    const graphTriplets = useMemo(() => toGraphTriplets(triplets), [triplets]);

    // Extract all unique labels from triplets
    const allLabels = useMemo(() => {
      const labels = new Set();
      labels.add("Entity"); // Always include Entity as default

      graphTriplets.forEach((triplet) => {
        if (triplet.source.primaryLabel)
          labels.add(triplet.source.primaryLabel);
        if (triplet.target.primaryLabel)
          labels.add(triplet.target.primaryLabel);
      });

      return Array.from(labels).sort((a, b) => {
        // Always put "Entity" first
        if (a === "Entity") return -1;
        if (b === "Entity") return 1;
        // Sort others alphabetically
        return a.localeCompare(b);
      });
    }, [graphTriplets]);

    // Create a shared label color map
    const sharedLabelColorMap = useMemo(() => {
      return createLabelColorMap(allLabels);
    }, [allLabels]);

    // Handle node click
    const handleNodeClick = (nodeId) => {
      // Find the triplet that contains this node
      const triplet = triplets.find(
        (t) => t.sourceNode.uuid === nodeId || t.targetNode.uuid === nodeId
      );

      if (!triplet) return;

      // Determine which node was clicked (source or target)
      const node =
        triplet.sourceNode.uuid === nodeId
          ? triplet.sourceNode
          : triplet.targetNode;

      // Set popup content and show the popup
      setNodePopupContent({
        id: nodeId,
        node: node,
      });
      setShowNodePopup(true);
      setShowEdgePopup(false);
    };

    // Handle edge click
    const handleEdgeClick = (edgeId) => {
      // Find the triplet that contains this edge
      const triplet = triplets.find((t) => t.edge.uuid === edgeId);

      if (!triplet) return;

      // Set popup content and show the popup
      setEdgePopupContent({
        id: edgeId,
        source: triplet.sourceNode,
        target: triplet.targetNode,
        relation: triplet.edge,
      });
      setShowEdgePopup(true);
      setShowNodePopup(false);
    };

    // Handle popover close
    const handlePopoverClose = () => {
      setShowNodePopup(false);
      setShowEdgePopup(false);
    };

    return (
      <div className={className}>
        {/* Entity Types Legend Button */}
        <EntityTypesLegend 
          allLabels={allLabels} 
          sharedLabelColorMap={sharedLabelColorMap} 
        />

        {triplets.length > 0 ? (
          <Graph
            ref={graphRef}
            triplets={graphTriplets}
            width={width}
            height={height}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            onBlur={handlePopoverClose}
            zoomOnMount={zoomOnMount}
            labelColorMap={sharedLabelColorMap}
          />
        ) : (
          <div className="graph-empty-state">
            <p>No graph data to visualize.</p>
          </div>
        )}
        
        <GraphPopovers
          showNodePopup={showNodePopup}
          showEdgePopup={showEdgePopup}
          nodePopupContent={nodePopupContent}
          edgePopupContent={edgePopupContent}
          onOpenChange={handlePopoverClose}
          labelColorMap={sharedLabelColorMap}
        />
      </div>
    );
  }
);

GraphVisualization.displayName = "GraphVisualization";

export default GraphVisualization; 