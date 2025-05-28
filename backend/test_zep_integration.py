#!/usr/bin/env python3
"""
Simple test script to verify Zep integration.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage.zep_manager import ZepManager
import config

async def test_zep_integration():
    """Test basic Zep functionality."""
    print("Testing Zep Integration...")
    print(f"ZEP_ENABLED: {config.ZEP_ENABLED}")
    print(f"ZEP_API_KEY set: {bool(config.ZEP_API_KEY)}")
    
    # Initialize Zep manager
    zep_manager = ZepManager()
    
    print(f"Zep manager enabled: {zep_manager.is_enabled()}")
    
    if not zep_manager.is_enabled():
        print("❌ Zep is not enabled or not properly configured")
        print("To enable Zep:")
        print("1. Set ZEP_ENABLED=true in your .env file")
        print("2. Set ZEP_API_KEY=your_api_key in your .env file")
        return
    
    # Test storing a conversation
    print("\n🧪 Testing conversation storage...")
    
    test_user_id = "test-user-123"
    test_user_message = "Hello, I'm testing the Zep integration!"
    test_ai_response = "Hello! I can see that Zep is working correctly and storing our conversation."
    
    try:
        success = await zep_manager.store_conversation_turn(
            user_id=test_user_id,
            user_message=test_user_message,
            ai_response=test_ai_response
        )
        
        if success:
            print("✅ Successfully stored conversation in Zep!")
        else:
            print("❌ Failed to store conversation in Zep")
            
    except Exception as e:
        print(f"❌ Error testing Zep: {str(e)}")
    
    print("\n✨ Zep integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_zep_integration()) 