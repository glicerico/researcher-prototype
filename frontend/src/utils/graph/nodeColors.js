/**
 * Node color palette and utilities for graph visualization
 * Converted from TypeScript to JavaScript
 */

// Define a color palette for node coloring
// Using standard web colors as we don't have tailwindcss/colors in the frontend
export const nodeColorPalette = {
  light: [
    '#ec4899', // pink-500 - Entity (default)
    '#3b82f6', // blue-500
    '#10b981', // emerald-500
    '#f59e0b', // amber-500
    '#6366f1', // indigo-500
    '#f97316', // orange-500
    '#14b8a6', // teal-500
    '#a855f7', // purple-500
    '#06b6d4', // cyan-500
    '#84cc16', // lime-500
    '#f43f5e', // rose-500
    '#8b5cf6', // violet-500
    '#22c55e', // green-500
    '#ef4444', // red-500
  ],
  dark: [
    '#f472b6', // pink-400 - Entity (default)
    '#60a5fa', // blue-400
    '#34d399', // emerald-400
    '#fbbf24', // amber-400
    '#818cf8', // indigo-400
    '#fb923c', // orange-400
    '#2dd4bf', // teal-400
    '#c084fc', // purple-400
    '#22d3ee', // cyan-400
    '#a3e635', // lime-400
    '#fb7185', // rose-400
    '#a78bfa', // violet-400
    '#4ade80', // green-400
    '#f87171', // red-400
  ],
};

/**
 * Function to create a map of label to color index
 * @param {Array<string>} labels - Array of label strings
 * @returns {Map<string, number>} Map of label to color index
 */
export function createLabelColorMap(labels) {
  // Start with Entity mapped to first color
  const result = new Map();
  result.set("Entity", 0);

  // Sort all non-Entity labels alphabetically for consistent color assignment
  const sortedLabels = labels
    .filter((label) => label !== "Entity")
    .sort((a, b) => a.localeCompare(b));

  // Map each unique label to a color index
  let nextIndex = 1;
  sortedLabels.forEach((label) => {
    if (!result.has(label)) {
      result.set(label, nextIndex % nodeColorPalette.light.length);
      nextIndex++;
    }
  });

  return result;
}

/**
 * Get color for a label directly
 * @param {string|null|undefined} label - The label to get color for
 * @param {boolean} isDarkMode - Whether dark mode is enabled
 * @param {Map<string, number>} labelColorMap - Map of label to color index
 * @returns {string} The color hex value
 */
export function getNodeColor(label, isDarkMode, labelColorMap) {
  if (!label) {
    return isDarkMode ? nodeColorPalette.dark[0] : nodeColorPalette.light[0];
  }

  // If label is "Entity" or not found in the map, return default color
  if (label === "Entity" || !labelColorMap.has(label)) {
    return isDarkMode ? nodeColorPalette.dark[0] : nodeColorPalette.light[0];
  }

  // Get the color index for this label
  const colorIndex = labelColorMap.get(label) || 0;

  // Return the color from the appropriate theme palette
  return isDarkMode
    ? nodeColorPalette.dark[colorIndex]
    : nodeColorPalette.light[colorIndex];
} 