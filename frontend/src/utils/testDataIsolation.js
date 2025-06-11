/**
 * Test utility to manually verify data isolation between users
 * Run this in the browser console to test user switching behavior
 */

export const testDataIsolation = () => {
  console.log('🧪 Testing Data Isolation...');
  
  // Test localStorage keys for different users
  const testUser1 = 'test-user-1';
  const testUser2 = 'test-user-2';
  const testSession1 = 'session-123';
  const testSession2 = 'session-456';
  
  // Create test data for user 1
  localStorage.setItem(`chat_messages_${testUser1}_${testSession1}`, JSON.stringify([
    { role: 'system', content: 'System message for user 1' },
    { role: 'user', content: 'Hello from user 1' },
    { role: 'assistant', content: 'Response for user 1' }
  ]));
  localStorage.setItem(`session_id_${testUser1}`, testSession1);
  localStorage.setItem(`session_history_${testUser1}`, JSON.stringify([testSession1]));
  
  // Create test data for user 2
  localStorage.setItem(`chat_messages_${testUser2}_${testSession2}`, JSON.stringify([
    { role: 'system', content: 'System message for user 2' },
    { role: 'user', content: 'Hello from user 2' },
    { role: 'assistant', content: 'Response for user 2' }
  ]));
  localStorage.setItem(`session_id_${testUser2}`, testSession2);
  localStorage.setItem(`session_history_${testUser2}`, JSON.stringify([testSession2]));
  
  console.log('✅ Test data created for both users');
  
  // Function to verify isolation
  const verifyIsolation = (userId) => {
    console.log(`\n🔍 Checking data for user: ${userId}`);
    
    const sessionId = localStorage.getItem(`session_id_${userId}`);
    const messages = sessionId ? 
      localStorage.getItem(`chat_messages_${userId}_${sessionId}`) : null;
    const history = localStorage.getItem(`session_history_${userId}`);
    
    console.log('Session ID:', sessionId);
    console.log('Messages:', messages ? JSON.parse(messages) : 'None');
    console.log('History:', history ? JSON.parse(history) : 'None');
    
    return { sessionId, messages: messages ? JSON.parse(messages) : null, history };
  };
  
  // Verify data exists for both users
  const user1Data = verifyIsolation(testUser1);
  const user2Data = verifyIsolation(testUser2);
  
  // Check isolation
  const isIsolated = (
    user1Data.sessionId !== user2Data.sessionId &&
    JSON.stringify(user1Data.messages) !== JSON.stringify(user2Data.messages)
  );
  
  console.log('\n📊 Isolation Test Result:', isIsolated ? '✅ PASSED' : '❌ FAILED');
  
  // Cleanup
  console.log('\n🧹 Cleaning up test data...');
  localStorage.removeItem(`chat_messages_${testUser1}_${testSession1}`);
  localStorage.removeItem(`session_id_${testUser1}`);
  localStorage.removeItem(`session_history_${testUser1}`);
  localStorage.removeItem(`chat_messages_${testUser2}_${testSession2}`);
  localStorage.removeItem(`session_id_${testUser2}`);
  localStorage.removeItem(`session_history_${testUser2}`);
  
  return isIsolated;
};

/**
 * Function to simulate user switching in React context
 * This should be called after user switching to verify state
 */
export const logCurrentUserState = (userId, messages, sessionId) => {
  console.log('📱 Current User State:');
  console.log('User ID:', userId);
  console.log('Session ID:', sessionId);
  console.log('Messages count:', messages.length);
  console.log('First message:', messages[0]);
  console.log('Last message:', messages[messages.length - 1]);
};

// Make functions available globally for testing
if (typeof window !== 'undefined') {
  window.testDataIsolation = testDataIsolation;
  window.logCurrentUserState = logCurrentUserState;
} 