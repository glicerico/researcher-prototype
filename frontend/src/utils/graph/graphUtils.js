/**
 * Graph utility functions for Zep Knowledge Graph visualization
 * Converted from TypeScript to JavaScript
 */

/**
 * Convert a node to graph node format
 * @param {Object} node - The node object
 * @returns {Object} Graph node
 */
export function toGraphNode(node) {
  const primaryLabel = node.labels?.find((label) => label !== "Entity") || "Entity";

  return {
    id: node.uuid,
    value: node.name,
    uuid: node.uuid,
    name: node.name,
    created_at: node.created_at,
    updated_at: node.updated_at,
    attributes: node.attributes,
    summary: node.summary,
    labels: node.labels,
    primaryLabel,
  };
}

/**
 * Convert an edge to graph edge format
 * @param {Object} edge - The edge object
 * @returns {Object} Graph edge
 */
export function toGraphEdge(edge) {
  return {
    id: edge.uuid,
    value: edge.name,
    ...edge,
  };
}

/**
 * Convert a triplet to graph triplet format
 * @param {Object} triplet - The triplet object
 * @returns {Object} Graph triplet
 */
export function toGraphTriplet(triplet) {
  return {
    source: toGraphNode(triplet.sourceNode),
    relation: toGraphEdge(triplet.edge),
    target: toGraphNode(triplet.targetNode),
  };
}

/**
 * Convert array of triplets to graph triplets
 * @param {Array} triplets - Array of triplet objects
 * @returns {Array} Array of graph triplets
 */
export function toGraphTriplets(triplets) {
  return triplets.map(toGraphTriplet);
}

/**
 * Create triplets from edges and nodes
 * @param {Array} edges - Array of edge objects
 * @param {Array} nodes - Array of node objects
 * @returns {Array} Array of raw triplets
 */
export function createTriplets(edges, nodes) {
  // Create a Set of node UUIDs that are connected by edges
  const connectedNodeIds = new Set();
  
  // Create triplets from edges
  const edgeTriplets = edges
    .map((edge) => {
      const sourceNode = nodes.find(
        (node) => node.uuid === edge.source_node_uuid
      );
      const targetNode = nodes.find(
        (node) => node.uuid === edge.target_node_uuid
      );

      if (!sourceNode || !targetNode) return null;

      // Add source and target node IDs to connected set
      connectedNodeIds.add(sourceNode.uuid);
      connectedNodeIds.add(targetNode.uuid);

      return {
        sourceNode,
        edge,
        targetNode,
      };
    })
    .filter(
      (t) => t !== null && t.sourceNode !== undefined && t.targetNode !== undefined
    );
  
  // Find isolated nodes (nodes that don't appear in any edge)
  const isolatedNodes = nodes.filter(node => !connectedNodeIds.has(node.uuid));
  
  // For isolated nodes, create special triplets
  const isolatedTriplets = isolatedNodes.map(node => {
    // Create a special marker edge for isolated nodes
    const virtualEdge = {
      uuid: `isolated-node-${node.uuid}`,
      source_node_uuid: node.uuid,
      target_node_uuid: node.uuid,
      // Use a special type that we can filter out in the Graph component
      type: "_isolated_node_",
      name: "", // Empty name so it doesn't show a label
      created_at: node.created_at,
      updated_at: node.updated_at
    };
    
    return {
      sourceNode: node,
      edge: virtualEdge,
      targetNode: node
    };
  });
  
  // Combine edge triplets with isolated node triplets
  return [...edgeTriplets, ...isolatedTriplets];
} 