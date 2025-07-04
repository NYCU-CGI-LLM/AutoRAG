#!/usr/bin/env python3
"""
MinIO bucket initialization script for AutoRAG
This script can be imported and used in your API server startup
"""

import time
import logging
from minio import Minio
from minio.error import S3Error
import requests

# Configure logging
logger = logging.getLogger(__name__)

def wait_for_minio(endpoint: str, max_retries: int = 5, retry_interval: int = 5) -> bool:
    """
    Wait for MinIO to be ready by checking health endpoint
    
    Args:
        endpoint: MinIO endpoint (e.g., 'localhost:9000')
        max_retries: Maximum number of retry attempts
        retry_interval: Seconds to wait between retries
    
    Returns:
        bool: True if MinIO is ready, False if timeout
    """
    health_url = f"http://{endpoint}/minio/health/live"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                logger.info("MinIO is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        logger.info(f"MinIO not ready yet. Attempt {attempt + 1}/{max_retries}. Waiting {retry_interval}s...")
        time.sleep(retry_interval)
    
    logger.error("MinIO failed to become ready within timeout period")
    return False

def initialize_minio_buckets(
    endpoint: str = "localhost:9000",
    access_key: str = "adminadmin", 
    secret_key: str = "adminadmin",
    bucket_names: list = None,
    secure: bool = False
) -> bool:
    """
    Initialize multiple MinIO buckets for AutoRAG
    
    Args:
        endpoint: MinIO endpoint
        access_key: MinIO access key
        secret_key: MinIO secret key
        bucket_names: List of bucket names to create
        secure: Whether to use HTTPS
    
    Returns:
        bool: True if all buckets created successfully, False otherwise
    """
    if bucket_names is None:
        bucket_names = ["rag-files", "rag-chunked-files", "rag-parsed-files"]
    
    try:
        # Wait for MinIO to be ready
        if not wait_for_minio(endpoint):
            return False
        
        # Create MinIO client
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # Create each bucket
        for bucket_name in bucket_names:
            try:
                # Check if bucket already exists
                if client.bucket_exists(bucket_name):
                    logger.info(f"Bucket '{bucket_name}' already exists")
                    continue
                
                # Create bucket
                client.make_bucket(bucket_name)
                logger.info(f"Successfully created bucket '{bucket_name}'")
                
                # Set bucket policy to public (optional)
                # Note: For production, you might want more restrictive policies
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                        }
                    ]
                }
                
                import json
                client.set_bucket_policy(bucket_name, json.dumps(policy))
                logger.info(f"Set public read policy for bucket '{bucket_name}'")
                
            except S3Error as e:
                logger.error(f"MinIO S3 error for bucket '{bucket_name}': {e}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error creating bucket '{bucket_name}': {e}")
                return False
        
        logger.info("All MinIO buckets initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error initializing MinIO: {e}")
        return False

# Keep the old function for backward compatibility
def initialize_minio_bucket(
    endpoint: str = "localhost:9000",
    access_key: str = "adminadmin", 
    secret_key: str = "adminadmin",
    bucket_name: str = "autorag-files",
    secure: bool = False
) -> bool:
    """
    Initialize single MinIO bucket for AutoRAG (backward compatibility)
    
    Args:
        endpoint: MinIO endpoint
        access_key: MinIO access key
        secret_key: MinIO secret key
        bucket_name: Name of bucket to create
        secure: Whether to use HTTPS
    
    Returns:
        bool: True if successful, False otherwise
    """
    return initialize_minio_buckets(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket_names=[bucket_name],
        secure=secure
    )

def main():
    """Main function for standalone execution"""
    success = initialize_minio_buckets()
    if success:
        logger.info("MinIO initialization completed successfully!")
    else:
        logger.error("MinIO initialization failed!")
        exit(1)

if __name__ == "__main__":
    main() 