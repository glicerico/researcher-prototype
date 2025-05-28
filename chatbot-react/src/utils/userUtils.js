/**
 * Utility functions for user management
 */

/**
 * Generate a display name from a user ID
 * @param {string} userId - The user ID (could be UUID or friendly format)
 * @param {string} [fallbackPrefix='User'] - Prefix for fallback display names
 * @returns {string} A human-readable display name
 */
export const generateDisplayName = (userId, fallbackPrefix = 'User') => {
  if (!userId) return fallbackPrefix;
  
  // Check if it's a friendly ID format (user-adjective-noun-number)
  if (userId.startsWith('user-') && userId.split('-').length === 4) {
    const parts = userId.split('-');
    const adjective = parts[1];
    const noun = parts[2];
    const number = parts[3];
    
    // Capitalize first letters and create a nice display name
    const capitalizedAdjective = adjective.charAt(0).toUpperCase() + adjective.slice(1);
    const capitalizedNoun = noun.charAt(0).toUpperCase() + noun.slice(1);
    
    return `${capitalizedAdjective} ${capitalizedNoun} ${number}`;
  }
  
  // Fallback for UUID format - use last 6 characters
  if (userId.length >= 6) {
    return `${fallbackPrefix} ${userId.substring(userId.length - 6)}`;
  }
  
  // Ultimate fallback
  return `${fallbackPrefix} ${userId}`;
};

/**
 * Check if a user ID is in the friendly format
 * @param {string} userId - The user ID to check
 * @returns {boolean} True if it's a friendly format
 */
export const isFriendlyUserId = (userId) => {
  return userId && userId.startsWith('user-') && userId.split('-').length === 4;
}; 