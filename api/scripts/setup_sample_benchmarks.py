#!/usr/bin/env python3
"""Script to set up sample benchmark datasets"""

import sys
import asyncio
import logging
from pathlib import Path

# Add the parent directory (api/) to Python path for imports
api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from app.services.benchmark_service import BenchmarkService
from app.core.database import SessionLocal
from app.core.minio_init import initialize_minio_buckets
from app.core.config import settings
from dataset_loaders import DATASET_LOADERS, load_benchmark_dataset
from app.models.evaluation import BenchmarkDataset
import pandas as pd
import tempfile
import os
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Set up sample benchmark datasets"""
    logger.info("Starting sample benchmark datasets setup...")
    
    try:
        # Initialize MinIO buckets first
        logger.info("Initializing MinIO buckets...")
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
            logger.error("Failed to create MinIO buckets")
            sys.exit(1)
        
        logger.info("MinIO buckets created successfully!")
        
        # Create benchmark service
        benchmark_service = BenchmarkService()
        
        # Create datasets using real dataset loaders
        logger.info("Creating benchmark datasets from real datasets...")
        datasets_to_create = [
            ('triviaqa', 'TriviaQA', 'General Knowledge'),
            ('msmarco', 'MS MARCO', 'Information Retrieval'),
            ('hotpotqa', 'HotpotQA', 'Multi-hop Reasoning'),
            ('eli5', 'ELI5', 'Educational Explanations'),
        ]
        
        session = SessionLocal()
        created_datasets = []
        
        try:
            for dataset_key, display_name, domain in datasets_to_create:
                logger.info(f"Creating {display_name} dataset...")
                
                # Create temporary directory for dataset files
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Load dataset (will fallback to mock data if HF fails)
                    success, error = load_benchmark_dataset(dataset_key, temp_dir)
                    
                    if not success:
                        logger.error(f"Failed to load {dataset_key}: {error}")
                        continue
                    
                    # Read the generated files
                    corpus_path = os.path.join(temp_dir, "corpus.parquet")
                    qa_path = os.path.join(temp_dir, "qa.parquet")
                    
                    if not os.path.exists(corpus_path) or not os.path.exists(qa_path):
                        logger.error(f"Missing required files for {dataset_key}")
                        continue
                    
                    # Read data to get metadata
                    try:
                        corpus_df = pd.read_parquet(corpus_path)
                        qa_df = pd.read_parquet(qa_path)
                        
                        total_docs = len(corpus_df)
                        total_queries = len(qa_df)
                        
                        logger.info(f"  - Loaded {total_docs} documents and {total_queries} queries")
                        
                    except Exception as read_error:
                        logger.error(f"Failed to read dataset files for {dataset_key}: {read_error}")
                        continue
                    
                    # Upload to MinIO using BenchmarkService
                    try:
                        benchmark_dataset = await benchmark_service.upload_benchmark_dataset(
                            name=display_name,
                            description=f"Real {display_name} benchmark dataset for {domain} evaluation",
                            domain=domain,
                            qa_data=qa_df,
                            corpus_data=corpus_df
                        )
                        
                        # Add to database session before committing
                        session.add(benchmark_dataset)
                        created_datasets.append(benchmark_dataset)
                        logger.info(f"  - Successfully uploaded {display_name} to MinIO and database")
                        
                    except Exception as upload_error:
                        logger.error(f"Failed to upload {dataset_key}: {upload_error}")
                        continue
            
            session.commit()
            logger.info(f"Successfully created {len(created_datasets)} benchmark datasets!")
            
            for dataset in created_datasets:
                logger.info(f"  - {dataset.name}: {dataset.total_queries} queries ({dataset.domain})")
                
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            session.rollback()
            raise
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error setting up sample benchmarks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 
