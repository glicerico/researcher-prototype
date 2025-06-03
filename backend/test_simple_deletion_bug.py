#!/usr/bin/env python3
"""
Simple test to reproduce the "delete 1 topic, lose 3 topics" bug.
"""
import os
import sys
import time
import shutil

# Add current directory to path
sys.path.append('.')

from storage.user_manager import UserManager
from storage.storage_manager import StorageManager

def setup_test():
    """Set up test environment."""
    test_storage_path = './test_simple_bug'
    if os.path.exists(test_storage_path):
        shutil.rmtree(test_storage_path)
    
    storage = StorageManager(test_storage_path)
    user_mgr = UserManager(storage)
    return storage, user_mgr, test_storage_path

def create_test_topics(user_mgr):
    """Create exactly 5 test topics."""
    user_id = user_mgr.create_user()
    session_id = "test-session"
    
    # Create 5 topics with same timestamp (like they would be in real usage)
    topics = [
        {"name": "Topic A", "description": "First topic", "confidence_score": 0.9},
        {"name": "Topic B", "description": "Second topic", "confidence_score": 0.8},
        {"name": "Topic C", "description": "Third topic", "confidence_score": 0.7},
        {"name": "Topic D", "description": "Fourth topic", "confidence_score": 0.6},
        {"name": "Topic E", "description": "Fifth topic", "confidence_score": 0.5}
    ]
    
    user_mgr.store_topic_suggestions(user_id, session_id, topics, "Test context")
    print(f"✅ Created 5 test topics")
    
    return user_id, session_id

def show_topics(user_mgr, user_id, session_id, title="Topics"):
    """Show current topics."""
    topics_data = user_mgr.get_user_topics(user_id)
    session_topics = topics_data.get("sessions", {}).get(session_id, [])
    
    print(f"\n{title}:")
    for i, topic in enumerate(session_topics):
        print(f"  [{i}] {topic.get('topic_name')} - ID: {topic.get('topic_id', 'NO-ID')[:8]}...")
    print(f"Total: {len(session_topics)} topics")
    return session_topics

def test_api_get_topics(user_mgr, user_id, session_id):
    """Test how the API returns topics (with sorting)."""
    print(f"\n🔄 Testing API GET /topics/suggestions/{session_id}")
    
    # Simulate the actual API endpoint logic
    stored_topics = user_mgr.get_topic_suggestions(user_id, session_id)
    
    # Convert to API response format (like in app.py)
    topic_suggestions = []
    for i, topic in enumerate(stored_topics):
        topic_suggestion = {
            "index": i,  # Original storage index
            "topic_id": topic.get("topic_id"),
            "name": topic.get("topic_name", ""),
            "description": topic.get("description", ""),
            "confidence_score": topic.get("confidence_score", 0.0),
            "suggested_at": topic.get("suggested_at", 0),
            "is_active_research": topic.get("is_active_research", False)
        }
        topic_suggestions.append(topic_suggestion)
    
    # CRITICAL: The API sorts by suggestion time (newest first)
    topic_suggestions.sort(key=lambda x: x["suggested_at"], reverse=True)
    
    print(f"API Response (sorted by time, newest first):")
    for i, topic in enumerate(topic_suggestions):
        print(f"  Dashboard[{i}]: '{topic['name']}' (Storage index: {topic['index']}, ID: {topic['topic_id'][:8]}...)")
    
    return topic_suggestions

def test_dashboard_deletion(user_mgr, user_id, session_id, dashboard_index):
    """Test what happens when dashboard deletes a topic at a specific index."""
    print(f"\n🗑️ Testing dashboard deletion at index {dashboard_index}")
    
    # Step 1: Get current state
    before_topics = show_topics(user_mgr, user_id, session_id, "BEFORE deletion")
    api_topics = test_api_get_topics(user_mgr, user_id, session_id)
    
    if dashboard_index >= len(api_topics):
        print(f"❌ Index {dashboard_index} out of bounds")
        return False
    
    # Step 2: Identify what the dashboard thinks it's deleting
    dashboard_topic = api_topics[dashboard_index]
    storage_index = dashboard_topic["index"]  # The actual storage index
    
    print(f"\n🎯 Dashboard wants to delete:")
    print(f"   Topic: '{dashboard_topic['name']}'")
    print(f"   Dashboard position: {dashboard_index}")
    print(f"   Storage index: {storage_index}")
    
    # Step 3: CRITICAL ISSUE - What index does the dashboard send to the API?
    # If the dashboard sends the dashboard index instead of storage index, wrong topic gets deleted!
    
    print(f"\n🔥 Testing two scenarios:")
    
    # Scenario A: Dashboard correctly sends storage index (CORRECT)
    print(f"A) Dashboard sends storage index {storage_index} to API")
    
    # Scenario B: Dashboard incorrectly sends dashboard index (BUG!)
    print(f"B) Dashboard sends dashboard index {dashboard_index} to API")
    
    if dashboard_index != storage_index:
        print(f"🚨 POTENTIAL BUG: Dashboard index {dashboard_index} != Storage index {storage_index}")
        print(f"   If dashboard sends {dashboard_index}, it will delete the wrong topic!")
        
        # Show what would happen in each scenario
        print(f"\n   Scenario A (correct): Delete topic at storage[{storage_index}] = '{dashboard_topic['name']}'")
        
        # Find what's actually at dashboard_index in storage order
        if dashboard_index < len(before_topics):
            wrong_topic = before_topics[dashboard_index]
            print(f"   Scenario B (BUG): Delete topic at storage[{dashboard_index}] = '{wrong_topic.get('topic_name')}'")
        
        return False  # This indicates the bug
    else:
        print(f"✅ No mismatch: Dashboard index {dashboard_index} == Storage index {storage_index}")
        return True

def simulate_actual_api_call(user_mgr, user_id, session_id, api_index):
    """Simulate the actual API deletion call."""
    print(f"\n🔥 Simulating API call: DELETE /topics/session/{session_id}/topic/{api_index}")
    
    before_count = len(user_mgr.get_topic_suggestions(user_id, session_id))
    
    # Use the actual API deletion method
    result = user_mgr.delete_topic_by_index_safe(user_id, session_id, api_index)
    
    after_topics = user_mgr.get_topic_suggestions(user_id, session_id)
    after_count = len(after_topics)
    
    print(f"Result: {result['success']}")
    if result['success']:
        print(f"Deleted: {result['deleted_topic']['topic_name']}")
    else:
        print(f"Error: {result['error']}")
    
    print(f"Topic count: {before_count} → {after_count} (change: {after_count - before_count})")
    
    return result

def main():
    """Run the simple deletion bug test."""
    print("🚀 Simple Deletion Bug Test")
    print("=" * 50)
    
    try:
        # Setup
        storage, user_mgr, test_storage_path = setup_test()
        user_id, session_id = create_test_topics(user_mgr)
        
        # Show initial state
        initial_topics = show_topics(user_mgr, user_id, session_id, "INITIAL STATE")
        print(f"Starting with {len(initial_topics)} topics")
        
        # Test the dashboard deletion flow
        print(f"\n" + "="*50)
        print(f"TESTING: Delete topic at dashboard position 1")
        print(f"="*50)
        
        # This simulates clicking "delete" on the second topic in the dashboard
        bug_detected = not test_dashboard_deletion(user_mgr, user_id, session_id, 1)
        
        if bug_detected:
            print(f"\n🚨 BUG CONFIRMED!")
            print(f"The dashboard shows topics in sorted order")
            print(f"But the deletion API expects storage order indices")
            print(f"This causes wrong topics to be deleted!")
        
        # Now let's see what actually happens with a real API call
        print(f"\n" + "="*50)
        print(f"SIMULATING ACTUAL API DELETION")
        print(f"="*50)
        
        # Simulate dashboard sending dashboard index (the bug)
        print(f"If dashboard sends dashboard index 1:")
        result = simulate_actual_api_call(user_mgr, user_id, session_id, 1)
        
        show_topics(user_mgr, user_id, session_id, "AFTER DELETION")
        
        return not bug_detected
        
    finally:
        # Cleanup
        if os.path.exists(test_storage_path):
            shutil.rmtree(test_storage_path)
        print(f"\n🧹 Cleanup complete")

if __name__ == "__main__":
    success = main()
    print(f"\nTest result: {'✅ PASS' if success else '❌ BUG DETECTED'}")
    exit(0 if success else 1) 