#!/usr/bin/env python3
"""
Test script for full evaluation workflow

This script tests the complete evaluation pipeline:
1. Submit an evaluation run
2. Monitor its progress
3. Get the final results
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
EVAL_ENDPOINT = f"{API_BASE_URL}/eval"


def get_available_data():
    """Get available datasets and retrievers"""
    print("🔍 Getting available datasets and retrievers...")
    
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/test/list-datasets")
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Found {len(data['benchmark_datasets'])} benchmark datasets")
        print(f"✅ Found {len(data['retriever_configs'])} retriever configs")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting available data: {e}")
        return None


def submit_evaluation(benchmark_id: str, retriever_id: str, evaluation_config: Dict[str, Any]) -> str:
    """Submit a full evaluation run"""
    print(f"\n🚀 Submitting evaluation run...")
    
    try:
        payload = {
            "name": "Test Full Evaluation Run",
            "retriever_config_id": retriever_id,
            "benchmark_dataset_id": benchmark_id,
            "evaluation_config": evaluation_config
        }
        
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
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Response text: {e.response.text}")
        return None


def monitor_evaluation(evaluation_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
    """Monitor evaluation progress until completion"""
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
                return data
            
            # Wait before next check
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error monitoring evaluation: {e}")
            time.sleep(5)  # Wait longer on error
    
    print(f"⏰ Evaluation monitoring timed out after {max_wait_time} seconds")
    return None


def get_evaluation_results(evaluation_id: str) -> Dict[str, Any]:
    """Get detailed evaluation results"""
    print(f"\n📋 Getting detailed results for evaluation {evaluation_id}...")
    
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/{evaluation_id}")
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ Retrieved evaluation results!")
        print(f"   Status: {data.get('status')}")
        print(f"   Execution Time: {data.get('execution_time', 0):.2f} seconds")
        print(f"   Total Queries: {data.get('total_queries', 0)}")
        print(f"   Processed Queries: {data.get('processed_queries', 0)}")
        
        # Print metrics if available
        if data.get('results'):
            print(f"\n📈 Evaluation Metrics:")
            for result in data['results']:
                print(f"   {result['metric_name']}: {result['value']:.4f}")
        
        # Print detailed results summary
        if data.get('detailed_results'):
            detailed = data['detailed_results']
            if 'retrieval_metrics' in detailed:
                print(f"\n🔍 Retrieval Metrics:")
                for metric, value in detailed['retrieval_metrics'].items():
                    print(f"   {metric}: {value:.4f}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting evaluation results: {e}")
        return None


def test_evaluation_list():
    """Test listing evaluations"""
    print(f"\n📋 Testing evaluation list...")
    
    try:
        response = requests.get(EVAL_ENDPOINT)
        response.raise_for_status()
        
        evaluations = response.json()
        print(f"✅ Found {len(evaluations)} evaluations in history")
        
        if evaluations:
            print(f"   Recent evaluations:")
            for eval_item in evaluations[:3]:  # Show first 3
                print(f"   - {eval_item['name']} ({eval_item['status']}) - {eval_item.get('overall_score', 'N/A')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing evaluations: {e}")
        return False


def main():
    """Main test function"""
    print("🧪 Testing Full Evaluation Workflow")
    print("=" * 50)
    
    # Step 1: Get available data
    available_data = get_available_data()
    if not available_data:
        print("❌ Cannot proceed without available data")
        return
    
    benchmark_datasets = available_data.get('benchmark_datasets', [])
    retriever_configs = available_data.get('retriever_configs', [])
    sample_config = available_data.get('sample_evaluation_config', {})
    
    if not benchmark_datasets or not retriever_configs:
        print("❌ Missing required datasets or retriever configs")
        return
    
    # Use first available dataset and retriever
    benchmark_id = benchmark_datasets[0]['id']
    retriever_id = retriever_configs[0]['id']
    
    print(f"\n🎯 Using for evaluation:")
    print(f"   Benchmark: {benchmark_datasets[0]['name']} ({benchmark_id})")
    print(f"   Retriever: {retriever_configs[0]['name']} ({retriever_id})")
    
    # Step 2: Submit evaluation
    evaluation_id = submit_evaluation(benchmark_id, retriever_id, sample_config)
    if not evaluation_id:
        print("❌ Failed to submit evaluation")
        return
    
    # Step 3: Monitor evaluation progress
    final_result = monitor_evaluation(evaluation_id)
    if not final_result:
        print("❌ Failed to monitor evaluation to completion")
        return
    
    # Step 4: Get detailed results
    detailed_results = get_evaluation_results(evaluation_id)
    if not detailed_results:
        print("❌ Failed to get detailed results")
        return
    
    # Step 5: Test evaluation listing
    test_evaluation_list()
    
    print(f"\n✅ Full evaluation workflow test completed!")
    print(f"   Evaluation ID: {evaluation_id}")
    print(f"   Final Status: {final_result.get('status', 'unknown')}")
    print("=" * 50)


if __name__ == "__main__":
    main() 