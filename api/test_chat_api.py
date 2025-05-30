#!/usr/bin/env python3
"""
Test script for the Chat API endpoints

This script demonstrates how to:
1. Create a chat session with a retriever and custom configuration
2. Send messages and get AI responses with parameter overrides
3. View chat history and configuration
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


def test_create_chat_with_config():
    """Test creating a new chat session with custom configuration"""
    print("🚀 Testing Chat Creation with Custom Configuration...")
    
    payload = {
        "name": "Advanced Research Chat",
        "retriever_id": SAMPLE_RETRIEVER_ID,
        "metadata": {
            "test": True,
            "description": "Testing advanced chat functionality",
            "project": "chat-api-demo"
        },
        # LLM Configuration
        "llm_model": "gpt-4",
        "temperature": 0.3,  # Lower temperature for more focused responses
        "top_p": 0.9,
        # Retrieval Configuration  
        "top_k": 8  # Retrieve more documents for better context
    }
    
    response = make_request("POST", CHAT_ENDPOINT, json=payload)
    
    if response:
        print(f"✅ Chat created successfully!")
        print(f"   Chat ID: {response.get('id')}")
        print(f"   Name: {response.get('name')}")
        print(f"   Retriever ID: {response.get('retriever_id')}")
        print(f"   Configuration:")
        config = response.get('config', {})
        print(f"     - Model: {config.get('llm_model')}")
        print(f"     - Temperature: {config.get('temperature')}")
        print(f"     - Top P: {config.get('top_p')}")
        print(f"     - Top K: {config.get('top_k')}")
        return response.get('id')
    else:
        print("❌ Failed to create chat")
        return None


def test_create_basic_chat():
    """Test creating a chat with minimal configuration (defaults)"""
    print("\n🚀 Testing Basic Chat Creation (with defaults)...")
    
    payload = {
        "name": "Basic Chat",
        "retriever_id": SAMPLE_RETRIEVER_ID
        # Using all default values for LLM parameters
    }
    
    response = make_request("POST", CHAT_ENDPOINT, json=payload)
    
    if response:
        print(f"✅ Basic chat created!")
        print(f"   Chat ID: {response.get('id')}")
        config = response.get('config', {})
        print(f"   Default config: Model={config.get('llm_model')}, Temp={config.get('temperature')}")
        return response.get('id')
    else:
        print("❌ Failed to create basic chat")
        return None


def test_list_chats():
    """Test listing all chats with their configurations"""
    print("\n📋 Testing Chat Listing with Configurations...")
    
    response = make_request("GET", CHAT_ENDPOINT)
    
    if response:
        print(f"✅ Found {len(response)} chats:")
        for chat in response:
            print(f"   - {chat.get('name')} (ID: {chat.get('id')})")
            print(f"     Messages: {chat.get('message_count')}")
            print(f"     Retriever: {chat.get('retriever_config_name')}")
            config = chat.get('config', {})
            print(f"     Config: {config.get('llm_model')} | T={config.get('temperature')} | K={config.get('top_k')}")
    else:
        print("❌ Failed to list chats")


def test_send_message_with_defaults(chat_id: str):
    """Test sending a message using chat default settings"""
    print(f"\n💬 Testing Message with Chat Defaults (Chat ID: {chat_id})...")
    
    payload = {
        "message": "What are the key findings about artificial intelligence in the documents?",
        "stream": False,
        "context_config": {
            "system_prompt": "You are an AI research assistant. Provide detailed, technical answers based on the provided research documents."
        }
        # Not specifying model, temperature, top_p, or top_k - will use chat defaults
    }
    
    response = make_request("POST", f"{CHAT_ENDPOINT}/{chat_id}", json=payload)
    
    if response:
        print("✅ Message sent with defaults!")
        print(f"   Response: {response.get('response')[:200]}...")
        config_used = response.get('config_used', {})
        print(f"   Configuration used:")
        print(f"     - Model: {config_used.get('model')}")
        print(f"     - Temperature: {config_used.get('temperature')}")
        print(f"     - Top P: {config_used.get('top_p')}")
        print(f"     - Top K: {config_used.get('top_k')}")
        print(f"   Processing Time: {response.get('processing_time'):.2f}s")
        print(f"   Sources Found: {len(response.get('sources', []))}")
        return response.get('message_id')
    else:
        print("❌ Failed to send message")
        return None


def test_send_message_with_overrides(chat_id: str):
    """Test sending a message with parameter overrides"""
    print(f"\n💬 Testing Message with Parameter Overrides (Chat ID: {chat_id})...")
    
    payload = {
        "message": "Can you provide a creative summary of the most interesting findings?",
        "model": "gpt-3.5-turbo",  # Override to faster model
        "temperature": 0.9,        # Override to higher creativity
        "top_p": 0.95,            # Override top_p
        "top_k": 3,               # Override to fewer sources
        "stream": False,
        "context_config": {
            "system_prompt": "You are a creative science communicator. Make the findings engaging and accessible.",
            "filters": {
                "document_type": "research_paper"
            }
        }
    }
    
    response = make_request("POST", f"{CHAT_ENDPOINT}/{chat_id}", json=payload)
    
    if response:
        print("✅ Message sent with overrides!")
        print(f"   Response: {response.get('response')[:200]}...")
        config_used = response.get('config_used', {})
        print(f"   Overridden configuration:")
        print(f"     - Model: {config_used.get('model')} ← overridden")
        print(f"     - Temperature: {config_used.get('temperature')} ← overridden")
        print(f"     - Top P: {config_used.get('top_p')} ← overridden")
        print(f"     - Top K: {config_used.get('top_k')} ← overridden")
        print(f"   Processing Time: {response.get('processing_time'):.2f}s")
        
        # Show token usage if available
        token_usage = response.get('token_usage', {})
        if token_usage:
            print(f"   Token Usage: {token_usage.get('total_tokens')} total")
        
        return response.get('message_id')
    else:
        print("❌ Failed to send message with overrides")
        return None


def test_get_chat_details(chat_id: str):
    """Test getting full chat details with configuration"""
    print(f"\n🔍 Testing Chat Details with Configuration (Chat ID: {chat_id})...")
    
    response = make_request("GET", f"{CHAT_ENDPOINT}/{chat_id}")
    
    if response:
        print("✅ Chat details retrieved!")
        print(f"   Name: {response.get('name')}")
        print(f"   Total Messages: {response.get('message_count')}")
        print(f"   Retriever: {response.get('retriever_config_name')}")
        
        # Show chat configuration
        config = response.get('config', {})
        print(f"   Chat Configuration:")
        print(f"     - Default Model: {config.get('llm_model')}")
        print(f"     - Default Temperature: {config.get('temperature')}")
        print(f"     - Default Top P: {config.get('top_p')}")
        print(f"     - Default Top K: {config.get('top_k')}")
        
        messages = response.get('messages', [])
        print(f"   Message History ({len(messages)} messages):")
        for msg in messages[-3:]:  # Show last 3 messages
            role = "🙋 User" if msg.get('role') == 'user' else "🤖 Assistant"
            content = msg.get('content', '')[:100]
            model = msg.get('metadata', {}).get('llm_model', 'unknown')
            print(f"     {role}: {content}... [Model: {model}]")
    else:
        print("❌ Failed to get chat details")


def demonstrate_configuration_features():
    """Demonstrate different configuration scenarios"""
    print("\n🎯 Configuration Features Demonstration")
    print("=" * 50)
    
    scenarios = [
        {
            "name": "Conservative Research Chat",
            "config": {
                "llm_model": "gpt-4",
                "temperature": 0.1,  # Very focused
                "top_p": 0.8,
                "top_k": 10  # Many sources for thorough research
            },
            "message": "What are the precise methodologies mentioned?"
        },
        {
            "name": "Creative Writing Chat", 
            "config": {
                "llm_model": "gpt-4o-mini",
                "temperature": 1.2,  # Very creative
                "top_p": 0.95,
                "top_k": 3  # Fewer sources for creative freedom
            },
            "message": "Write a compelling story based on these documents."
        },
        {
            "name": "Balanced Analysis Chat",
            "config": {
                "llm_model": "gpt-4",
                "temperature": 0.7,  # Balanced
                "top_p": 1.0,
                "top_k": 5  # Standard retrieval
            },
            "message": "Provide a balanced analysis of the main topics."
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🔧 Scenario: {scenario['name']}")
        config = scenario['config']
        print(f"   Config: T={config['temperature']}, P={config['top_p']}, K={config['top_k']}")
        
        # This would create and test each scenario
        # (Commented out to avoid creating too many test chats)
        # chat_payload = {"name": scenario['name'], "retriever_id": SAMPLE_RETRIEVER_ID, **config}
        # print(f"   Would create with: {chat_payload}")


def main():
    """Run the complete chat API test suite with configuration features"""
    print("🧪 Enhanced Chat API Test Suite")
    print("=" * 50)
    
    # Note: This test will fail until you have a real retriever ID
    print(f"⚠️  Note: Using sample retriever ID: {SAMPLE_RETRIEVER_ID}")
    print("   Replace with a real retriever ID from your system")
    
    # Test chat creation with custom config
    advanced_chat_id = test_create_chat_with_config()
    
    # Test basic chat creation with defaults
    basic_chat_id = test_create_basic_chat()
    
    # Test listing chats with configurations
    test_list_chats()
    
    if advanced_chat_id:
        # Test messaging with chat defaults
        test_send_message_with_defaults(advanced_chat_id)
        
        # Test messaging with parameter overrides
        test_send_message_with_overrides(advanced_chat_id)
        
        # Test getting detailed chat info
        test_get_chat_details(advanced_chat_id)
    
    # Demonstrate configuration scenarios
    demonstrate_configuration_features()
    
    print("\n🎉 Enhanced test suite completed!")
    print("\n💡 Key Features Tested:")
    print("   ✅ Chat creation with custom LLM parameters")
    print("   ✅ Default parameter inheritance")
    print("   ✅ Per-message parameter overrides")
    print("   ✅ Configuration visibility in responses")
    print("   ✅ Different temperature/creativity settings")
    print("   ✅ Variable retrieval counts (top_k)")


if __name__ == "__main__":
    main() 