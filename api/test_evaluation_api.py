#!/usr/bin/env python3
"""
Test script for evaluation API endpoints

This script helps test the evaluation service functionality:
1. List available datasets and retriever configs
2. Test data download and config generation
3. Submit a full evaluation run

Usage:
    python test_evaluation_api.py
"""

import requests
import json
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
EVAL_ENDPOINT = f"{API_BASE_URL}/eval"


def test_list_datasets() -> Dict[str, Any]:
    """Test listing available datasets and retrievers"""
    print("🔍 Testing: List available datasets and retrievers...")
    
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/test/list-datasets")
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ Found {len(data['benchmark_datasets'])} benchmark datasets")
        print(f"✅ Found {len(data['retriever_configs'])} retriever configs")
        
        if data['benchmark_datasets']:
            print("\n📊 Available Benchmark Datasets:")
            for dataset in data['benchmark_datasets']:
                print(f"  - ID: {dataset['id']}")
                print(f"    Name: {dataset['name']}")
                print(f"    Description: {dataset['description']}")
                print()
        
        if data['retriever_configs']:
            print("🔧 Available Retriever Configs:")
            for retriever in data['retriever_configs']:
                print(f"  - ID: {retriever['id']}")
                print(f"    Name: {retriever['name']}")
                print(f"    Type: {retriever['config_type']}")
                print()
        
        print("📝 Sample Evaluation Config:")
        print(json.dumps(data['sample_evaluation_config'], indent=2))
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing datasets: {e}")
        return {}


def test_config_generation_only(evaluation_config: Dict[str, Any]) -> Dict[str, Any]:
    """Test config generation only (no data download)"""
    print(f"\n⚙️ Testing: Config generation only...")
    
    try:
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/config-only",
            json=evaluation_config
        )
        response.raise_for_status()
        
        data = response.json()
        
        print("✅ Config generation successful!")
        print(f"   Embedding Model: {data['config_info']['embedding_model']}")
        print(f"   Collection Name: {data['config_info']['collection_name']}")
        print(f"   Node Count: {data['config_info']['node_count']}")
        print(f"   Retrieval Modules: {data['config_info']['retrieval_modules']}")
        print(f"   Generation Modules: {data['config_info']['generation_modules']}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing config generation: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {e.response.text}")
        return {}


def test_download_and_config(
    benchmark_id: str,
    evaluation_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Test data download and config generation"""
    print(f"\n🧪 Testing: Download data and generate config...")
    print(f"   Benchmark ID: {benchmark_id}")
    
    try:
        payload = {
            "benchmark_dataset_id": benchmark_id,
            "evaluation_config": evaluation_config
        }
        
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/download-and-config",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        
        print("✅ Data download and config generation successful!")
        print(f"   QA Records: {data['data_info']['qa_records']}")
        print(f"   Corpus Records: {data['data_info']['corpus_records']}")
        print(f"   QA Columns: {data['data_info']['qa_columns']}")
        print(f"   Corpus Columns: {data['data_info']['corpus_columns']}")
        
        print(f"\n⚙️ Generated Config Info:")
        print(f"   Embedding Model: {data['config_info']['embedding_model']}")
        print(f"   Collection Name: {data['config_info']['collection_name']}")
        print(f"   Node Count: {data['config_info']['node_count']}")
        print(f"   Retrieval Modules: {data['config_info']['retrieval_modules']}")
        
        print(f"\n📄 Full Generated Config:")
        print(json.dumps(data['generated_config'], indent=2))
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing download and config: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {e.response.text}")
        return {}


def test_submit_evaluation(
    retriever_id: str,
    benchmark_id: str,
    evaluation_config: Dict[str, Any],
    name: str = None
) -> Dict[str, Any]:
    """Test submitting a full evaluation run"""
    print(f"\n🚀 Testing: Submit full evaluation run...")
    
    try:
        payload = {
            "name": name or "Test Evaluation Run",
            "retriever_config_id": retriever_id,
            "benchmark_dataset_id": benchmark_id,
            "evaluation_config": evaluation_config
        }
        
        response = requests.post(EVAL_ENDPOINT, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        print("✅ Evaluation run submitted successfully!")
        print(f"   Evaluation ID: {data['id']}")
        print(f"   Name: {data['name']}")
        print(f"   Status: {data['status']}")
        print(f"   Progress: {data.get('progress', 0)}%")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error submitting evaluation: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {e.response.text}")
        return {}


def main():
    """Main test function"""
    print("🧪 Starting Evaluation API Tests")
    print("=" * 50)
    
    # Step 1: List available datasets and retrievers
    datasets_info = test_list_datasets()
    
    if not datasets_info:
        print("❌ Cannot proceed without dataset information")
        return
    
    # Check if we have data to test with
    benchmark_datasets = datasets_info.get('benchmark_datasets', [])
    retriever_configs = datasets_info.get('retriever_configs', [])
    sample_config = datasets_info.get('sample_evaluation_config', {})
    
    if not benchmark_datasets:
        print("❌ No benchmark datasets available for testing")
        return
    
    if not retriever_configs:
        print("❌ No retriever configs available for testing")
        return
    
    # Use first available dataset and retriever for testing
    benchmark_id = benchmark_datasets[0]['id']
    retriever_id = retriever_configs[0]['id']
    
    print(f"\n🎯 Using for testing:")
    print(f"   Benchmark: {benchmark_datasets[0]['name']} ({benchmark_id})")
    print(f"   Retriever: {retriever_configs[0]['name']} ({retriever_id})")
    
    # Step 2: Test config generation only (fast test)
    print("\n" + "="*30 + " STEP 2: CONFIG GENERATION " + "="*30)
    config_only_result = test_config_generation_only(sample_config)
    
    if not config_only_result:
        print("❌ Config generation test failed")
        return
    
    # Step 3: Test data download and config generation (full test)
    print("\n" + "="*30 + " STEP 3: DATA DOWNLOAD + CONFIG " + "="*30)
    config_result = test_download_and_config(
        benchmark_id=benchmark_id,
        evaluation_config=sample_config
    )
    
    if not config_result:
        print("❌ Data download and config generation test failed")
        return
    
    # Step 4: Optionally test full evaluation submission
    print(f"\n❓ Would you like to submit a full evaluation run? (y/N): ", end="")
    try:
        user_input = input().strip().lower()
        if user_input in ['y', 'yes']:
            test_submit_evaluation(
                retriever_id=retriever_id,
                benchmark_id=benchmark_id,
                evaluation_config=sample_config,
                name="API Test Evaluation"
            )
        else:
            print("⏭️  Skipping full evaluation submission")
    except KeyboardInterrupt:
        print("\n⏭️  Skipping full evaluation submission")
    
    print(f"\n✅ All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    main() 