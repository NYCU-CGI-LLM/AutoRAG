import logging
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from io import BytesIO, StringIO
from pathlib import Path

from app.models.evaluation import BenchmarkDataset
from app.services.minio_service import MinIOService
from app.core.config import settings

logger = logging.getLogger(__name__)


class BenchmarkService:
    """Service for managing benchmark datasets for evaluation"""
    
    def __init__(self):
        self.minio_service = MinIOService()
        self.benchmark_bucket = settings.minio_benchmark_bucket
    
    async def upload_benchmark_dataset(
        self,
        name: str,
        qa_data: pd.DataFrame,
        corpus_data: pd.DataFrame,
        description: Optional[str] = None,
        domain: Optional[str] = None,
        language: str = "en",
        version: str = "1.0",
        evaluation_metrics: Optional[Dict[str, Any]] = None
    ) -> BenchmarkDataset:
        """
        Upload a benchmark dataset to MINIO and create database record
        
        Args:
            name: Dataset name
            qa_data: DataFrame with columns ['qid', 'query', 'retrieval_gt', 'generation_gt']
            corpus_data: DataFrame with columns ['doc_id', 'contents', 'metadata']
            description: Dataset description
            domain: Domain/topic
            language: Language code
            version: Dataset version
            evaluation_metrics: Default evaluation metrics configuration
        
        Returns:
            BenchmarkDataset: Created benchmark dataset record
        """
        try:
            # Validate required columns
            required_qa_columns = ['qid', 'query', 'retrieval_gt', 'generation_gt']
            required_corpus_columns = ['doc_id', 'contents']
            
            if not all(col in qa_data.columns for col in required_qa_columns):
                raise ValueError(f"QA data must contain columns: {required_qa_columns}")
            
            if not all(col in corpus_data.columns for col in required_corpus_columns):
                raise ValueError(f"Corpus data must contain columns: {required_corpus_columns}")
            
            # Create object keys
            dataset_id = uuid4()
            qa_object_key = f"benchmarks/{dataset_id}/qa_data.parquet"
            corpus_object_key = f"benchmarks/{dataset_id}/corpus_data.parquet"
            
            # Upload QA data
            qa_buffer = BytesIO()
            qa_data.to_parquet(qa_buffer, index=False)
            qa_buffer.seek(0)
            
            self.minio_service.client.put_object(
                bucket_name=self.benchmark_bucket,
                object_name=qa_object_key,
                data=qa_buffer,
                length=len(qa_buffer.getvalue()),
                content_type="application/octet-stream"
            )
            
            # Upload corpus data
            corpus_buffer = BytesIO()
            corpus_data.to_parquet(corpus_buffer, index=False)
            corpus_buffer.seek(0)
            
            self.minio_service.client.put_object(
                bucket_name=self.benchmark_bucket,
                object_name=corpus_object_key,
                data=corpus_buffer,
                length=len(corpus_buffer.getvalue()),
                content_type="application/octet-stream"
            )
            
            # Set default evaluation metrics if not provided
            if evaluation_metrics is None:
                evaluation_metrics = {
                    "retrieval": ["retrieval_f1", "retrieval_recall", "retrieval_precision"],
                    "generation": ["bleu", "rouge", "meteor"]
                }
            
            # Create database record
            benchmark_dataset = BenchmarkDataset(
                id=dataset_id,
                name=name,
                description=description,
                version=version,
                domain=domain,
                language=language,
                total_queries=len(qa_data),
                qa_data_object_key=qa_object_key,
                corpus_data_object_key=corpus_object_key,
                evaluation_metrics=evaluation_metrics
            )
            
            logger.info(f"Successfully uploaded benchmark dataset '{name}' with {len(qa_data)} queries")
            return benchmark_dataset
            
        except Exception as e:
            logger.error(f"Error uploading benchmark dataset '{name}': {e}")
            raise
    
    async def download_benchmark_dataset(
        self, 
        benchmark_dataset: BenchmarkDataset
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Download benchmark dataset from MINIO
        
        Args:
            benchmark_dataset: Benchmark dataset record
            
        Returns:
            tuple: (qa_data, corpus_data) DataFrames
        """
        try:
            logger.info(f"Starting download of benchmark dataset '{benchmark_dataset.name}'")
            
            # Download QA data
            logger.debug(f"Downloading QA data from: {benchmark_dataset.qa_data_object_key}")
            qa_response = self.minio_service.download_file(
                benchmark_dataset.qa_data_object_key,
                bucket_name=self.benchmark_bucket
            )
            qa_data_bytes = qa_response.read()
            qa_response.close()
            logger.debug(f"Downloaded QA data: {len(qa_data_bytes)} bytes")
            qa_data = pd.read_parquet(BytesIO(qa_data_bytes))
            logger.debug(f"Parsed QA data: {len(qa_data)} records")
            
            # Download corpus data
            logger.debug(f"Downloading corpus data from: {benchmark_dataset.corpus_data_object_key}")
            corpus_response = self.minio_service.download_file(
                benchmark_dataset.corpus_data_object_key,
                bucket_name=self.benchmark_bucket
            )
            corpus_data_bytes = corpus_response.read()
            corpus_response.close()
            logger.debug(f"Downloaded corpus data: {len(corpus_data_bytes)} bytes")
            corpus_data = pd.read_parquet(BytesIO(corpus_data_bytes))
            logger.debug(f"Parsed corpus data: {len(corpus_data)} records")
            
            logger.info(f"Successfully downloaded benchmark dataset '{benchmark_dataset.name}' - QA: {len(qa_data)} records, Corpus: {len(corpus_data)} records")
            return qa_data, corpus_data
            
        except Exception as e:
            logger.error(f"Error downloading benchmark dataset '{benchmark_dataset.name}': {e}")
            logger.error(f"QA object key: {benchmark_dataset.qa_data_object_key}")
            logger.error(f"Corpus object key: {benchmark_dataset.corpus_data_object_key}")
            raise
    
    async def create_sample_benchmarks(self) -> List[BenchmarkDataset]:
        """
        Create sample benchmark datasets for testing
        
        Returns:
            List[BenchmarkDataset]: List of created benchmark datasets
        """
        sample_datasets = []
        
        # Sample Dataset 1: Simple QA
        qa_data_1 = pd.DataFrame([
            {
                "qid": "q1",
                "query": "What is machine learning?",
                "retrieval_gt": [["doc1", "doc3"]],
                "generation_gt": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed."
            },
            {
                "qid": "q2", 
                "query": "How does natural language processing work?",
                "retrieval_gt": [["doc2", "doc4"]],
                "generation_gt": "Natural language processing uses computational techniques to analyze, understand, and generate human language in text and speech form."
            },
            {
                "qid": "q3",
                "query": "What are neural networks?",
                "retrieval_gt": [["doc1", "doc5"]],
                "generation_gt": "Neural networks are computing systems inspired by biological neural networks that learn to perform tasks by analyzing examples."
            }
        ])
        
        corpus_data_1 = pd.DataFrame([
            {
                "doc_id": "doc1",
                "contents": "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence (AI) based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention.",
                "metadata": {"topic": "machine_learning", "source": "textbook"}
            },
            {
                "doc_id": "doc2", 
                "contents": "Natural language processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language, in particular how to program computers to process and analyze large amounts of natural language data.",
                "metadata": {"topic": "nlp", "source": "textbook"}
            },
            {
                "doc_id": "doc3",
                "contents": "Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. AI research has been highly successful in developing effective techniques for solving a wide range of problems.",
                "metadata": {"topic": "ai", "source": "textbook"}
            },
            {
                "doc_id": "doc4",
                "contents": "Text processing and analysis involves various computational linguistics techniques including tokenization, part-of-speech tagging, named entity recognition, and semantic analysis to understand and extract meaning from text data.",
                "metadata": {"topic": "text_processing", "source": "textbook"}
            },
            {
                "doc_id": "doc5",
                "contents": "Deep learning neural networks consist of multiple layers of interconnected nodes that can learn complex patterns in data. These networks are particularly effective for tasks like image recognition, speech processing, and natural language understanding.",
                "metadata": {"topic": "deep_learning", "source": "textbook"}
            }
        ])
        
        dataset_1 = await self.upload_benchmark_dataset(
            name="AI Basics QA",
            qa_data=qa_data_1,
            corpus_data=corpus_data_1,
            description="Basic questions and answers about AI, ML, and NLP",
            domain="artificial_intelligence",
            language="en",
            version="1.0"
        )
        sample_datasets.append(dataset_1)
        
        # Sample Dataset 2: Technical FAQ
        qa_data_2 = pd.DataFrame([
            {
                "qid": "tech_q1",
                "query": "How to configure Docker containers?",
                "retrieval_gt": [["tech_doc1", "tech_doc2"]],
                "generation_gt": "Docker containers can be configured using Dockerfile instructions, environment variables, volume mounts, and network settings to define the application environment."
            },
            {
                "qid": "tech_q2",
                "query": "What is REST API?",
                "retrieval_gt": [["tech_doc3", "tech_doc4"]],
                "generation_gt": "REST API is an architectural style for designing web services that uses HTTP methods (GET, POST, PUT, DELETE) to perform operations on resources identified by URLs."
            }
        ])
        
        corpus_data_2 = pd.DataFrame([
            {
                "doc_id": "tech_doc1",
                "contents": "Docker is a platform that uses containerization technology to package applications and their dependencies into lightweight, portable containers. Configuration is done through Dockerfiles, docker-compose files, and runtime parameters.",
                "metadata": {"topic": "docker", "source": "documentation"}
            },
            {
                "doc_id": "tech_doc2",
                "contents": "Container orchestration involves managing multiple containers, their networking, storage, and scaling. Tools like Docker Compose and Kubernetes help automate container deployment and management.",
                "metadata": {"topic": "containers", "source": "documentation"}
            },
            {
                "doc_id": "tech_doc3",
                "contents": "Representational State Transfer (REST) is an architectural style that defines constraints for creating web services. RESTful APIs use standard HTTP methods and status codes to interact with resources.",
                "metadata": {"topic": "rest_api", "source": "documentation"}
            },
            {
                "doc_id": "tech_doc4",
                "contents": "Web APIs enable communication between different software applications over the internet. They define endpoints, request/response formats, authentication methods, and error handling procedures.",
                "metadata": {"topic": "web_apis", "source": "documentation"}
            }
        ])
        
        dataset_2 = await self.upload_benchmark_dataset(
            name="Tech FAQ",
            qa_data=qa_data_2,
            corpus_data=corpus_data_2,
            description="Technical FAQ for software development",
            domain="software_engineering",
            language="en",
            version="1.0"
        )
        sample_datasets.append(dataset_2)
        
        logger.info(f"Created {len(sample_datasets)} sample benchmark datasets")
        return sample_datasets 