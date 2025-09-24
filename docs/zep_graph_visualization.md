# Zep Knowledge Graph Visualization Documentation

## Overview

The Zep Knowledge Graph Visualization feature allows users to view their knowledge graph stored in Zep as an interactive D3.js visualization. This document covers the implementation details, usage, and troubleshooting.

## Architecture

### Backend Components

1. **API Endpoints** (`backend/api/graph.py`):
   - `POST /api/graph/fetch` - Fetches graph data (nodes and edges) from Zep
   - Debug connectivity testing available in development mode

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
- **Force-directed layout** using D3.js physics simulation with natural initialization
- **Intelligent zoom and pan** capabilities with user preference tracking
- **Drag nodes** to reposition them (preserves user layout preferences)
- **Smart click interactions**:
  - **Single-click nodes**: Highlight node and connected edges
  - **Double-click nodes**: Open detailed information modal
  - **Single-click edges**: View relationship details
  - **Single-click background**: Reset selection and clear highlights
  - **Double-click background**: Reset zoom to fit entire graph

### Visual Features
- **Color-coded nodes** by entity type
- **Entity types legend** with hover display
- **Curved edges** for multiple relationships
- **Arrowheads** showing relationship direction
- **Edge labels** showing relationship types
- **Full-screen modals** with dark overlay for node/edge details
- **Keyboard shortcuts**: ESC key to close modals
- **Automatic centering** that respects user interactions

### Data Display
- **Node details**: Name, summary, labels, attributes, timestamps
- **Edge details**: Relationship type, facts, episodes, validity periods
- **Graph statistics**: Total nodes and edges count

## Usage

### For End Users

1. Navigate to **📊 Dashboards** in the top navigation
2. Click **🕸️ Knowledge Graph** from the dropdown menu
3. The graph will load automatically with natural layout and auto-centering

#### Graph Interactions

**Navigation:**
- **Zoom**: Mouse wheel or pinch gesture
- **Pan**: Click and drag on background
- **Move nodes**: Click and drag individual nodes
- **Reset view**: Double-click background to auto-fit graph

**Exploration:**
- **Highlight connections**: Single-click any node to see its connections
- **View node details**: Double-click any node to open detailed information modal
- **View relationship details**: Single-click any edge/connection
- **Clear selection**: Single-click on empty background

**Modal Controls:**
- **Close modal**: Press ESC key or click outside the modal
- **Click outside**: Click the dark overlay to close
- **Close button**: Click the X button in the modal header

#### User Experience Features
- **Zoom preference tracking**: Your zoom level is preserved during exploration
- **Natural layout**: Graph automatically arranges itself organically on load
- **Responsive design**: Works on desktop and mobile devices

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

## User Experience Design

### Interaction Design Principles

1. **Progressive Disclosure**: Single-click for quick exploration, double-click for details
2. **Non-destructive Navigation**: User zoom/pan preferences are preserved
3. **Clear Visual Feedback**: Highlighting, dimming, and focus states guide exploration
4. **Keyboard Accessibility**: ESC key consistently closes modals
5. **Intuitive Reset**: Double-click background provides easy way back to overview

### Accessibility Features

- **Keyboard Navigation**: ESC key support for modal dismissal
- **Visual Contrast**: Dark overlay ensures modal content is clearly readable
- **Clear State Indication**: Selected and highlighted states are visually distinct
- **Touch Support**: All interactions work on mobile devices

### Performance Optimizations

- **Intelligent Auto-zoom**: Only triggers when user hasn't manually adjusted view
- **Natural Layout**: Graph self-organizes without artificial positioning
- **Smooth Transitions**: 750ms animations for zoom and layout changes
- **Memory Management**: Proper cleanup of D3 simulations and event listeners

## Configuration

### Environment Variables

- `ZEP_API_KEY` - Required for Zep Cloud SDK authentication  
- `ZEP_ENABLED` - Set to 'true' to enable Zep integration
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
  "triplets": [...]
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

5. **Graph appears clustered/overlapping on load**
   - This should auto-resolve as the simulation runs
   - If persistent, try refreshing the page
   - Check that the natural layout initialization is working

6. **Auto-zoom not working**
   - Verify that user hasn't manually zoomed (this disables auto-zoom)
   - Double-click background to reset zoom behavior
   - Check browser console for zoom calculation errors

7. **Modal not closing with ESC key**
   - Ensure the modal has focus (click on it first)
   - Check that no other elements are capturing keyboard events
   - Try clicking outside the modal as alternative

8. **Node highlighting not working**
   - Ensure you're single-clicking (not double-clicking) nodes
   - Check that simulation has finished initial layout
   - Verify theme colors are properly configured

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

## Recent Enhancements (v2024.1)

✅ **Improved Interaction Model**:
- Single-click for exploration, double-click for details
- ESC key modal dismissal
- Background double-click zoom reset

✅ **Smart Auto-zoom**:
- Respects user zoom preferences
- Natural graph layout initialization
- Preserves exploration state

✅ **Enhanced UX**:
- Full-screen modals with dark overlays
- Smooth transitions and animations
- Touch-friendly mobile support

## Future Enhancements

1. **Search and Filter**:
   - Search nodes by name or attributes
   - Filter by node types or date ranges
   - Saved filter presets

2. **Graph Analytics**:
   - Centrality measures
   - Clustering visualization
   - Path finding between nodes
   - Graph metrics dashboard

3. **Export Features**:
   - Export as image (PNG/SVG)
   - Export graph data as JSON
   - Generate graph reports
   - Shareable graph URLs

4. **Advanced Interactions**:
   - Multi-select nodes with Ctrl/Cmd+click
   - Bookmarkable node positions
   - Minimap for large graphs
   - Timeline view for temporal data

5. **Collaboration**:
   - Share graph views
   - Collaborative annotations
   - Graph versioning
   - Real-time collaborative exploration

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