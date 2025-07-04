#!/usr/bin/env python3
"""
Quick test script to verify the MinIO download fix
"""

import requests
import json

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
EVAL_ENDPOINT = f"{API_BASE_URL}/eval"

def test_config_only():
    """Test config generation only (should work)"""
    print("🧪 Testing config generation only...")
    
    sample_config = {
        "embedding_model": "openai_embed_3_large",
        "retrieval_strategy": {
            "metrics": ["retrieval_f1", "retrieval_recall"],
            "top_k": 10
        },
        "generation_strategy": {
            "metrics": [
                {"metric_name": "bleu"},
                {"metric_name": "rouge"}
            ]
        },
        "generator_config": {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 512,
            "batch": 16
        }
    }
    
    try:
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/config-only",
            json=sample_config
        )
        response.raise_for_status()
        
        data = response.json()
        print("✅ Config generation successful!")
        print(f"   Embedding Model: {data['config_info']['embedding_model']}")
        print(f"   VectorDB Path: {data['config_info']['vectordb_path']}")
        print(f"   Node Count: {data['config_info']['node_count']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Config generation failed: {e}")
        return False

def test_download_and_config():
    """Test download and config generation (the fixed functionality)"""
    print("\n🧪 Testing download and config generation...")
    
    # First get available datasets
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/test/list-datasets")
        response.raise_for_status()
        datasets_info = response.json()
        
        if not datasets_info.get('benchmark_datasets'):
            print("❌ No benchmark datasets available")
            return False
        
        # Use first available dataset
        benchmark_id = datasets_info['benchmark_datasets'][0]['id']
        sample_config = datasets_info['sample_evaluation_config']
        
        print(f"   Using benchmark: {datasets_info['benchmark_datasets'][0]['name']}")
        
        # Test the download and config generation
        payload = {
            "benchmark_dataset_id": benchmark_id,
            "evaluation_config": sample_config
        }
        
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/download-and-config",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        print("✅ Download and config generation successful!")
        print(f"   QA Records: {data['data_info']['qa_records']}")
        print(f"   Corpus Records: {data['data_info']['corpus_records']}")
        print(f"   VectorDB Path: {data['config_info']['vectordb_path']}")
        print(f"   Config Generated: {data['config_info']['embedding_model']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Download and config generation failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {e.response.text}")
        return False

def test_save_files_to_disk():
    """Test saving files to disk for inspection"""
    print("\n🧪 Testing save files to disk...")
    
    # First get available datasets
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/test/list-datasets")
        response.raise_for_status()
        datasets_info = response.json()
        
        if not datasets_info.get('benchmark_datasets'):
            print("❌ No benchmark datasets available")
            return False
        
        # Use first available dataset
        benchmark_id = datasets_info['benchmark_datasets'][0]['id']
        sample_config = datasets_info['sample_evaluation_config']
        
        print(f"   Using benchmark: {datasets_info['benchmark_datasets'][0]['name']}")
        
        # Test saving files to disk
        payload = {
            "benchmark_dataset_id": benchmark_id,
            "evaluation_config": sample_config
        }
        
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/save-files",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        print("✅ Files saved to disk successfully!")
        print(f"   Temp Directory: {data['file_paths']['temp_directory']}")
        print(f"   VectorDB Path: {data['file_paths']['vectordb_path']}")
        print(f"   QA Data: {data['file_paths']['qa_data']}")
        print(f"   Corpus Data: {data['file_paths']['corpus_data']}")
        print(f"   Config File: {data['file_paths']['config_file']}")
        print(f"   Summary File: {data['file_paths']['summary_file']}")
        print(f"\n🧹 To clean up later: {data['cleanup_command']}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Save files to disk failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {e.response.text}")
        return False

def main():
    print("🔧 Testing MinIO Download Fix")
    print("=" * 40)
    
    # Test 1: Config generation only (should always work)
    config_success = test_config_only()
    
    if not config_success:
        print("❌ Basic config test failed - check API server")
        return
    
    # Test 2: Download and config generation (the fixed functionality)
    download_success = test_download_and_config()
    
    if download_success:
        print("\n✅ All tests passed! MinIO download fix is working.")
    else:
        print("\n❌ Download test failed - check MinIO connection and data.")
    
    # Test 3: Save files to disk
    save_files_success = test_save_files_to_disk()
    
    if save_files_success:
        print("\n✅ All tests passed! Files saved to disk successfully.")
    else:
        print("\n❌ Files save test failed - check MinIO connection and data.")
    
    print("=" * 40)

if __name__ == "__main__":
    main() 