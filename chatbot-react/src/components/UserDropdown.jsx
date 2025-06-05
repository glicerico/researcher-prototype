import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getUsers, createUser, getCurrentUser } from '../services/api';
import { generateDisplayName } from '../utils/userUtils';
import '../styles/UserDropdown.css';

const UserDropdown = ({ onUserSelected, currentUserId, currentDisplayName, profileUpdateTime = 0 }) => {
  const [users, setUsers] = useState([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [newUserName, setNewUserName] = useState('');
  const [error, setError] = useState(null);
  
  const dropdownRef = useRef(null);
  
  // Load users when component mounts or when profileUpdateTime changes
  useEffect(() => {
    const loadUsers = async () => {
      try {
        console.log('Loading users. Current user ID:', currentUserId, 'Display name:', currentDisplayName);
        setIsLoading(true);
        setError(null); // Clear any previous errors
        
        // Load users and get current user data if needed
        const [usersData, currentUserData] = await Promise.all([
          getUsers(),
          // Only fetch current user if we have an ID but no display name
          (currentUserId && !currentDisplayName) ? getCurrentUser() : Promise.resolve(null)
        ]);
        
        // Set users data
        setUsers(Array.isArray(usersData) ? usersData : []);
        console.log('Users loaded:', usersData);
        
        // Check if the current user ID actually exists in the users list
        if (currentUserId && Array.isArray(usersData)) {
          const userExists = usersData.some(user => user.user_id === currentUserId);
          if (!userExists) {
            console.log('Current user ID not found in users list, clearing selection');
            localStorage.removeItem('user_id');
            onUserSelected('', ''); // Clear the current user selection
            return;
          }
        }
        
        // Update current user display name if needed
        if (currentUserData && currentUserData.display_name) {
          console.log('Setting display name from loaded data:', currentUserData.display_name);
          onUserSelected(currentUserId, currentUserData.display_name);
        }
      } catch (error) {
        console.error('Error loading users:', error);
        setError('Failed to load users');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadUsers();
  }, [currentUserId, currentDisplayName, onUserSelected, profileUpdateTime]); // Add profileUpdateTime to dependency array
  
  // Handle clicks outside the dropdown to close it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // Reload users when dropdown is opened
  useEffect(() => {
    if (isDropdownOpen) {
      const reloadUsers = async () => {
        try {
          console.log('Reloading users on dropdown open');
          setIsLoading(true);
          
          const usersData = await getUsers();
          setUsers(Array.isArray(usersData) ? usersData : []);
          
          console.log('Users reloaded:', usersData);
        } catch (error) {
          console.error('Error reloading users:', error);
          // Don't show error message for reloads to avoid user confusion
        } finally {
          setIsLoading(false);
        }
      };
      
      reloadUsers();
    }
  }, [isDropdownOpen]);
  
  // Handle selecting a user
  const handleUserSelect = useCallback((userId, displayName) => {
    if (userId !== currentUserId) {
      onUserSelected(userId, displayName);
      localStorage.setItem('user_id', userId);
    }
    setIsDropdownOpen(false);
  }, [currentUserId, onUserSelected]);
  
  // Handle creating a new user
  const handleCreateUser = async () => {
    // Validate input
    if (!newUserName.trim()) {
      setError('Please enter a name for the new user');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      
      // Create the user and get the result
      const newUser = await createUser({ display_name: newUserName.trim() });
      console.log('Created new user:', newUser);
      
      // Reload user list and select the new user
      const updatedUsers = await getUsers();
      setUsers(Array.isArray(updatedUsers) ? updatedUsers : []);
      
      // Select the newly created user
      if (newUser && newUser.user_id) {
        onUserSelected(newUser.user_id, newUser.display_name);
        setIsDropdownOpen(false);
      }
      
      // Reset new user form
      setNewUserName('');
      setIsCreatingUser(false);
    } catch (error) {
      console.error('Error creating user:', error);
      setError('Failed to create user: ' + (error.message || 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="user-dropdown" ref={dropdownRef}>
      <button 
        className="selected-user-button"
        onClick={() => !isLoading && setIsDropdownOpen(!isDropdownOpen)}
        disabled={isLoading}
      >
        <span className="user-icon">👤</span>
        {currentUserId ? 
          (currentDisplayName || 'Anonymous User') : 
          'Select User'
        }
        <span className="dropdown-arrow">{isLoading ? '⟳' : '▼'}</span>
      </button>
      
      {isDropdownOpen && (
        <div className="dropdown-menu">
          <div className="dropdown-menu-header">
            <h4>Select User</h4>
            {!isLoading && (
              <button 
                className="refresh-button" 
                onClick={async (e) => {
                  e.stopPropagation();
                  try {
                    setIsLoading(true);
                    const usersData = await getUsers();
                    setUsers(Array.isArray(usersData) ? usersData : []);
                  } catch (error) {
                    console.error('Error refreshing users:', error);
                  } finally {
                    setIsLoading(false);
                  }
                }}
              >
                ⟳
              </button>
            )}
          </div>
          
          <div className="dropdown-menu-content">
            {isLoading && <div className="user-dropdown-loading">Loading users...</div>}
            
            {error && <div className="user-dropdown-error">{error}</div>}
            
            {!isLoading && !error && users.length > 0 && users.map((user) => {
              // Get the display name using the utility function
              const displayName = user.display_name || generateDisplayName(user.user_id);
              
              return (
                <div 
                  key={user.user_id}
                  className={`dropdown-item ${user.user_id === currentUserId ? 'active' : ''}`}
                  onClick={() => handleUserSelect(user.user_id, displayName)}
                >
                  <div className="dropdown-item-content">
                    <span className="dropdown-item-name">{displayName}</span>
                    <span className="dropdown-item-details">
                      {user.personality.style || 'helpful'} • {user.personality.tone || 'friendly'}
                    </span>
                  </div>
                </div>
              );
            })}
            
            {!isLoading && !error && users.length === 0 && (
              <div className="dropdown-item-empty">No users found</div>
            )}
            
            {!isCreatingUser && (
              <div 
                className="dropdown-item create-new-item"
                onClick={() => setIsCreatingUser(true)}
              >
                <div className="dropdown-item-content">
                  <span className="dropdown-item-name">+ Create New User</span>
                </div>
              </div>
            )}
            
            {isCreatingUser && (
              <div className="create-user-form">
                <input
                  type="text"
                  placeholder="Enter name"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  autoFocus
                />
                <div className="create-user-buttons">
                  <button onClick={handleCreateUser}>Create</button>
                  <button onClick={() => {
                    setIsCreatingUser(false);
                    setNewUserName('');
                    setError(null);
                  }}>Cancel</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default UserDropdown; 