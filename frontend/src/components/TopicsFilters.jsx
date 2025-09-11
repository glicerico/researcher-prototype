import React from 'react';
import '../styles/TopicsFilters.css';

const TopicsFilters = ({ filters, onFiltersChange, topicsCount }) => {
  const handleFilterChange = (key, value) => {
    onFiltersChange(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const clearFilters = () => {
    onFiltersChange(prev => ({
      ...prev,
      searchTerm: '',
      sortBy: 'confidence',
      sortOrder: 'desc',
      autoOnly: false,
    }));
  };

  const hasActiveFilters = filters.searchTerm;

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
            <button 
              className="clear-search"
              onClick={() => handleFilterChange('searchTerm', '')}
              title={filters.searchTerm ? "Clear search" : "No search to clear"}
              aria-label={filters.searchTerm ? "Clear search" : "No search to clear"}
              disabled={!filters.searchTerm}
            >
              ✕
            </button>
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
              aria-label={`Sort ${filters.sortOrder === 'desc' ? 'ascending' : 'descending'}`}
            >
              {filters.sortOrder === 'desc' ? '↓' : '↑'}
            </button>
          </div>
        </div>

        {/* Auto expansions filter */}
        <div className="filter-group auto-group">
          <label htmlFor="auto-only">Auto expansions only</label>
          <div>
            <input
              id="auto-only"
              type="checkbox"
              checked={!!filters.autoOnly}
              onChange={(e) => handleFilterChange('autoOnly', e.target.checked)}
            />
          </div>
        </div>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <div className="filter-group clear-group">
            <button className="clear-filters-btn" onClick={clearFilters}>
              Clear Search
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
