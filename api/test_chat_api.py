#!/usr/bin/env python3
"""
Test script for the Chat API endpoints

This script demonstrates how to:
1. Create a chat session with a retriever
2. Send messages and get AI responses
3. View chat history
4. Manage chats

Prerequisites:
- API server running on http://localhost:8000
- A valid retriever ID from the retriever API
- OPENAI_API_KEY environment variable set
"""

import requests
import json
import uuid
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"

# Sample retriever ID - replace with a real one from your system
SAMPLE_RETRIEVER_ID = str(uuid.uuid4())


def make_request(method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request and handle response"""
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return {}


def test_create_chat():
    """Test creating a new chat session"""
    print("🚀 Testing Chat Creation...")
    
    payload = {
        "name": "My Test Chat",
        "retriever_config_id": SAMPLE_RETRIEVER_ID,
        "metadata": {
            "test": True,
            "description": "Testing chat functionality"
        }
    }
    
    response = make_request("POST", CHAT_ENDPOINT, json=payload)
    
    if response:
        print(f"✅ Chat created successfully!")
        print(f"   Chat ID: {response.get('id')}")
        print(f"   Name: {response.get('name')}")
        print(f"   Retriever ID: {response.get('retriever_config_id')}")
        return response.get('id')
    else:
        print("❌ Failed to create chat")
        return None


def test_list_chats():
    """Test listing all chats"""
    print("\n📋 Testing Chat Listing...")
    
    response = make_request("GET", CHAT_ENDPOINT)
    
    if response:
        print(f"✅ Found {len(response)} chats:")
        for chat in response:
            print(f"   - {chat.get('name')} (ID: {chat.get('id')})")
            print(f"     Messages: {chat.get('message_count')}")
            print(f"     Retriever: {chat.get('retriever_config_name')}")
    else:
        print("❌ Failed to list chats")


def test_send_message(chat_id: str):
    """Test sending a message and getting AI response"""
    print(f"\n💬 Testing Message Sending (Chat ID: {chat_id})...")
    
    payload = {
        "message": "Hello! Can you tell me about the available documents?",
        "model": "gpt-3.5-turbo",
        "stream": False,
        "context_config": {
            "top_k": 5,
            "system_prompt": "You are a helpful document assistant. Answer based on the provided context."
        }
    }
    
    response = make_request("POST", f"{CHAT_ENDPOINT}/{chat_id}", json=payload)
    
    if response:
        print("✅ Message sent successfully!")
        print(f"   Response: {response.get('response')[:200]}...")
        print(f"   Model: {response.get('model_used')}")
        print(f"   Processing Time: {response.get('processing_time'):.2f}s")
        print(f"   Sources Found: {len(response.get('sources', []))}")
        
        # Show sources
        for i, source in enumerate(response.get('sources', [])[:2], 1):
            print(f"   Source {i}: {source.get('content')[:100]}... (Score: {source.get('score', 0):.3f})")
        
        return response.get('message_id')
    else:
        print("❌ Failed to send message")
        return None


def test_get_chat_details(chat_id: str):
    """Test getting full chat details with message history"""
    print(f"\n🔍 Testing Chat Details (Chat ID: {chat_id})...")
    
    response = make_request("GET", f"{CHAT_ENDPOINT}/{chat_id}")
    
    if response:
        print("✅ Chat details retrieved!")
        print(f"   Name: {response.get('name')}")
        print(f"   Total Messages: {response.get('message_count')}")
        print(f"   Retriever: {response.get('retriever_config_name')}")
        
        messages = response.get('messages', [])
        print(f"   Message History ({len(messages)} messages):")
        for msg in messages:
            role = "🙋 User" if msg.get('role') == 'user' else "🤖 Assistant"
            content = msg.get('content', '')[:100]
            print(f"     {role}: {content}...")
    else:
        print("❌ Failed to get chat details")


def test_delete_message(chat_id: str, message_id: str):
    """Test deleting a specific message"""
    print(f"\n🗑️ Testing Message Deletion (Message ID: {message_id})...")
    
    response = requests.delete(f"{CHAT_ENDPOINT}/{chat_id}/messages/{message_id}")
    
    if response.status_code == 204:
        print("✅ Message deleted successfully!")
    else:
        print(f"❌ Failed to delete message: {response.status_code}")
        print(f"   Response: {response.text}")


def test_delete_chat(chat_id: str):
    """Test deleting a chat"""
    print(f"\n🗑️ Testing Chat Deletion (Chat ID: {chat_id})...")
    
    response = requests.delete(f"{CHAT_ENDPOINT}/{chat_id}")
    
    if response.status_code == 204:
        print("✅ Chat deleted successfully!")
    else:
        print(f"❌ Failed to delete chat: {response.status_code}")
        print(f"   Response: {response.text}")


def main():
    """Run the complete chat API test suite"""
    print("🧪 Chat API Test Suite")
    print("=" * 50)
    
    # Note: This test will fail until you have a real retriever ID
    print(f"⚠️  Note: Using sample retriever ID: {SAMPLE_RETRIEVER_ID}")
    print("   Replace with a real retriever ID from your system")
    
    # Test chat creation
    chat_id = test_create_chat()
    if not chat_id:
        print("❌ Cannot proceed without a chat ID")
        return
    
    # Test listing chats
    test_list_chats()
    
    # Test sending a message
    message_id = test_send_message(chat_id)
    
    # Test getting chat details
    test_get_chat_details(chat_id)
    
    # Test message deletion (if we have a message ID)
    if message_id:
        test_delete_message(chat_id, message_id)
    
    # Test chat deletion
    test_delete_chat(chat_id)
    
    print("\n🎉 Test suite completed!")


if __name__ == "__main__":
    main() 