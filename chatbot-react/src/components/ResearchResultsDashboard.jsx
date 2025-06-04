import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSession } from '../context/SessionContext';
import { 
  getResearchFindings,
  markFindingAsRead,
  getResearchEngineStatus
} from '../services/api';
import '../styles/ResearchResultsDashboard.css';

const ResearchResultsDashboard = () => {
  const { currentUser } = useSession();
  const [researchData, setResearchData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedTopics, setExpandedTopics] = useState(new Set());
  const [bookmarkedFindings, setBookmarkedFindings] = useState(new Set());
  const [filters, setFilters] = useState({
    searchTerm: '',
    dateRange: 'all', // all, week, month, quarter
    unreadOnly: false,
    sortBy: 'date', // date, quality, topic
    sortOrder: 'desc'
  });

  // Load research data
  const loadResearchData = useCallback(async () => {
    console.log('=== loadResearchData called ===');
    console.log('currentUser:', currentUser);
    
    // Temporary fallback for testing - use a known user ID if currentUser isn't available
    const userId = currentUser?.user_id || 'user-swift-foal-81';
    console.log('Using userId:', userId);
    
    if (!userId) {
      console.log('No userId available, exiting early');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      console.log('Making API calls for user:', userId);

      const [findingsResponse] = await Promise.all([
        getResearchFindings(userId, null, filters.unreadOnly).catch(err => {
          console.error('getResearchFindings error:', err);
          throw err;
        }),
        getResearchEngineStatus().catch(err => {
          console.error('getResearchEngineStatus error:', err);
          throw err;
        })
      ]);

      console.log('API responses received');
      console.log('findingsResponse:', findingsResponse);

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

      console.log('Grouped findings:', groupedFindings);
      setResearchData(groupedFindings);

    } catch (err) {
      console.error('Error loading research data:', err);
      setError(`Failed to load research data: ${err.message || 'Please try again.'}`);
    } finally {
      setLoading(false);
    }
  }, [currentUser, filters.unreadOnly]);

  useEffect(() => {
    loadResearchData();
  }, [loadResearchData]);

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
    
    // Save to localStorage
    localStorage.setItem('bookmarkedFindings', JSON.stringify([...newBookmarked]));
  };

  // Handle mark as read
  const handleMarkAsRead = async (findingId) => {
    try {
      await markFindingAsRead(findingId);
      await loadResearchData(); // Refresh data
    } catch (err) {
      console.error('Error marking finding as read:', err);
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

      // Download as text file
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research-findings-${new Date().toISOString().split('T')[0]}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
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

  return (
    <div className="research-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>Research Results</h1>
          <div className="stats-summary">
            <div className="stat-item">
              <span className="stat-number">{totalTopics}</span>
              <span className="stat-label">Topics</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{totalFindings}</span>
              <span className="stat-label">Findings</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{unreadCount}</span>
              <span className="stat-label">Unread</span>
            </div>
          </div>
        </div>
        
        <div className="header-actions">
          <button 
            className="export-btn"
            onClick={() => exportFindings('text')}
            disabled={totalFindings === 0}
          >
            📄 Export Results
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={loadResearchData}>Retry</button>
        </div>
      )}

      {/* Filters */}
      <div className="filters-section">
        <div className="filter-row">
          <div className="search-filter">
            <input
              type="text"
              placeholder="Search topics and findings..."
              value={filters.searchTerm}
              onChange={(e) => setFilters(prev => ({ ...prev, searchTerm: e.target.value }))}
              className="search-input"
            />
          </div>
          
          <div className="filter-group">
            <select
              value={filters.dateRange}
              onChange={(e) => setFilters(prev => ({ ...prev, dateRange: e.target.value }))}
              className="filter-select"
            >
              <option value="all">All Time</option>
              <option value="week">Past Week</option>
              <option value="month">Past Month</option>
              <option value="quarter">Past Quarter</option>
            </select>
            
            <select
              value={filters.sortBy}
              onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value }))}
              className="filter-select"
            >
              <option value="date">Sort by Date</option>
              <option value="quality">Sort by Quality</option>
              <option value="topic">Sort by Topic</option>
            </select>
            
            <button
              className={`sort-order-btn ${filters.sortOrder}`}
              onClick={() => setFilters(prev => ({ 
                ...prev, 
                sortOrder: prev.sortOrder === 'desc' ? 'asc' : 'desc' 
              }))}
            >
              {filters.sortOrder === 'desc' ? '↓' : '↑'}
            </button>
          </div>
          
          <label className="checkbox-filter">
            <input
              type="checkbox"
              checked={filters.unreadOnly}
              onChange={(e) => setFilters(prev => ({ ...prev, unreadOnly: e.target.checked }))}
            />
            Unread only
          </label>
        </div>
      </div>

      {/* Results Content */}
      <div className="results-content">
        {filteredTopics.length === 0 ? (
          <div className="empty-state">
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
                <div key={topicName} className="topic-section">
                  <div 
                    className="topic-header"
                    onClick={() => toggleTopic(topicName)}
                  >
                    <div className="topic-info">
                      <h3 className="topic-name">{topicName}</h3>
                      <div className="topic-meta">
                        <span className="findings-count">{findings.length} findings</span>
                        {unreadInTopic > 0 && (
                          <span className="unread-badge">{unreadInTopic} unread</span>
                        )}
                        <span className="quality-score">
                          Avg Quality: {avgQuality.toFixed(2)}
                        </span>
                        <span className="last-updated">
                          Last: {new Date(latestFinding.research_time * 1000).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="topic-toggle">
                      <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                        ▼
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="findings-list">
                      {findings.map((finding, index) => (
                        <div 
                          key={finding.finding_id || index} 
                          className={`finding-card ${!finding.read ? 'unread' : ''}`}
                        >
                          <div className="finding-header">
                            <div className="finding-meta">
                              <span className="finding-date">
                                {new Date(finding.research_time * 1000).toLocaleDateString()}
                              </span>
                              <span className="quality-badge">
                                Quality: {finding.quality_score?.toFixed(2) || 'N/A'}
                              </span>
                              {!finding.read && (
                                <span className="unread-indicator">New</span>
                              )}
                            </div>
                            <div className="finding-actions">
                              <button
                                className={`bookmark-btn ${bookmarkedFindings.has(finding.finding_id) ? 'bookmarked' : ''}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleBookmark(finding.finding_id);
                                }}
                                title="Bookmark this finding"
                              >
                                ⭐
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
                            </div>
                          </div>

                          <div className="finding-content">
                            <div className="finding-summary">
                              <p>{finding.findings_summary || 'No summary available'}</p>
                            </div>

                            {finding.key_insights && finding.key_insights.length > 0 && (
                              <div className="key-insights">
                                <h4>Key Insights:</h4>
                                <ul>
                                  {finding.key_insights.map((insight, i) => (
                                    <li key={i}>{insight}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {finding.source_urls && finding.source_urls.length > 0 && (
                              <div className="source-urls">
                                <h4>Sources:</h4>
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