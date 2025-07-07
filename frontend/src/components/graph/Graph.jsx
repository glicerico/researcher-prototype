/**
 * D3.js Graph Visualization Component
 * Converted from TypeScript to JavaScript
 */
import React, {
  useEffect,
  useRef,
  useMemo,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";
import * as d3 from "d3";
import {
  createLabelColorMap,
  getNodeColor as getNodeColorByLabel,
} from "../../utils/graph/nodeColors";

// Define theme colors (matching the app's color scheme)
const colors = {
  pink: { 
    300: '#f9a8d4', 
    400: '#f472b6', 
    500: '#ec4899' 
  },
  blue: { 
    400: '#60a5fa', 
    500: '#3b82f6' 
  },
  slate: {
    100: '#f1f5f9',
    200: '#e2e8f0',
    400: '#94a3b8',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a'
  }
};

// eslint-disable-next-line react/display-name
const Graph = forwardRef(
  (
    {
      triplets,
      width = 1000,
      height = 800,
      zoomOnMount = true,
      onNodeClick,
      onEdgeClick,
      onBlur,
      labelColorMap: externalLabelColorMap,
    },
    ref
  ) => {
    const svgRef = useRef(null);
    
    // Detect theme mode from CSS variable or body class
    const themeMode = useMemo(() => {
      const bodyClasses = document.body.classList;
      return bodyClasses.contains('dark') ? 'dark' : 'light';
    }, []);

    // Function refs to keep track of reset functions
    const resetLinksRef = useRef(null);
    const resetNodesRef = useRef(null);
    const handleLinkClickRef = useRef(null);
    const simulationRef = useRef(null);
    const zoomRef = useRef(null);
    const isInitializedRef = useRef(false);

    // Add ref for zoomToLinkById
    const graphRef = useRef({
      zoomToLinkById: (linkId) => {
        if (
          !svgRef.current ||
          !resetLinksRef.current ||
          !resetNodesRef.current ||
          !handleLinkClickRef.current
        )
          return;
        const svgElement = d3.select(svgRef.current);
        const linkGroups = svgElement.selectAll("g > g"); // Select all link groups

        let found = false;

        // Iterate through link groups to find matching relation
        linkGroups.each(function (d) {
          if (found) return; // Skip if already found

          if (d?.relationData) {
            const relation = d.relationData.find(
              (r) => r.id === linkId
            );
            if (relation) {
              found = true;
              const resetLinks = resetLinksRef.current;
              const resetNodes = resetNodesRef.current;
              const handleLinkClick = handleLinkClickRef.current;

              if (resetLinks) resetLinks();
              if (resetNodes) resetNodes();
              if (handleLinkClick)
                handleLinkClick({ stopPropagation: () => {} }, d, relation);
            }
          }
        });

        if (!found) {
          console.warn(`Link with id ${linkId} not found`);
        }
      },
    });

    // Expose the ref through forwardRef
    useImperativeHandle(ref, () => graphRef.current);

    // Memoize theme to prevent unnecessary recreation
    const theme = useMemo(
      () => ({
        node: {
          fill: colors.pink[500],
          stroke: themeMode === "dark" ? colors.slate[100] : colors.slate[900],
          hover: colors.blue[400],
          text: themeMode === "dark" ? colors.slate[100] : colors.slate[900],
          selected: colors.blue[500],
          dimmed: colors.pink[300],
        },
        link: {
          stroke: themeMode === "dark" ? colors.slate[600] : colors.slate[400],
          selected: colors.blue[400],
          dimmed: themeMode === "dark" ? colors.slate[800] : colors.slate[200],
          label: {
            bg: themeMode === "dark" ? colors.slate[800] : colors.slate[200],
            text: themeMode === "dark" ? colors.slate[100] : colors.slate[900],
          },
        },
        background:
          themeMode === "dark" ? colors.slate[900] : colors.slate[100],
        controls: {
          bg: themeMode === "dark" ? colors.slate[800] : colors.slate[200],
          hover: themeMode === "dark" ? colors.slate[700] : colors.slate[300],
          text: themeMode === "dark" ? colors.slate[100] : colors.slate[900],
        },
      }),
      [themeMode]
    );

    // Extract all unique labels from triplets
    const allLabels = useMemo(() => {
      // Only calculate if we need to create our own map
      if (externalLabelColorMap) return [];

      const labels = new Set();
      labels.add("Entity"); // Always include Entity as default

      triplets.forEach((triplet) => {
        if (triplet.source.primaryLabel)
          labels.add(triplet.source.primaryLabel);
        if (triplet.target.primaryLabel)
          labels.add(triplet.target.primaryLabel);
      });

      return Array.from(labels);
    }, [triplets, externalLabelColorMap]);

    // Create a mapping of label to color
    const labelColorMap = useMemo(() => {
      return externalLabelColorMap || createLabelColorMap(allLabels);
    }, [allLabels, externalLabelColorMap]);

    // Create a mapping of node IDs to their data
    const nodeDataMap = useMemo(() => {
      const result = new Map();

      triplets.forEach((triplet) => {
        result.set(triplet.source.id, triplet.source);
        result.set(triplet.target.id, triplet.target);
      });

      return result;
    }, [triplets]);

    // Function to get node color
    const getNodeColor = useCallback(
      (node) => {
        if (!node) {
          return getNodeColorByLabel(null, themeMode === "dark", labelColorMap);
        }

        // Get the full node data if we only have an ID
        const nodeData = nodeDataMap.get(node.id) || node;

        // Extract primaryLabel from node data
        const primaryLabel = nodeData.primaryLabel;

        return getNodeColorByLabel(
          primaryLabel,
          themeMode === "dark",
          labelColorMap
        );
      },
      [labelColorMap, nodeDataMap, themeMode]
    );

    // Process graph data
    const { nodes, links } = useMemo(() => {
      const nodes = Array.from(
        new Set(triplets.flatMap((t) => [t.source.id, t.target.id]))
      ).map((id) => {
        const nodeData = triplets.find(
          (t) => t.source.id === id || t.target.id === id
        );
        const value = nodeData
          ? nodeData.source.id === id
            ? nodeData.source.value
            : nodeData.target.value
          : id;
        return {
          id,
          value,
        };
      });

      const linkGroups = triplets.reduce(
        (groups, triplet) => {
          // Skip isolated node edges (they are just placeholders for showing isolated nodes)
          if (triplet.relation.type === "_isolated_node_") {
            return groups;
          }

          let key = `${triplet.source.id}-${triplet.target.id}`;
          const reverseKey = `${triplet.target.id}-${triplet.source.id}`;

          if (groups[reverseKey]) {
            key = reverseKey;
          }

          if (!groups[key]) {
            groups[key] = {
              source: triplet.source.id,
              target: triplet.target.id,
              relations: [],
              relationData: [],
              curveStrength: 0,
            };
          }
          groups[key].relations.push(triplet.relation.value);
          groups[key].relationData.push(triplet.relation);
          return groups;
        },
        {}
      );

      return {
        nodes,
        links: Object.values(linkGroups),
      };
    }, [triplets]);

    // Initialize or update visualization - This will run only once on mount
    useEffect(() => {
      // Skip if already initialized or ref not available
      if (isInitializedRef.current || !svgRef.current) return;

      // Mark as initialized to prevent re-running
      isInitializedRef.current = true;

      const svgElement = d3.select(svgRef.current);
      svgElement.selectAll("*").remove();

      const g = svgElement.append("g");

      // Drag handler function
      const drag = (simulation) => {
        const originalSettings = {
          velocityDecay: 0.4,
          alphaDecay: 0.05,
        };

        function dragstarted(event) {
          if (!event.active) {
            simulation
              .velocityDecay(0.7)
              .alphaDecay(0.1)
              .alphaTarget(0.1)
              .restart();
          }
          d3.select(event.sourceEvent.target.parentNode)
            .select("circle")
            .attr("stroke", theme.node.hover)
            .attr("stroke-width", 3);

          event.subject.fx = event.subject.x;
          event.subject.fy = event.subject.y;
        }

        function dragged(event) {
          event.subject.x = event.x;
          event.subject.y = event.y;
          event.subject.fx = event.x;
          event.subject.fy = event.y;
        }

        function dragended(event) {
          if (!event.active) {
            simulation
              .velocityDecay(originalSettings.velocityDecay)
              .alphaDecay(originalSettings.alphaDecay)
              .alphaTarget(0);
          }

          // Keep the node fixed at its final position
          event.subject.fx = event.x;
          event.subject.fy = event.y;

          d3.select(event.sourceEvent.target.parentNode)
            .select("circle")
            .attr("stroke", theme.node.stroke)
            .attr("stroke-width", 2);
        }

        return d3
          .drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended);
      };

      // Setup zoom behavior
      const zoom = d3
        .zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        });

      zoomRef.current = zoom;
      svgElement.call(zoom).call(zoom.transform, d3.zoomIdentity.scale(0.8));

      // Identify which nodes are isolated (not in any links)
      const nodeIdSet = new Set(nodes.map((n) => n.id));
      const linkedNodeIds = new Set();

      links.forEach((link) => {
        const sourceId =
          typeof link.source === "string" ? link.source : link.source.id;
        const targetId =
          typeof link.target === "string" ? link.target : link.target.id;
        linkedNodeIds.add(sourceId);
        linkedNodeIds.add(targetId);
      });

      // Nodes that don't appear in any link are isolated
      const isolatedNodeIds = new Set();
      nodeIdSet.forEach((nodeId) => {
        if (!linkedNodeIds.has(nodeId)) {
          isolatedNodeIds.add(nodeId);
        }
      });

      // Create simulation with custom forces
      const simulation = d3
        .forceSimulation(nodes)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d) => d.id)
            .distance(200)
            .strength(0.2)
        )
        .force(
          "charge",
          d3
            .forceManyBody()
            .strength((d) => {
              // Use a less negative strength for isolated nodes
              // to pull them closer to the center
              return isolatedNodeIds.has(d.id) ? -500 : -3000;
            })
            .distanceMin(20)
            .distanceMax(500)
            .theta(0.8)
        )
        .force("center", d3.forceCenter(width / 2, height / 2).strength(0.05))
        .force(
          "collide",
          d3.forceCollide().radius(50).strength(0.3).iterations(5)
        )
        // Add a special gravity force for isolated nodes to pull them toward the center
        .force(
          "isolatedGravity",
          d3
            .forceRadial(
              100, // distance from center
              width / 2, // center x
              height / 2 // center y
            )
            .strength((d) => (isolatedNodeIds.has(d.id) ? 0.15 : 0.01))
        )
        .velocityDecay(0.4)
        .alphaDecay(0.05)
        .alphaMin(0.001);

      simulationRef.current = simulation;

      const link = g.append("g").selectAll("g").data(links).join("g");

      // Define reset functions
      resetLinksRef.current = () => {
        link
          .selectAll("path")
          .attr("stroke", theme.link.stroke)
          .attr("stroke-opacity", 0.6)
          .attr("stroke-width", 1);

        link.selectAll(".link-label rect").attr("fill", theme.link.label.bg);
        link.selectAll(".link-label text").attr("fill", theme.link.label.text);
      };

      // Create node groups
      const node = g
        .append("g")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .call(drag(simulation))
        .attr("cursor", "pointer");

      resetNodesRef.current = () => {
        node
          .selectAll("circle")
          .attr("fill", (d) => getNodeColor(d))
          .attr("stroke", theme.node.stroke)
          .attr("stroke-width", 1);
      };

      // Handle link click
      handleLinkClickRef.current = (event, d, relation) => {
        if (event.stopPropagation) {
          event.stopPropagation();
        }

        if (resetLinksRef.current) resetLinksRef.current();
        if (onEdgeClick) onEdgeClick(relation.id);

        // Reset all elements to default state
        link
          .selectAll("path")
          .attr("stroke", theme.link.stroke)
          .attr("stroke-opacity", 0.6)
          .attr("stroke-width", 1);

        // Reset non-highlighted nodes to their proper colors
        node
          .selectAll("circle")
          .attr("fill", (d) => getNodeColor(d))
          .attr("stroke", theme.node.stroke)
          .attr("stroke-width", 1);

        // Find and highlight the corresponding path and label
        const linkGroup = event.target?.closest("g")
          ? d3.select(event.target.closest("g"))
          : link.filter((l) => l === d);

        linkGroup
          .selectAll("path")
          .attr("stroke", theme.link.selected)
          .attr("stroke-opacity", 1)
          .attr("stroke-width", 2);

        // Update label styling
        linkGroup.select(".link-label rect").attr("fill", theme.link.selected);
        linkGroup.select(".link-label text").attr("fill", theme.node.text);

        // Highlight connected nodes
        node
          .selectAll("circle")
          .attr("fill", (n) => {
            const sourceId =
              typeof d.source === "string" ? d.source : d.source.id;
            const targetId =
              typeof d.target === "string" ? d.target : d.target.id;
            return n.id === sourceId || n.id === targetId
              ? theme.node.selected
              : getNodeColor(n);
          })
          .attr("stroke-width", (n) => {
            const sourceId =
              typeof d.source === "string" ? d.source : d.source.id;
            const targetId =
              typeof d.target === "string" ? d.target : d.target.id;
            return n.id === sourceId || n.id === targetId ? 2 : 1;
          });
      };

      // Variable to track click timing for proper single/double click handling
      let clickTimeout = null;

      // Function to highlight node and its connections
      function highlightNode(d) {
        if (resetLinksRef.current) resetLinksRef.current();
        if (resetNodesRef.current) resetNodesRef.current();

        // Highlight clicked node
        node
          .selectAll("circle")
          .attr("fill", (n) => {
            if (n.id === d.id) return theme.node.selected;
            return getNodeColor(n);
          })
          .attr("stroke", (n) => {
            if (n.id === d.id) return theme.node.selected;
            return theme.node.stroke;
          })
          .attr("stroke-width", (n) => {
            if (n.id === d.id) return 3;
            return 1;
          });

        // Highlight connected links
        link
          .selectAll("path")
          .attr("stroke", (l) => {
            const sourceId =
              typeof l.source === "string" ? l.source : l.source.id;
            const targetId =
              typeof l.target === "string" ? l.target : l.target.id;
            return sourceId === d.id || targetId === d.id
              ? theme.link.selected
              : theme.link.dimmed;
          })
          .attr("stroke-opacity", (l) => {
            const sourceId =
              typeof l.source === "string" ? l.source : l.source.id;
            const targetId =
              typeof l.target === "string" ? l.target : l.target.id;
            return sourceId === d.id || targetId === d.id ? 1 : 0.3;
          })
          .attr("stroke-width", (l) => {
            const sourceId =
              typeof l.source === "string" ? l.source : l.source.id;
            const targetId =
              typeof l.target === "string" ? l.target : l.target.id;
            return sourceId === d.id || targetId === d.id ? 2 : 1;
          });

        // Highlight connected nodes
        const connectedNodeIds = new Set();
        links.forEach((l) => {
          const sourceId =
            typeof l.source === "string" ? l.source : l.source.id;
          const targetId =
            typeof l.target === "string" ? l.target : l.target.id;
          if (sourceId === d.id) connectedNodeIds.add(targetId);
          if (targetId === d.id) connectedNodeIds.add(sourceId);
        });

        node
          .selectAll("circle")
          .attr("fill", (n) => {
            if (n.id === d.id) return theme.node.selected;
            if (connectedNodeIds.has(n.id)) return getNodeColor(n);
            return theme.node.dimmed;
          })
          .attr("stroke-width", (n) => {
            if (n.id === d.id) return 3;
            if (connectedNodeIds.has(n.id)) return 2;
            return 1;
          });
      }

      // Function to handle node single click (highlight only)
      function handleNodeSingleClick(event, d) {
        event.stopPropagation();

        // Clear any existing timeout
        if (clickTimeout) {
          clearTimeout(clickTimeout);
        }

        // Set a timeout to handle single click after double-click detection window
        clickTimeout = setTimeout(() => {
          highlightNode(d);
          clickTimeout = null;
        }, 200); // 200ms delay to detect double-click
      }

      // Function to handle node double click (show modal)
      function handleNodeDoubleClick(event, d) {
        event.stopPropagation();
        
        // Clear the single click timeout
        if (clickTimeout) {
          clearTimeout(clickTimeout);
          clickTimeout = null;
        }

        // Highlight the node first
        highlightNode(d);
        
        // Then call the original onNodeClick callback to show the modal
        if (onNodeClick) onNodeClick(d.id);
      }

      // Bind node click handlers
      node.on("click", handleNodeSingleClick);
      node.on("dblclick", handleNodeDoubleClick);

      // Add circles to nodes
      node
        .append("circle")
        .attr("r", 20)
        .attr("fill", (d) => getNodeColor(d))
        .attr("stroke", theme.node.stroke)
        .attr("stroke-width", 2);

      // Add labels to nodes
      node
        .append("text")
        .text((d) => d.value)
        .attr("x", 0)
        .attr("y", 5)
        .attr("text-anchor", "middle")
        .attr("font-size", 12)
        .attr("fill", theme.node.text)
        .attr("pointer-events", "none")
        .attr("user-select", "none");

      // Draw links
      link.each(function (d) {
        const group = d3.select(this);
        const lineGenerator = d3.line().curve(d3.curveBasis);

        d.relations.forEach((_, idx) => {
          const path = group
            .append("path")
            .attr("stroke", theme.link.stroke)
            .attr("stroke-width", 1)
            .attr("stroke-opacity", 0.6)
            .attr("fill", "none")
            .attr("marker-end", "url(#arrowhead)")
            .attr("data-relation-index", idx);

          // Add click handler for path
          path.on("click", (event) => {
            if (handleLinkClickRef.current) {
              handleLinkClickRef.current(event, d, d.relationData[idx]);
            }
          });
        });

        // Create label group
        const labelGroup = group
          .append("g")
          .attr("class", "link-label")
          .attr("cursor", "pointer");

        // Background rect for label
        const rect = labelGroup
          .append("rect")
          .attr("fill", theme.link.label.bg)
          .attr("rx", 4)
          .attr("ry", 4);

        // Text label
        const text = labelGroup
          .append("text")
          .attr("text-anchor", "middle")
          .attr("font-size", 10)
          .attr("fill", theme.link.label.text)
          .attr("pointer-events", "none");

        // Add click handler for label group
        labelGroup.on("click", (event) => {
          if (handleLinkClickRef.current && d.relationData.length > 0) {
            handleLinkClickRef.current(event, d, d.relationData[0]);
          }
        });
      });

      // Add arrowhead marker
      svgElement
        .append("defs")
        .append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "-0 -5 10 10")
        .attr("refX", 30)
        .attr("refY", 0)
        .attr("orient", "auto")
        .attr("markerWidth", 8)
        .attr("markerHeight", 8)
        .append("svg:path")
        .attr("d", "M 0,-5 L 10 ,0 L 0,5")
        .attr("fill", theme.link.stroke)
        .style("stroke", "none");

      // Animation function
      simulation.on("tick", () => {
        // Update link positions
        link.each(function (d) {
          const group = d3.select(this);
          const paths = group.selectAll("path");

          const source = d.source;
          const target = d.target;

          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dr = Math.sqrt(dx * dx + dy * dy);

          paths.each(function (_, idx) {
            const path = d3.select(this);
            const curvature = 0.2 * (idx + 1);

            // Calculate control point for curve
            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2;

            // Perpendicular vector
            const perpX = -dy / dr;
            const perpY = dx / dr;

            // Control point
            const ctrlX = midX + perpX * dr * curvature;
            const ctrlY = midY + perpY * dr * curvature;

            // Create curved path
            const lineData = [
              [source.x, source.y],
              [ctrlX, ctrlY],
              [target.x, target.y],
            ];

            path.attr("d", d3.line().curve(d3.curveBasis)(lineData));
          });

          // Update label position
          const labelGroup = group.select(".link-label");
          const text = labelGroup.select("text");
          const rect = labelGroup.select("rect");

          // Position at midpoint
          const midX = (source.x + target.x) / 2;
          const midY = (source.y + target.y) / 2;

          // Update text
          const labelText = d.relations.length > 1
            ? `${d.relations[0]} (+${d.relations.length - 1})`
            : d.relations[0];

          text.text(labelText);

          // Get text dimensions
          const bbox = text.node().getBBox();
          const padding = 4;

          // Update rect dimensions and position
          rect
            .attr("x", -bbox.width / 2 - padding)
            .attr("y", -bbox.height / 2 - padding / 2)
            .attr("width", bbox.width + padding * 2)
            .attr("height", bbox.height + padding);

          // Position the label group
          labelGroup.attr("transform", `translate(${midX}, ${midY})`);
        });

        // Update node positions
        node.attr("transform", (d) => `translate(${d.x}, ${d.y})`);
      });

      // Zoom to fit on mount
      if (zoomOnMount && nodes.length > 0) {
        setTimeout(() => {
          const bounds = g.node().getBBox();
          const fullWidth = width;
          const fullHeight = height;
          const widthScale = fullWidth / bounds.width;
          const heightScale = fullHeight / bounds.height;
          const scale = 0.8 * Math.min(widthScale, heightScale);
          const translate = [
            fullWidth / 2 - scale * (bounds.x + bounds.width / 2),
            fullHeight / 2 - scale * (bounds.y + bounds.height / 2),
          ];

          svgElement
            .transition()
            .duration(750)
            .call(
              zoom.transform,
              d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
            );
        }, 100);
      }

      // Handle background click to reset
      svgElement.on("click", () => {
        if (resetLinksRef.current) resetLinksRef.current();
        if (resetNodesRef.current) resetNodesRef.current();
        if (onBlur) onBlur();
      });

      // Cleanup function
      return () => {
        if (simulationRef.current) {
          simulationRef.current.stop();
        }
      };
    }, []); // Empty dependency array ensures this runs only once

    return (
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{ background: theme.background }}
      />
    );
  }
);

Graph.displayName = "Graph";

export default Graph;
export { Graph }; 