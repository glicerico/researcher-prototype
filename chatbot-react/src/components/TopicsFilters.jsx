import React from 'react';
import '../styles/TopicsFilters.css';

const TopicsFilters = ({ filters, onFiltersChange, topicsCount }) => {
  const handleFilterChange = (key, value) => {
    onFiltersChange(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleConfidenceChange = (type, value) => {
    const numValue = parseFloat(value);
    if (type === 'min') {
      onFiltersChange(prev => ({
        ...prev,
        minConfidence: numValue,
        maxConfidence: Math.max(numValue, prev.maxConfidence)
      }));
    } else {
      onFiltersChange(prev => ({
        ...prev,
        maxConfidence: numValue,
        minConfidence: Math.min(numValue, prev.minConfidence)
      }));
    }
  };

  const clearFilters = () => {
    onFiltersChange({
      searchTerm: '',
      minConfidence: 0,
      maxConfidence: 1,
      sortBy: 'confidence',
      sortOrder: 'desc'
    });
  };

  const hasActiveFilters = filters.searchTerm || 
                          filters.minConfidence > 0 || 
                          filters.maxConfidence < 1;

  return (
    <div className="topics-filters">
      <div className="filters-row">
        {/* Search */}
        <div className="filter-group search-group">
          <label htmlFor="search">Search Topics</label>
          <div className="search-input-wrapper">
            <input
              id="search"
              type="text"
              placeholder="Search by name or description..."
              value={filters.searchTerm}
              onChange={(e) => handleFilterChange('searchTerm', e.target.value)}
              className="search-input"
            />
            {filters.searchTerm && (
              <button 
                className="clear-search"
                onClick={() => handleFilterChange('searchTerm', '')}
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Confidence Range */}
        <div className="filter-group confidence-group">
          <label>Confidence Range</label>
          <div className="confidence-inputs">
            <div className="confidence-input">
              <label htmlFor="min-confidence">Min</label>
              <input
                id="min-confidence"
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={filters.minConfidence}
                onChange={(e) => handleConfidenceChange('min', e.target.value)}
              />
            </div>
            <span className="confidence-separator">to</span>
            <div className="confidence-input">
              <label htmlFor="max-confidence">Max</label>
              <input
                id="max-confidence"
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={filters.maxConfidence}
                onChange={(e) => handleConfidenceChange('max', e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Sort Controls */}
        <div className="filter-group sort-group">
          <label htmlFor="sort-by">Sort By</label>
          <div className="sort-controls">
            <select
              id="sort-by"
              value={filters.sortBy}
              onChange={(e) => handleFilterChange('sortBy', e.target.value)}
            >
              <option value="confidence">Confidence</option>
              <option value="date">Date</option>
              <option value="name">Name</option>
            </select>
            <button
              className={`sort-order-btn ${filters.sortOrder === 'desc' ? 'desc' : 'asc'}`}
              onClick={() => handleFilterChange('sortOrder', filters.sortOrder === 'desc' ? 'asc' : 'desc')}
              title={`Sort ${filters.sortOrder === 'desc' ? 'ascending' : 'descending'}`}
            >
              {filters.sortOrder === 'desc' ? '↓' : '↑'}
            </button>
          </div>
        </div>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <div className="filter-group clear-group">
            <button className="clear-filters-btn" onClick={clearFilters}>
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* Results Summary */}
      <div className="results-summary">
        <span className="results-count">
          {topicsCount} topic{topicsCount !== 1 ? 's' : ''} found
        </span>
        {hasActiveFilters && (
          <span className="filter-indicator">
            (filtered)
          </span>
        )}
      </div>
    </div>
  );
};

export default TopicsFilters; 