#!/usr/bin/env python3
"""
Simple Parser Service Test

This script tests the parser service step by step.
Run from the api directory: python tests/simple_parser_test.py
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test if we can import all required modules"""
    print("Testing imports...")
    
    try:
        from app.services.parser_service import ParserService
        print("✓ ParserService imported successfully")
    except Exception as e:
        print(f"✗ Failed to import ParserService: {e}")
        return False
    
    try:
        from app.services.minio_service import MinIOService
        print("✓ MinIOService imported successfully")
    except Exception as e:
        print(f"✗ Failed to import MinIOService: {e}")
        return False
    
    try:
        from app.core.database import get_session
        print("✓ Database session imported successfully")
    except Exception as e:
        print(f"✗ Failed to import database session: {e}")
        return False
    
    return True

def test_autorag_availability():
    """Test AutoRAG module availability"""
    print("\nTesting AutoRAG availability...")
    
    try:
        from app.services.parser_service import LANGCHAIN_AVAILABLE, LLAMAPARSE_AVAILABLE, CLOVA_AVAILABLE
        
        print(f"  Langchain Parse: {'✓' if LANGCHAIN_AVAILABLE else '✗'}")
        print(f"  LlamaParse: {'✓' if LLAMAPARSE_AVAILABLE else '✗'}")
        print(f"  Clova OCR: {'✓' if CLOVA_AVAILABLE else '✗'}")
        
        return LANGCHAIN_AVAILABLE or LLAMAPARSE_AVAILABLE or CLOVA_AVAILABLE
        
    except Exception as e:
        print(f"✗ Failed to check AutoRAG availability: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from app.core.database import get_session
        
        with get_session() as session:
            # Try a simple query
            result = session.exec("SELECT 1").first()
            if result:
                print("✓ Database connection successful")
                return True
            else:
                print("✗ Database query returned no result")
                return False
                
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_minio_connection():
    """Test MinIO connection"""
    print("\nTesting MinIO connection...")
    
    try:
        from app.services.minio_service import MinIOService
        
        minio_service = MinIOService()
        
        # Try to list buckets (this will test the connection)
        buckets = minio_service.client.list_buckets()
        print(f"✓ MinIO connection successful. Found {len(buckets)} buckets")
        
        # Check if our bucket exists
        bucket_exists = minio_service.client.bucket_exists(minio_service.bucket_name)
        print(f"✓ Bucket '{minio_service.bucket_name}' {'exists' if bucket_exists else 'will be created'}")
        
        return True
        
    except Exception as e:
        print(f"✗ MinIO connection failed: {e}")
        return False

def test_parser_service_basic():
    """Test basic parser service functionality"""
    print("\nTesting parser service basic functionality...")
    
    try:
        from app.services.parser_service import ParserService
        from app.core.database import get_session
        
        parser_service = ParserService()
        
        with get_session() as session:
            # Test listing parsers (should work even if empty)
            parsers = parser_service.get_active_parsers(session)
            print(f"✓ Found {len(parsers)} active parsers")
            
            # Test creating a simple parser
            try:
                parser = parser_service.create_parser(
                    session=session,
                    name="test_pdf_parser",
                    module_type="langchain",
                    supported_mime=["application/pdf"],
                    params={"parse_method": "pymupdf"}
                )
                print(f"✓ Created test parser: {parser.id}")
                
                # Test getting the parser back
                retrieved_parser = parser_service.get_parser_by_id(session, parser.id)
                if retrieved_parser:
                    print(f"✓ Retrieved parser: {retrieved_parser.name}")
                else:
                    print("✗ Failed to retrieve created parser")
                    return False
                
                return True
                
            except Exception as e:
                print(f"✗ Failed to create parser: {e}")
                return False
                
    except Exception as e:
        print(f"✗ Parser service test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Parser Service Test Suite ===\n")
    
    tests = [
        ("Import Test", test_imports),
        ("AutoRAG Availability", test_autorag_availability),
        ("Database Connection", test_database_connection),
        ("MinIO Connection", test_minio_connection),
        ("Parser Service Basic", test_parser_service_basic),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Parser service is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        
        # Provide troubleshooting tips
        print("\nTroubleshooting tips:")
        if not results.get("Database Connection", True):
            print("- Check if PostgreSQL is running and DATABASE_URL is correct")
        if not results.get("MinIO Connection", True):
            print("- Check if MinIO is running and credentials are correct")
        if not results.get("AutoRAG Availability", True):
            print("- Check if AutoRAG is installed and the path is correct")

if __name__ == "__main__":
    main() 