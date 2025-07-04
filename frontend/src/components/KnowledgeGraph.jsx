import React, { useEffect, useState } from 'react';
import { useSession } from '../context/SessionContext';
import { getKnowledgeGraph } from '../services/api';
import '../styles/KnowledgeGraph.css';

const circleLayout = (nodes, radius, centerX, centerY) => {
  const angleStep = (2 * Math.PI) / nodes.length;
  return nodes.map((node, index) => ({
    ...node,
    x: centerX + radius * Math.cos(angleStep * index),
    y: centerY + radius * Math.sin(angleStep * index),
  }));
};

const KnowledgeGraph = () => {
  const { userId } = useSession();
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadGraph = async () => {
      try {
        const data = await getKnowledgeGraph();
        setGraph(data);
      } catch {
        setError('Failed to load knowledge graph');
      }
    };
    if (userId) loadGraph();
  }, [userId]);

  if (!userId) return <p className="kg-message">Select a user to view the graph.</p>;
  if (error) return <p className="kg-message">{error}</p>;
  if (!graph) return <p className="kg-message">Loading graph...</p>;
  if (!graph.enabled) return <p className="kg-message">Zep memory is disabled.</p>;

  const positioned = circleLayout(graph.nodes, 200, 250, 250);

  return (
    <div className="knowledge-graph">
      <svg width="500" height="500">
        {graph.edges.map((edge, idx) => {
          const source = positioned.find(n => n.uuid_ === edge.source_node_uuid);
          const target = positioned.find(n => n.uuid_ === edge.target_node_uuid);
          if (!source || !target) return null;
          return (
            <line
              key={idx}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="#555"
            />
          );
        })}
        {positioned.map(node => (
          <g key={node.uuid_}>
            <circle cx={node.x} cy={node.y} r="20" fill="#3182ce" />
            <text x={node.x} y={node.y} textAnchor="middle" dy=".3em" fill="white" fontSize="10">
              {node.name || node.uuid_}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
};

export default KnowledgeGraph;
