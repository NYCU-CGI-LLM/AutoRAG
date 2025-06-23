#!/usr/bin/env python3
"""
Script to set up sample benchmark datasets
"""

import sys
import asyncio
from pathlib import Path

# Add the api directory to Python path
api_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(api_dir))

from app.services.benchmark_service import BenchmarkService
from app.core.database import SessionLocal
from app.core.minio_init import initialize_minio_buckets
from app.core.config import settings

async def main():
    """Set up sample benchmark datasets"""
    print("Setting up sample benchmark datasets...")
    
    try:
        # Initialize MinIO buckets first
        print("Initializing MinIO buckets...")
        buckets_created = initialize_minio_buckets(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket_names=[
                settings.minio_bucket_name,
                settings.minio_benchmark_bucket,
                settings.minio_evaluation_bucket,
                "rag-chunked-files",
                "rag-parsed-files",
                "rag-indexes"
            ],
            secure=settings.minio_secure
        )
        
        if not buckets_created:
            print("❌ Failed to create MinIO buckets")
            sys.exit(1)
        
        print("✅ MinIO buckets created successfully!")
        
        # Create benchmark service
        benchmark_service = BenchmarkService()
        
        # Create sample benchmarks
        print("Creating sample benchmark datasets...")
        sample_datasets = await benchmark_service.create_sample_benchmarks()
        
        # Save to database
        session = SessionLocal()
        for dataset in sample_datasets:
            session.add(dataset)
        
        session.commit()
        session.close()
        
        print(f"✅ Created {len(sample_datasets)} sample benchmark datasets!")
        
        for dataset in sample_datasets:
            print(f"  - {dataset.name}: {dataset.total_queries} queries ({dataset.domain})")
        
    except Exception as e:
        print(f"❌ Error setting up sample benchmarks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 