#!/usr/bin/env python3
"""
Test the embedding_batch fix for token limits
"""

import requests
import json
import time

def test_batch_fix():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Embedding Batch Fix")
    print("=" * 40)
    
    # Get benchmark datasets
    print("🔍 Getting benchmark datasets...")
    response = requests.get(f"{base_url}/benchmark-datasets")
    if response.status_code != 200:
        print(f"❌ Failed to get datasets: {response.status_code}")
        return
    
    datasets = response.json()
    if not datasets:
        print("❌ No datasets found")
        return
        
    dataset = datasets[0]  # Use TriviaQA
    print(f"✅ Using dataset: {dataset['name']} (ID: {dataset['id']})")
    print(f"   Total queries: {dataset['total_queries']}")
    
    # Create evaluation with small batch configuration
    eval_config = {
        "name": "Batch Fix Test",
        "benchmark_dataset_id": dataset["id"],
        "evaluation_config": {
            "embedding_model": "openai_embed_3_large",
            "retrieval_strategy": {
                "metrics": ["retrieval_f1", "retrieval_recall"],
                "top_k": 3  # Small top_k
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
                "max_tokens": 256,  # Small max_tokens
                "batch": 1  # Very small batch for generation
            }
        }
    }
    
    print(f"\n🚀 Submitting evaluation with batch fix...")
    print(f"   - VectorDB embedding_batch: 10 (hardcoded in service)")
    print(f"   - Retrieval embedding_batch: 10 (hardcoded in service)")
    print(f"   - Generation batch: 1")
    print(f"   - Top_k: 3")
    
    # Submit evaluation
    response = requests.post(f"{base_url}/evaluations", json=eval_config)
    if response.status_code != 200:
        print(f"❌ Failed to submit evaluation: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    evaluation = response.json()
    eval_id = evaluation["id"]
    print(f"✅ Evaluation submitted successfully!")
    print(f"   Evaluation ID: {eval_id}")
    print(f"   Status: {evaluation['status']}")
    
    # Monitor evaluation
    print(f"\n📊 Monitoring evaluation {eval_id}...")
    start_time = time.time()
    timeout = 600  # 10 minutes timeout for large dataset
    
    last_status = None
    last_progress = None
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{base_url}/evaluations/{eval_id}")
        if response.status_code == 200:
            evaluation = response.json()
            status = evaluation["status"]
            progress = evaluation.get("progress", 0)
            message = evaluation.get("message", "")
            
            # Only print if status or progress changed
            if status != last_status or progress != last_progress:
                print(f"   Status: {status}, Progress: {progress}%")
                if message and "Error code: 400" not in message:
                    print(f"   Message: {message[:100]}...")
                last_status = status
                last_progress = progress
            
            if status in ["completed", "failure"]:
                if message:
                    print(f"   Final Message: {message}")
                break
                
        elif response.status_code == 404:
            print(f"   ❌ Evaluation not found")
            break
        else:
            print(f"   ❌ Error checking status: {response.status_code}")
            break
            
        time.sleep(15)  # Check every 15 seconds
    
    if time.time() - start_time >= timeout:
        print("⏰ Evaluation monitoring timed out")
        return
    
    # Final status check
    response = requests.get(f"{base_url}/evaluations/{eval_id}")
    if response.status_code == 200:
        evaluation = response.json()
        print(f"\n✅ Evaluation completed!")
        print(f"   Final Status: {evaluation['status']}")
        print(f"   Progress: {evaluation.get('progress', 0)}%")
        print(f"   Execution Time: {evaluation.get('execution_time', 0):.2f} seconds")
        
        if evaluation['status'] == 'completed':
            print(f"   🎉 SUCCESS: Batch fix worked!")
            if evaluation.get('results'):
                results = evaluation['results']
                print(f"   Results Summary: {json.dumps(results, indent=2)}")
        else:
            print(f"   ❌ FAILURE: {evaluation.get('message', 'Unknown error')}")
            
        print(f"\n=" * 50)
        return evaluation['status'] == 'completed'
    else:
        print(f"❌ Failed to get final status: {response.status_code}")
        return False

if __name__ == "__main__":
    success = test_batch_fix()
    if success:
        print("✅ Batch fix test PASSED!")
    else:
        print("❌ Batch fix test FAILED!") 