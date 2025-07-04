import React, { useEffect, useState } from 'react';
import { getKnowledgeGraph } from '../services/api';
import '../styles/KnowledgeGraph.css';

const circleLayout = (nodes, radius, cx, cy) => {
  return nodes.map((n, idx) => {
    const angle = (idx / nodes.length) * Math.PI * 2;
    return { ...n, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });
};

const KnowledgeGraphPage = () => {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getKnowledgeGraph();
        setGraph(data);
      } catch (e) {
        console.error(e);
        setError('Failed to load knowledge graph');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return <div className="knowledge-graph">Loading...</div>;
  }
  if (error) {
    return <div className="knowledge-graph error">{error}</div>;
  }
  if (!graph || !graph.nodes?.length) {
    return <div className="knowledge-graph">No data available</div>;
  }

  const positioned = circleLayout(graph.nodes, 200, 250, 250);
  const map = {};
  positioned.forEach(n => { map[n.uuid] = n; });

  return (
    <div className="knowledge-graph">
      <h2>Memory Graph</h2>
      <svg width="500" height="500">
        {graph.edges.map(edge => {
          const s = map[edge.source_node_uuid];
          const t = map[edge.target_node_uuid];
          if (!s || !t) return null;
          return <line key={edge.uuid} x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#888" />;
        })}
        {positioned.map(node => (
          <g key={node.uuid}>
            <circle cx={node.x} cy={node.y} r={20} fill="#4caf50" />
            <text x={node.x} y={node.y} textAnchor="middle" dy="5" fill="#fff" fontSize="10">
              {node.name}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
};

export default KnowledgeGraphPage;
