#!/usr/bin/env python3
"""
Simple evaluation test script

This script tests the new simplified evaluation API that only requires
benchmark_dataset_id and evaluation_config.
"""

import requests
import json
import time

# Configuration
API_BASE_URL = "http://localhost:8000"
EVAL_ENDPOINT = f"{API_BASE_URL}/eval"


def test_simplified_evaluation():
    """Test the simplified evaluation API"""
    print("🧪 Testing Simplified Evaluation API")
    print("=" * 50)
    
    # First, get benchmark datasets
    print("🔍 Getting benchmark datasets...")
    
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/benchmarks/")
        response.raise_for_status()
        
        datasets = response.json()
        print(f"✅ Found {len(datasets)} benchmark datasets")
        
        if not datasets:
            print("❌ No benchmark datasets found")
            return
        
        # Use first dataset
        dataset = datasets[0]
        print(f"   Using dataset: {dataset['name']} (ID: {dataset['id']})")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting benchmark datasets: {e}")
        return
    
    # Prepare evaluation config
    evaluation_config = {
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
    
    # Submit evaluation with new simplified format
    print(f"\n🚀 Submitting evaluation with new API...")
    
    try:
        payload = {
            "name": "Simplified Test Evaluation",
            "benchmark_dataset_id": dataset['id'],
            "evaluation_config": evaluation_config
        }
        
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(EVAL_ENDPOINT, json=payload)
        response.raise_for_status()
        
        data = response.json()
        evaluation_id = data['id']
        
        print(f"✅ Evaluation submitted successfully!")
        print(f"   Evaluation ID: {evaluation_id}")
        print(f"   Name: {data['name']}")
        print(f"   Status: {data['status']}")
        print(f"   Progress: {data.get('progress', 0)}%")
        
        return evaluation_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error submitting evaluation: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Response text: {e.response.text}")
        return None


def monitor_evaluation(evaluation_id: str, max_wait_time: int = 60):
    """Monitor evaluation progress"""
    print(f"\n📊 Monitoring evaluation {evaluation_id}...")
    
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(f"{EVAL_ENDPOINT}/{evaluation_id}")
            response.raise_for_status()
            
            data = response.json()
            status = data.get('status', 'unknown')
            progress = data.get('progress', 0)
            
            # Only print if progress changed
            if progress != last_progress:
                print(f"   Status: {status}, Progress: {progress}%")
                last_progress = progress
            
            # Check if completed
            if status in ['success', 'failure', 'completed']:
                print(f"\n✅ Evaluation completed with status: {status}")
                if status == 'failure':
                    print(f"   Error message: {data.get('message', 'No error message')}")
                
                # Print results if available
                if data.get('results'):
                    print(f"\n📈 Results:")
                    for result in data['results']:
                        print(f"   {result['metric_name']}: {result['value']:.4f}")
                
                return data
            
            # Wait before next check
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error monitoring evaluation: {e}")
            time.sleep(5)
    
    print(f"⏰ Evaluation monitoring timed out after {max_wait_time} seconds")
    return None


def test_config_only():
    """Test config generation only"""
    print(f"\n🔍 Testing config generation only...")
    
    evaluation_config = {
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
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/config-only",
            json=evaluation_config
        )
        response.raise_for_status()
        
        data = response.json()
        print("✅ Config generation works!")
        print(f"   Embedding Model: {data['config_info']['embedding_model']}")
        print(f"   VectorDB Path: {data['config_info']['vectordb_path']}")
        print(f"   Retrieval Modules: {data['config_info']['retrieval_modules']}")
        print(f"   Generation Modules: {data['config_info']['generation_modules']}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Config generation failed: {e}")
        return False


def main():
    """Main test function"""
    # Test config generation first
    config_works = test_config_only()
    
    if not config_works:
        print("\n❌ Config generation doesn't work, cannot proceed")
        return
    
    # Test simplified evaluation submission
    evaluation_id = test_simplified_evaluation()
    
    if not evaluation_id:
        print("\n❌ Evaluation submission failed")
        return
    
    # Monitor evaluation progress
    final_result = monitor_evaluation(evaluation_id)
    
    print(f"\n{'='*50}")
    if final_result:
        print("✅ Simplified evaluation API is working!")
        print(f"   Final Status: {final_result.get('status', 'unknown')}")
        if final_result.get('execution_time'):
            print(f"   Execution Time: {final_result['execution_time']:.2f} seconds")
    else:
        print("⚠️ Evaluation monitoring failed or timed out")
    print(f"{'='*50}")


if __name__ == "__main__":
    main() 