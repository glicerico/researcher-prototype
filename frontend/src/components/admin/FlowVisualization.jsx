import React, { useState, useEffect } from 'react';
import { 
  getFlowSummary, 
  getFlowData, 
  getNodeInfo, 
  generateFlowDiagrams,
  getPromptUsageMap 
} from '../../services/adminApi';

const FlowVisualization = ({ onEditPrompt }) => {
  const [flowSummary, setFlowSummary] = useState(null);
  const [selectedGraph, setSelectedGraph] = useState('main');
  const [flowData, setFlowData] = useState(null);
  const [promptUsage, setPromptUsage] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeInfo, setNodeInfo] = useState(null);
  const [diagrams, setDiagrams] = useState({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  // Helper function to construct full URLs for static assets
  const getStaticUrl = (relativePath) => {
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    return `${baseUrl}${relativePath}`;
  };

  useEffect(() => {
    loadFlowData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedGraph) {
      loadGraphData(selectedGraph);
    }
  }, [selectedGraph]);

  const loadFlowData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load flow summary and prompt usage in parallel
      const [summaryResponse, usageResponse] = await Promise.all([
        getFlowSummary(),
        getPromptUsageMap()
      ]);

      setFlowSummary(summaryResponse.flow_summary);
      setPromptUsage(usageResponse.prompt_usage);

      // Set default diagrams (they should already exist)
      setDiagrams({
        main_chat: {
          url: getStaticUrl('/static/diagrams/main_chat_flow.png'),
          generated: true
        },
        research: {
          url: getStaticUrl('/static/diagrams/research_flow.png'),
          generated: true
        }
      });

      // Try to generate diagrams if they don't exist or need updating
      await generateDiagrams();

    } catch (err) {
      console.error('Error loading flow data:', err);
      setError('Failed to load flow data');
    } finally {
      setLoading(false);
    }
  };

  const loadGraphData = async (graphType) => {
    try {
      const response = await getFlowData(graphType);
      setFlowData(response.flow_data);
    } catch (err) {
      console.error('Error loading graph data:', err);
      setError(`Failed to load ${graphType} graph data`);
    }
  };

  const generateDiagrams = async (forceRegenerate = false) => {
    try {
      setGenerating(true);
      const response = await generateFlowDiagrams(forceRegenerate);
      
      if (response.success) {
        // Convert relative URLs to absolute URLs
        const diagramsWithFullUrls = {};
        Object.entries(response.diagrams).forEach(([key, diagram]) => {
          diagramsWithFullUrls[key] = {
            ...diagram,
            url: getStaticUrl(diagram.url)
          };
        });
        setDiagrams(diagramsWithFullUrls);
        
        // Log whether we used cache or generated new diagrams
        const usedCache = Object.values(response.diagrams).some(d => d.cached);
        if (usedCache) {
          console.log('Using cached flow diagrams');
        } else {
          console.log('Generated new flow diagrams');
        }
      } else {
        console.warn('Diagram generation had errors:', response.errors);
        const diagramsWithFullUrls = {};
        Object.entries(response.diagrams || {}).forEach(([key, diagram]) => {
          diagramsWithFullUrls[key] = {
            ...diagram,
            url: getStaticUrl(diagram.url)
          };
        });
        setDiagrams(diagramsWithFullUrls);
      }
    } catch (err) {
      console.error('Error generating diagrams:', err);
      // Don't set error here as this is not critical
    } finally {
      setGenerating(false);
    }
  };

  const handleNodeClick = async (nodeId) => {
    try {
      setSelectedNode(nodeId);
      const response = await getNodeInfo(nodeId);
      setNodeInfo(response);
    } catch (err) {
      console.error('Error getting node info:', err);
      setError(`Failed to get information for node: ${nodeId}`);
    }
  };

  const handleEditPrompt = (promptName) => {
    if (onEditPrompt && promptName) {
      onEditPrompt(promptName);
    }
  };

  const renderFlowSummary = () => {
    if (!flowSummary) return null;

    return (
      <div className="flow-summary">
        <h3>Flow Overview</h3>
        <div className="summary-grid">
          <div className="summary-card">
            <h4>Main Chat Flow</h4>
            <p>{flowSummary.flows?.main_chat?.node_count || 0} nodes</p>
            <p>{flowSummary.flows?.main_chat?.edge_count || 0} connections</p>
            <p>Type: {flowSummary.flows?.main_chat?.type || 'Unknown'}</p>
          </div>
          <div className="summary-card">
            <h4>Research Flow</h4>
            <p>{flowSummary.flows?.research?.node_count || 0} nodes</p>
            <p>{flowSummary.flows?.research?.edge_count || 0} connections</p>
            <p>Type: {flowSummary.flows?.research?.type || 'Unknown'}</p>
          </div>
          <div className="summary-card">
            <h4>Prompt Usage</h4>
            <p>{flowSummary.total_prompts || 0} active prompts</p>
            <p>{flowSummary.total_nodes || 0} total nodes</p>
          </div>
        </div>
      </div>
    );
  };

  const renderDiagram = () => {
    const diagramKey = selectedGraph === 'main' ? 'main_chat' : selectedGraph;
    const diagramData = diagrams[diagramKey];
    
    if (!diagramData) {
      return (
        <div className="diagram-placeholder">
          <p>Diagram could not be loaded</p>
          <button 
            onClick={() => generateDiagrams(true)}
            disabled={generating}
            className="btn btn-primary"
          >
            {generating ? 'Generating...' : 'Regenerate Diagram'}
          </button>
        </div>
      );
    }

    return (
      <div className="diagram-container">
        <img 
          src={diagramData.url} 
          alt={`${selectedGraph} flow diagram`}
          className="flow-diagram"
          onError={(e) => {
            e.target.style.display = 'none';
            e.target.nextSibling.style.display = 'block';
          }}
        />
        <div className="diagram-error" style={{ display: 'none' }}>
          <p>Diagram could not be loaded</p>
          <button 
            onClick={() => generateDiagrams(true)}
            disabled={generating}
            className="btn btn-primary"
          >
            Regenerate Diagram
          </button>
        </div>
      </div>
    );
  };

  const renderNodeList = () => {
    if (!flowData || !flowData.nodes) return null;

    return (
      <div className="node-list">
        <h4>Flow Nodes</h4>
        <div className="nodes-grid">
          {flowData.nodes.map((node) => (
            <div 
              key={node.id} 
              className={`node-card ${node.category?.toLowerCase()}`}
              onClick={() => handleNodeClick(node.id)}
            >
              <div className="node-header">
                <h5>{node.id}</h5>
                <span className="node-category">{node.category}</span>
              </div>
              <p className="node-description">{node.description}</p>
              {node.prompt && (
                <div className="node-prompt">
                  <strong>Prompt:</strong> {node.prompt}
                </div>
              )}
              {node.prompt && (
                <button 
                  className="btn btn-sm btn-outline-primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEditPrompt(node.prompt);
                  }}
                >
                  Edit Prompt
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderNodeDetails = () => {
    if (!selectedNode || !nodeInfo) return null;

    return (
      <div className="node-details">
        <h4>Node Details: {selectedNode}</h4>
        <div className="node-info">
          <p><strong>Category:</strong> {nodeInfo.node_info?.category}</p>
          <p><strong>Description:</strong> {nodeInfo.node_info?.description}</p>
          
          {nodeInfo.node_info?.prompt && (
            <div className="prompt-info">
              <p><strong>Associated Prompt:</strong> {nodeInfo.node_info.prompt}</p>
              {nodeInfo.prompt_details && (
                <div className="prompt-details">
                  <p><strong>Variables:</strong> {nodeInfo.prompt_details.variables?.join(', ') || 'None'}</p>
                  <button 
                    className="btn btn-primary"
                    onClick={() => handleEditPrompt(nodeInfo.node_info.prompt)}
                  >
                    Edit This Prompt
                  </button>
                </div>
              )}
            </div>
          )}
          
          {!nodeInfo.node_info?.prompt && (
            <p className="no-prompt">This node does not use a prompt</p>
          )}
        </div>
        
        <button 
          className="btn btn-secondary"
          onClick={() => {
            setSelectedNode(null);
            setNodeInfo(null);
          }}
        >
          Close Details
        </button>
      </div>
    );
  };

  const renderPromptUsage = () => {
    if (!promptUsage) return null;

    return (
      <div className="prompt-usage">
        <h4>Prompt Usage Map</h4>
        <div className="usage-list">
          {Object.entries(promptUsage).map(([promptName, nodes]) => (
            <div key={promptName} className="usage-item">
              <div className="usage-header">
                <strong>{promptName}</strong>
                <button 
                  className="btn btn-sm btn-outline-primary"
                  onClick={() => handleEditPrompt(promptName)}
                >
                  Edit
                </button>
              </div>
              <p>Used by: {nodes.join(', ')}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading flow data...</p>
      </div>
    );
  }
  
  return (
    <div className="flow-visualization">
      <div className="flow-header">
        <h2>LangGraph Flow Visualization</h2>
        <p>Understand how prompts intervene in conversation flows</p>
      </div>

      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          {error}
          <button onClick={loadFlowData} className="btn-primary" style={{marginLeft: '1rem'}}>
            Retry
          </button>
        </div>
      )}

      {renderFlowSummary()}
      {renderDiagram()}
      {renderNodeList()}
      {renderNodeDetails()}
      {renderPromptUsage()}
    </div>
  );
};

export default FlowVisualization; 