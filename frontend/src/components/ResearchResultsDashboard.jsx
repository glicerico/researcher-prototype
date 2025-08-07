import React, { useState, useEffect, useCallback, useMemo, useRef, useLayoutEffect } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useSession } from '../context/SessionContext';
import { useNotifications } from '../context/NotificationContext';
import { 
  getResearchFindings,
  markFindingAsRead,
  deleteResearchFinding,
  deleteAllTopicFindings
} from '../services/api';
import '../styles/ResearchResultsDashboard.css';

const ResearchResultsDashboard = () => {
  const { userId } = useSession();
  const { markResearchNotificationsRead } = useNotifications();
  const [researchData, setResearchData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isBackgroundRefreshing, setIsBackgroundRefreshing] = useState(false);
  const [expandedTopics, setExpandedTopics] = useState(new Set());
  const [bookmarkedFindings, setBookmarkedFindings] = useState(new Set());
  const [filters, setFilters] = useState({
    searchTerm: '',
    dateRange: 'all',
    unreadOnly: false,
    sortBy: 'date',
    sortOrder: 'desc'
  });
  const scrollContainerRef = useRef(null);
  const scrollPositionRef = useRef(null);

  // Custom link renderer to open external links in new tab
  const LinkRenderer = ({ href, children, ...props }) => {
    // Check if it's an external link
    const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
    
    if (isExternal) {
      return (
        <a 
          href={href} 
          target="_blank" 
          rel="noopener noreferrer" 
          onClick={(e) => e.stopPropagation()} // Prevent parent click handlers from interfering
          {...props}
        >
          {children}
        </a>
      );
    }
    
    // Internal links or non-http links use default behavior
    return <a href={href} {...props}>{children}</a>;
  };

  // ReactMarkdown components configuration
  const markdownComponents = {
    a: LinkRenderer
  };

  // Load research data
  const loadResearchData = useCallback(async (isBackground = false) => {
    if (!userId) {
      setLoading(false);
      return;
    }

    try {
      if (!isBackground) {
        setLoading(true);
      } else {
        setIsBackgroundRefreshing(true);
        if (scrollContainerRef.current) {
          scrollPositionRef.current = scrollContainerRef.current.scrollTop;
        }
      }
      setError(null);
      
      const findingsResponse = await getResearchFindings(userId, null, filters.unreadOnly);
      
      // Group findings by topic
      const groupedFindings = {};
      const findings = findingsResponse.findings || [];
      
      findings.forEach(finding => {
        const topicName = finding.topic_name;
        if (!groupedFindings[topicName]) {
          groupedFindings[topicName] = [];
        }
        groupedFindings[topicName].push(finding);
      });

      // Sort findings within each topic by date
      Object.keys(groupedFindings).forEach(topic => {
        groupedFindings[topic].sort((a, b) => 
          (b.research_time || 0) - (a.research_time || 0)
        );
      });

      setResearchData(groupedFindings);

    } catch (err) {
      console.error('Error loading research data:', err);
      setError(`Failed to load research data: ${err.message || 'Please try again.'}`);
    } finally {
      if (!isBackground) {
        setLoading(false);
      } else {
        setIsBackgroundRefreshing(false);
      }
    }
  }, [userId, filters.unreadOnly]);

  useEffect(() => {
    loadResearchData(false);
  }, [loadResearchData]);

  // Mark research notifications as read when user visits this page (only once)
  useEffect(() => {
    markResearchNotificationsRead();
  }, []); // Run only once when component mounts

  // Auto-refresh research data every 10 seconds when user is selected
  useEffect(() => {
    if (!userId) return;

    const interval = setInterval(() => {
      loadResearchData(true);
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [userId, loadResearchData]);

  useLayoutEffect(() => {
    if (scrollContainerRef.current && scrollPositionRef.current !== null) {
      scrollContainerRef.current.scrollTop = scrollPositionRef.current;
      scrollPositionRef.current = null; // Reset after use
    }
  }, [isBackgroundRefreshing, researchData]);

  // Filter and sort topics
  const filteredTopics = useMemo(() => {
    let topics = Object.keys(researchData);

    // Search filter
    if (filters.searchTerm) {
      const searchLower = filters.searchTerm.toLowerCase();
      topics = topics.filter(topic => 
        topic.toLowerCase().includes(searchLower) ||
        researchData[topic].some(finding => 
          finding.findings_summary?.toLowerCase().includes(searchLower) ||
          finding.key_insights?.some(insight => 
            insight.toLowerCase().includes(searchLower)
          )
        )
      );
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = Date.now() / 1000;
      const ranges = {
        week: 7 * 24 * 60 * 60,
        month: 30 * 24 * 60 * 60,
        quarter: 90 * 24 * 60 * 60
      };
      const cutoff = now - ranges[filters.dateRange];

      topics = topics.filter(topic =>
        researchData[topic].some(finding => 
          (finding.research_time || 0) >= cutoff
        )
      );
    }

    // Sort topics
    topics.sort((a, b) => {
      const aFindings = researchData[a];
      const bFindings = researchData[b];

      switch (filters.sortBy) {
        case 'quality':
          const aMaxQuality = Math.max(...aFindings.map(f => f.quality_score || 0));
          const bMaxQuality = Math.max(...bFindings.map(f => f.quality_score || 0));
          return filters.sortOrder === 'desc' ? bMaxQuality - aMaxQuality : aMaxQuality - bMaxQuality;
        
        case 'topic':
          return filters.sortOrder === 'desc' ? b.localeCompare(a) : a.localeCompare(b);
        
        case 'date':
        default:
          const aLatest = Math.max(...aFindings.map(f => f.research_time || 0));
          const bLatest = Math.max(...bFindings.map(f => f.research_time || 0));
          return filters.sortOrder === 'desc' ? bLatest - aLatest : aLatest - bLatest;
      }
    });

    return topics;
  }, [researchData, filters]);

  // Handle topic expand/collapse
  const toggleTopic = (topicName) => {
    const newExpanded = new Set(expandedTopics);
    if (newExpanded.has(topicName)) {
      newExpanded.delete(topicName);
    } else {
      newExpanded.add(topicName);
    }
    setExpandedTopics(newExpanded);
  };

  // Handle bookmark toggle
  const toggleBookmark = (findingId) => {
    const newBookmarked = new Set(bookmarkedFindings);
    if (newBookmarked.has(findingId)) {
      newBookmarked.delete(findingId);
    } else {
      newBookmarked.add(findingId);
    }
    setBookmarkedFindings(newBookmarked);
    
    localStorage.setItem('bookmarkedFindings', JSON.stringify([...newBookmarked]));
  };

  // Handle mark as read
  const handleMarkAsRead = async (findingId) => {
    try {
      await markFindingAsRead(findingId);
      await loadResearchData();
    } catch (err) {
      console.error('Error marking finding as read:', err);
    }
  };

  // Handle delete individual finding
  const handleDeleteFinding = async (findingId, findingSummary) => {
    const summary = findingSummary ? findingSummary.substring(0, 100) + '...' : 'this finding';
    if (!window.confirm(`Are you sure you want to delete ${summary}?`)) {
      return;
    }

    try {
      await deleteResearchFinding(findingId);
      await loadResearchData();
    } catch (err) {
      console.error('Error deleting finding:', err);
      setError('Failed to delete finding. Please try again.');
    }
  };

  // Handle delete all findings for a topic
  const handleDeleteAllTopicFindings = async (topicName) => {
    if (!window.confirm(`Are you sure you want to delete ALL findings for topic "${topicName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await deleteAllTopicFindings(topicName);
      await loadResearchData();
    } catch (err) {
      console.error('Error deleting all topic findings:', err);
      setError('Failed to delete topic findings. Please try again.');
    }
  };

  // Export findings
  const exportFindings = (format = 'text') => {
    if (format === 'text') {
      let content = `Research Findings Export\n${'='.repeat(50)}\n\n`;
      
      filteredTopics.forEach(topic => {
        content += `${topic}\n${'-'.repeat(topic.length)}\n\n`;
        
        researchData[topic].forEach((finding, index) => {
          content += `Finding ${index + 1}:\n`;
          content += `Date: ${new Date(finding.research_time * 1000).toLocaleDateString()}\n`;
          content += `Quality Score: ${finding.quality_score?.toFixed(2) || 'N/A'}\n`;
          content += `Summary: ${finding.findings_summary || 'No summary'}\n\n`;
          
          if (finding.key_insights?.length > 0) {
            content += `Key Insights:\n`;
            finding.key_insights.forEach(insight => {
              content += `• ${insight}\n`;
            });
            content += '\n';
          }
          
          content += `${'-'.repeat(40)}\n\n`;
        });
        
        content += '\n';
      });

      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research-findings-${new Date().toISOString().split('T')[0]}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({
      searchTerm: '',
      dateRange: 'all',
      unreadOnly: false,
      sortBy: 'date',
      sortOrder: 'desc'
    });
  };

  // Load bookmarks from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('bookmarkedFindings');
    if (saved) {
      try {
        setBookmarkedFindings(new Set(JSON.parse(saved)));
      } catch (e) {
        console.error('Error loading bookmarks:', e);
      }
    }
  }, []);

  // Show user selection prompt if no user is selected
  if (!userId) {
    return (
      <div className="research-dashboard">
        <div className="user-selection-prompt">
          <div className="prompt-icon">👤</div>
          <h2>No User Selected</h2>
          <p>
            Please select a user to view research results. You can select a user from the chat page.
          </p>
          <Link to="/" className="select-user-btn">
            Go to Chat & Select User
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="research-dashboard">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading research findings...</p>
        </div>
      </div>
    );
  }

  const totalFindings = Object.values(researchData).reduce((sum, findings) => sum + findings.length, 0);
  const totalTopics = filteredTopics.length;
  const unreadCount = Object.values(researchData).reduce((sum, findings) => 
    sum + findings.filter(f => !f.read).length, 0
  );
  const hasActiveFilters = filters.searchTerm || filters.dateRange !== 'all' || filters.unreadOnly;

  return (
    <div className="research-dashboard" ref={scrollContainerRef}>
      {/* Header */}
      <header className="research-dashboard-header">
        <h1>Research Feed</h1>
        {isBackgroundRefreshing && <div className="background-refresh-indicator">Updating...</div>}
        <p>Explore findings from the autonomous research engine.</p>
      </header>
      
      {/* Stats Overview */}
      <div className="stats-overview">
        <div className="stat-card highlight">
          <div className="stat-number">{unreadCount}</div>
          <div className="stat-label">Unread</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{totalTopics}</div>
          <div className="stat-label">Topics</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{totalFindings}</div>
          <div className="stat-label">Total Findings</div>
        </div>
      </div>

      {/* Header Actions */}
      <div className="header-actions">
        <button 
          className="export-btn"
          onClick={() => exportFindings('text')}
          disabled={totalFindings === 0}
        >
          📄 Export Results
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={loadResearchData}>Retry</button>
        </div>
      )}

      {/* Filters */}
      <div className="research-filters">
        <div className="filters-row">
          {/* Search */}
          <div className="filter-group search-group">
            <label htmlFor="search">Search Results</label>
            <div className="search-input-wrapper">
              <input
                id="search"
                type="text"
                placeholder="Search topics and findings..."
                value={filters.searchTerm}
                onChange={(e) => setFilters(prev => ({ ...prev, searchTerm: e.target.value }))}
                className="search-input"
              />
              {filters.searchTerm && (
                <button 
                  className="clear-search"
                  onClick={() => setFilters(prev => ({ ...prev, searchTerm: '' }))}
                  title="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
          
          {/* Date Range */}
          <div className="filter-group">
            <label htmlFor="date-range">Time Period</label>
            <select
              id="date-range"
              value={filters.dateRange}
              onChange={(e) => setFilters(prev => ({ ...prev, dateRange: e.target.value }))}
            >
              <option value="all">All Time</option>
              <option value="week">Past Week</option>
              <option value="month">Past Month</option>
              <option value="quarter">Past Quarter</option>
            </select>
          </div>

          {/* Unread Filter */}
          <div className="filter-group checkbox-group">
            <label className="checkbox-filter">
              <input
                type="checkbox"
                checked={filters.unreadOnly}
                onChange={(e) => setFilters(prev => ({ ...prev, unreadOnly: e.target.checked }))}
              />
              <span>Unread only</span>
            </label>
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
            {totalTopics} topic{totalTopics !== 1 ? 's' : ''} with {totalFindings} finding{totalFindings !== 1 ? 's' : ''}
          </span>
          {hasActiveFilters && (
            <span className="filter-indicator">
              (filtered)
            </span>
          )}
        </div>
      </div>

      {/* Results Content */}
      <div className="results-content">
        {filteredTopics.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <h3>No Research Results Found</h3>
            <p>
              {totalFindings === 0 
                ? "No research has been conducted yet. Start by enabling research on some topics!"
                : "No results match your current filters. Try adjusting your search criteria."
              }
            </p>
          </div>
        ) : (
          <div className="topics-list">
            {filteredTopics.map(topicName => {
              const findings = researchData[topicName];
              const isExpanded = expandedTopics.has(topicName);
              const unreadInTopic = findings.filter(f => !f.read).length;
              const latestFinding = findings[0];
              const avgQuality = findings.reduce((sum, f) => sum + (f.quality_score || 0), 0) / findings.length;

              return (
                <div key={topicName} className="topic-card">
                  <div 
                    className="topic-header"
                    onClick={() => toggleTopic(topicName)}
                  >
                    <div className="topic-info">
                      <h3 className="topic-name">{topicName}</h3>
                      <div className="topic-stats">
                        <span className="findings-count">{findings.length} findings</span>
                        {unreadInTopic > 0 && (
                          <span className="unread-badge">{unreadInTopic} new</span>
                        )}
                        <span className="quality-score">
                          Quality: {avgQuality.toFixed(1)}
                        </span>
                        <span className="last-updated">
                          {new Date(latestFinding.research_time * 1000).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="topic-actions">
                      <button
                        className="delete-topic-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteAllTopicFindings(topicName);
                        }}
                        title={`Delete all ${findings.length} findings for this topic`}
                      >
                        🗑️ Delete All
                      </button>
                      <div className="topic-toggle">
                        <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                          ▼
                        </span>
                      </div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="findings-list">
                      {findings.map((finding, index) => (
                        <div 
                          key={finding.finding_id || index} 
                          className={`finding-item ${!finding.read ? 'unread' : ''}`}
                        >
                          <div className="finding-header">
                            <div className="finding-meta">
                              <span className="finding-date">
                                {new Date(finding.research_time * 1000).toLocaleDateString()}
                              </span>
                              <span className="quality-badge">
                                {finding.quality_score?.toFixed(1) || 'N/A'}
                              </span>
                              {!finding.read && (
                                <span className="new-indicator">New</span>
                              )}
                            </div>
                            
                            <div className="finding-actions">
                              <button
                                className={`bookmark-btn ${bookmarkedFindings.has(finding.finding_id) ? 'bookmarked' : ''}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleBookmark(finding.finding_id);
                                }}
                                title={bookmarkedFindings.has(finding.finding_id) ? 'Remove bookmark' : 'Bookmark'}
                              >
                                {bookmarkedFindings.has(finding.finding_id) ? '⭐' : '☆'}
                              </button>
                              
                              {!finding.read && (
                                <button
                                  className="mark-read-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleMarkAsRead(finding.finding_id);
                                  }}
                                  title="Mark as read"
                                >
                                  ✓
                                </button>
                              )}
                              
                              <button
                                className="delete-finding-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteFinding(finding.finding_id, finding.findings_summary);
                                }}
                                title="Delete this finding"
                              >
                                🗑️
                              </button>
                            </div>
                          </div>

                          <div className="finding-content">
                            {/* Display formatted content with citations if available, otherwise fallback to summary */}
                            {finding.formatted_content ? (
                              <div className="finding-formatted-content">
                                <ReactMarkdown components={markdownComponents}>{finding.formatted_content}</ReactMarkdown>
                              </div>
                            ) : finding.findings_summary && (
                              <div className="finding-summary">
                                <p>{finding.findings_summary}</p>
                              </div>
                            )}

                            {finding.key_insights && finding.key_insights.length > 0 && (
                              <div className="key-insights">
                                <h4>Key Insights</h4>
                                <ul>
                                  {finding.key_insights.map((insight, i) => (
                                    <li key={i}>{insight}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Display structured search sources if available, otherwise fallback to source URLs */}
                            {finding.search_sources && finding.search_sources.length > 0 ? (
                              <div className="search-sources">
                                <h4>Sources</h4>
                                <div className="sources-list">
                                  {finding.search_sources.map((source, i) => (
                                    <a 
                                      key={i} 
                                      href={source.url} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      className="source-link"
                                    >
                                      [{i + 1}]. {source.title || `Source ${i + 1}`}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            ) : finding.source_urls && finding.source_urls.length > 0 && (
                              <div className="source-urls">
                                <h4>Sources</h4>
                                <div className="urls-list">
                                  {finding.source_urls.map((url, i) => (
                                    <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                                      Source {i + 1}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchResultsDashboard; 