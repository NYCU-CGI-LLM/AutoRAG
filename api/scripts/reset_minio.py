#!/usr/bin/env python3
"""Reset MinIO buckets script - deletes all buckets and recreates them"""

import sys
import logging
from pathlib import Path

# Add the parent directory (api/) to Python path for imports
api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from minio import Minio
from minio.error import S3Error
from minio.deleteobjects import DeleteObject
from app.core.config import settings
from app.core.minio_init import initialize_minio_buckets, wait_for_minio
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def delete_all_buckets(client: Minio) -> bool:
    """
    Delete all existing buckets and their contents
    
    Args:
        client: MinIO client instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get list of all buckets
        buckets = client.list_buckets()
        
        if not buckets:
            logger.info("No buckets found to delete")
            return True
            
        logger.info(f"Found {len(buckets)} buckets to delete")
        
        for bucket in buckets:
            bucket_name = bucket.name
            logger.info(f"Deleting bucket: {bucket_name}")
            
            try:
                # First, delete all objects in the bucket
                objects = client.list_objects(bucket_name, recursive=True)
                delete_objects = [DeleteObject(obj.object_name) for obj in objects]
                
                if delete_objects:
                    logger.info(f"  - Deleting {len(delete_objects)} objects from {bucket_name}")
                    # Delete objects in batches
                    errors = client.remove_objects(bucket_name, delete_objects)
                    for error in errors:
                        logger.error(f"    Error deleting object {error.object_name}: {error}")
                else:
                    logger.info(f"  - Bucket {bucket_name} is empty")
                
                # Then delete the bucket itself
                client.remove_bucket(bucket_name)
                logger.info(f"  ✓ Successfully deleted bucket: {bucket_name}")
                
            except S3Error as e:
                logger.error(f"  ✗ Error deleting bucket {bucket_name}: {e}")
                return False
            except Exception as e:
                logger.error(f"  ✗ Unexpected error deleting bucket {bucket_name}: {e}")
                return False
        
        logger.info("All buckets deleted successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error getting bucket list: {e}")
        return False

def get_all_bucket_names() -> list:
    """
    Get list of all bucket names that should be created
    
    Returns:
        list: List of bucket names
    """
    return [
        settings.minio_bucket_name,           # autorag-files
        settings.minio_benchmark_bucket,      # rag-benchmarks  
        settings.minio_evaluation_bucket,     # rag-evaluations
        "rag-chunked-files",                  # chunked files
        "rag-parsed-files",                   # parsed files
        "rag-indexes",                        # index files  
    ]

def reset_minio():
    """
    Complete MinIO reset: delete all buckets and recreate them
    """
    logger.info("Starting MinIO reset process...")
    logger.info("=" * 60)
    
    try:
        # Wait for MinIO to be ready
        logger.info("Checking MinIO connectivity...")
        if not wait_for_minio(settings.minio_endpoint):
            logger.error("MinIO is not accessible. Please ensure MinIO is running.")
            return False
        
        # Create MinIO client
        client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        
        # Step 1: Delete all existing buckets
        logger.info("\n🗑️  STEP 1: Deleting all existing buckets...")
        if not delete_all_buckets(client):
            logger.error("Failed to delete existing buckets")
            return False
        
        # Step 2: Recreate all necessary buckets
        logger.info("\n🏗️  STEP 2: Creating all necessary buckets...")
        bucket_names = get_all_bucket_names()
        
        success = initialize_minio_buckets(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket_names=bucket_names,
            secure=settings.minio_secure
        )
        
        if not success:
            logger.error("Failed to recreate buckets")
            return False
        
        # Step 3: Verify all buckets were created
        logger.info("\n✅ STEP 3: Verifying bucket creation...")
        buckets = client.list_buckets()
        created_bucket_names = [bucket.name for bucket in buckets]
        
        logger.info(f"Successfully created {len(created_bucket_names)} buckets:")
        for bucket_name in sorted(created_bucket_names):
            logger.info(f"  ✓ {bucket_name}")
        
        # Check if all expected buckets were created
        missing_buckets = set(bucket_names) - set(created_bucket_names)
        if missing_buckets:
            logger.warning(f"Missing buckets: {list(missing_buckets)}")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 MinIO reset completed successfully!")
        logger.info("\nBucket descriptions:")
        logger.info("  • autorag-files     - Main file storage")
        logger.info("  • rag-benchmarks    - Evaluation benchmark datasets")
        logger.info("  • rag-evaluations   - Evaluation results and reports")
        logger.info("  • rag-chunked-files - Document chunks after chunking")
        logger.info("  • rag-parsed-files  - Parsed document content")
        logger.info("  • rag-indexes       - Vector and search indexes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during MinIO reset: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    print("🚨 WARNING: This will DELETE ALL MinIO buckets and their contents!")
    print("This action cannot be undone.")
    print()
    
    # Ask for confirmation
    response = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("Operation cancelled.")
        sys.exit(0)
    
    print("\nProceeding with MinIO reset...")
    
    success = reset_minio()
    
    if success:
        print("\n✅ MinIO reset completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ MinIO reset failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 