#!/usr/bin/env python3
"""
Test script to verify autorag package installation and imports
"""
import sys
import os

print("Python path:")
for path in sys.path:
    print(f"  {path}")

print("\nAutoRAG package location:")
try:
    import autorag
    print(f"  Location: {autorag.__file__}")
    
    # Test basic import without checking package metadata
    print("  Basic autorag import successful")
    
    # Test a simple import that should work
    try:
        from autorag.nodes.generator import llm
        print("  Generator LLM import successful")
    except ImportError as e:
        print(f"  Generator LLM import failed: {e}")
    
    print("✅ AutoRAG import successful!")
    
except ImportError as e:
    print(f"❌ AutoRAG import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1) 