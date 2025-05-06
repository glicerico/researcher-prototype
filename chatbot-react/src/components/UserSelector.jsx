import React, { useState, useEffect, useCallback } from 'react';
import { getUsers, createUser, updateUserDisplayName } from '../services/api';
import '../styles/UserSelector.css';

const UserSelector = ({ onUserSelected }) => {
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [editingUserId, setEditingUserId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Wrap the user selection handler in useCallback to prevent recreating it on each render
  const handleUserSelect = useCallback((userId) => {
    setSelectedUserId(userId);
    localStorage.setItem('user_id', userId);
    onUserSelected(userId);
  }, [onUserSelected]);

  // Load users only once when component mounts
  useEffect(() => {
    let isMounted = true;
    
    const loadUsers = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const userData = await getUsers();
        
        // Only update state if component is still mounted
        if (isMounted) {
          setUsers(userData);
          
          // Check if there's a previously selected user in localStorage
          const savedUserId = localStorage.getItem('user_id');
          if (savedUserId && userData.some(user => user.user_id === savedUserId)) {
            setSelectedUserId(savedUserId);
            onUserSelected(savedUserId);
          } else if (userData.length > 0) {
            // Select the first user if none is saved
            setSelectedUserId(userData[0].user_id);
            localStorage.setItem('user_id', userData[0].user_id);
            onUserSelected(userData[0].user_id);
          }
        }
      } catch (error) {
        console.error('Error loading users:', error);
        if (isMounted) {
          setError('Failed to load users. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    
    loadUsers();
    
    // Cleanup function to prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, []); // Empty dependency array to ensure it runs only once

  const handleCreateUser = async () => {
    if (!newUserName.trim()) {
      alert('Please enter a name for the new user');
      return;
    }

    try {
      setIsLoading(true);
      const newUser = await createUser(newUserName);
      setUsers(prevUsers => [...prevUsers, {
        user_id: newUser.user_id,
        created_at: newUser.created_at,
        personality_style: newUser.personality.style,
        personality_tone: newUser.personality.tone,
        conversation_count: 0,
        display_name: newUserName
      }]);
      
      setNewUserName('');
      setIsCreatingUser(false);
      handleUserSelect(newUser.user_id);
    } catch (error) {
      console.error('Error creating user:', error);
      alert('Failed to create user');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditName = async (userId) => {
    if (!editingName.trim()) {
      alert('Please enter a name');
      return;
    }

    try {
      setIsLoading(true);
      await updateUserDisplayName(userId, editingName);
      
      // Update local users list using functional update to avoid stale state
      setUsers(prevUsers => prevUsers.map(user => 
        user.user_id === userId 
          ? { ...user, display_name: editingName } 
          : user
      ));
      
      setEditingUserId(null);
      setEditingName('');
    } catch (error) {
      console.error('Error updating user name:', error);
      alert('Failed to update user name');
    } finally {
      setIsLoading(false);
    }
  };

  const startEditingName = (userId, currentName) => {
    setEditingUserId(userId);
    setEditingName(currentName);
  };

  if (isLoading && users.length === 0) {
    return <div className="user-selector-loading">Loading users...</div>;
  }

  if (error) {
    return <div className="user-selector-error">{error}</div>;
  }

  return (
    <div className="user-selector">
      <div className="user-selector-header">
        <h3>Select User</h3>
        <button 
          className="create-user-btn"
          onClick={() => setIsCreatingUser(!isCreatingUser)}
          disabled={isLoading}
        >
          {isCreatingUser ? 'Cancel' : 'New User'}
        </button>
      </div>
      
      {isCreatingUser && (
        <div className="create-user-form">
          <input
            type="text"
            placeholder="Enter user name"
            value={newUserName}
            onChange={(e) => setNewUserName(e.target.value)}
            disabled={isLoading}
          />
          <button 
            onClick={handleCreateUser}
            disabled={isLoading}
          >
            Create
          </button>
        </div>
      )}
      
      <div className="user-list">
        {users.length === 0 ? (
          <div className="no-users">No users found. Create a new user to get started.</div>
        ) : (
          users.map(user => (
            <div 
              key={user.user_id} 
              className={`user-item ${selectedUserId === user.user_id ? 'selected' : ''}`}
              onClick={() => !isLoading && handleUserSelect(user.user_id)}
            >
              <div className="user-info">
                {editingUserId === user.user_id ? (
                  <div className="edit-name-form">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      disabled={isLoading}
                    />
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditName(user.user_id);
                      }}
                      disabled={isLoading}
                    >
                      Save
                    </button>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingUserId(null);
                      }}
                      disabled={isLoading}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="user-name">
                    <span>{user.display_name}</span>
                    <button 
                      className="edit-name-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        startEditingName(user.user_id, user.display_name);
                      }}
                      disabled={isLoading}
                    >
                      ✏️
                    </button>
                  </div>
                )}
                <div className="user-details">
                  <span>Style: {user.personality_style}</span>
                  <span>Tone: {user.personality_tone}</span>
                  <span>Conversations: {user.conversation_count}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default UserSelector; 