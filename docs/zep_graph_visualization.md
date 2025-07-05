# Zep Knowledge Graph Visualization Documentation

## Overview

The Zep Knowledge Graph Visualization feature allows users to view their knowledge graph stored in Zep as an interactive D3.js visualization. This document covers the implementation details, usage, and troubleshooting.

## Architecture

### Backend Components

1. **API Endpoints** (`backend/api/graph.py`):
   - `POST /api/graph/fetch` - Fetches graph data (nodes and edges) from Zep
   - `GET /api/graph/test/{user_id}` - Tests graph connectivity for debugging

2. **Data Models**:
   - `GraphNode` - Represents a node in the knowledge graph
   - `GraphEdge` - Represents a relationship between nodes
   - `GraphTriplet` - Combines source node, edge, and target node
   - `GraphResponse` - API response containing triplets and counts

3. **Integration with Zep**:
   - Uses the existing `ZepManager` to access Zep Cloud SDK
   - Implements pagination for large graphs (100 nodes/edges per batch)
   - Handles isolated nodes by creating virtual self-referencing edges

### Frontend Components

1. **Core Visualization** (`frontend/src/components/graph/`):
   - `Graph.jsx` - D3.js force-directed graph implementation
   - `GraphVisualization.jsx` - Main wrapper component
   - `GraphPopovers.jsx` - Node and edge detail popups
   - `KnowledgeGraphViewer.jsx` - User-facing component with modal

2. **Utilities** (`frontend/src/utils/graph/`):
   - `graphUtils.js` - Data transformation functions
   - `nodeColors.js` - Color palette and node coloring logic

3. **Styling** (`frontend/src/styles/Graph.css`):
   - Complete styling for all graph components
   - Dark mode support
   - Responsive design

## Features

### Interactive Graph Visualization
- **Force-directed layout** using D3.js physics simulation
- **Zoom and pan** capabilities with mouse/touch controls
- **Drag nodes** to reposition them
- **Click interactions**:
  - Click nodes to view node details
  - Click edges to view relationship details
  - Click background to reset selection

### Visual Features
- **Color-coded nodes** by entity type
- **Entity types legend** with hover display
- **Curved edges** for multiple relationships
- **Arrowheads** showing relationship direction
- **Edge labels** showing relationship types

### Data Display
- **Node details**: Name, summary, labels, attributes, timestamps
- **Edge details**: Relationship type, facts, episodes, validity periods
- **Graph statistics**: Total nodes and edges count

## Usage

### For End Users

1. Navigate to User Settings in the application
2. Click the "Knowledge Graph" button
3. The graph will load automatically
4. Interact with the graph:
   - Zoom: Mouse wheel or pinch gesture
   - Pan: Click and drag on background
   - Move nodes: Click and drag nodes
   - View details: Click on nodes or edges

### For Developers

#### Adding the Component

```javascript
import KnowledgeGraphViewer from './components/graph/KnowledgeGraphViewer';

// In your component
<KnowledgeGraphViewer 
  userId={userId} 
  userName={displayName}
/>
```

#### Direct Graph Visualization

```javascript
import GraphVisualization from './components/graph/GraphVisualization';

// With your triplet data
<GraphVisualization
  triplets={graphData.triplets}
  width={1000}
  height={800}
  zoomOnMount={true}
/>
```

## Configuration

### Environment Variables

- `ZEP_API_KEY` - Required for Zep Cloud SDK authentication
- `REACT_APP_DEBUG` - Set to 'true' to enable debug features

### Customization Options

1. **Node Colors**: Edit `nodeColorPalette` in `nodeColors.js`
2. **Graph Physics**: Modify force simulation parameters in `Graph.jsx`
3. **Styling**: Update CSS variables in `Graph.css`

## API Reference

### Backend Endpoints

#### POST /api/graph/fetch
Fetches graph data for a user or group.

**Request Body:**
```json
{
  "type": "user",  // or "group"
  "id": "user-id-123"
}
```

**Response:**
```json
{
  "triplets": [...],
  "node_count": 42,
  "edge_count": 38
}
```

#### GET /api/graph/test/{user_id}
Tests if graph data is available for a user.

**Response:**
```json
{
  "status": "success",
  "has_nodes": true,
  "has_edges": true,
  "message": "Graph connectivity test successful"
}
```

## Troubleshooting

### Common Issues

1. **"Zep service is not available"**
   - Ensure `ZEP_API_KEY` is set in environment variables
   - Verify Zep is enabled in configuration

2. **Empty graph (no nodes/edges)**
   - User may not have any stored memories in Zep
   - Check if conversations are being stored to Zep

3. **Performance issues with large graphs**
   - Consider implementing node/edge limits
   - Adjust D3 force simulation parameters

4. **Graph not rendering**
   - Check browser console for errors
   - Ensure D3.js is properly installed (`npm install d3`)

### Debug Mode

Enable debug mode by setting `REACT_APP_DEBUG=true` to access:
- Connectivity test button
- Additional console logging
- Performance metrics

## Performance Considerations

1. **Large Graphs**: 
   - Pagination is implemented (100 items per batch)
   - Consider implementing virtualization for very large graphs

2. **Memory Usage**:
   - D3 simulations can be memory-intensive
   - Cleanup is implemented in useEffect cleanup

3. **Rendering**:
   - SVG rendering can be slow for many elements
   - Consider Canvas rendering for graphs >1000 nodes

## Future Enhancements

1. **Search and Filter**:
   - Search nodes by name or attributes
   - Filter by node types or date ranges

2. **Graph Analytics**:
   - Centrality measures
   - Clustering visualization
   - Path finding between nodes

3. **Export Features**:
   - Export as image (PNG/SVG)
   - Export graph data as JSON
   - Generate graph reports

4. **Collaboration**:
   - Share graph views
   - Collaborative annotations
   - Graph versioning

## Security Considerations

1. **Access Control**:
   - Users can only view their own graphs
   - Group graphs require group membership (not yet implemented)

2. **API Security**:
   - Zep API key is never exposed to frontend
   - User authentication required for all endpoints

3. **Data Privacy**:
   - No graph data is cached on frontend
   - All data fetched on-demand 