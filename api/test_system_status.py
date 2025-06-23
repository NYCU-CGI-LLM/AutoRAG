#!/usr/bin/env python3
"""
System status check script

This script checks if all required components are available for evaluation:
1. Benchmark datasets
2. Retriever configurations  
3. API endpoints
"""

import requests
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
EVAL_ENDPOINT = f"{API_BASE_URL}/eval"


def check_api_health():
    """Check if API is responding"""
    print("🔍 Checking API health...")
    
    try:
        # Try the root endpoint
        response = requests.get(f"http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ API is responding")
            return True
        else:
            print(f"⚠️ API responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API is not responding: {e}")
        return False


def check_benchmark_datasets():
    """Check available benchmark datasets"""
    print("\n🔍 Checking benchmark datasets...")
    
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/benchmarks/")
        response.raise_for_status()
        
        datasets = response.json()
        print(f"✅ Found {len(datasets)} benchmark datasets")
        
        if datasets:
            for dataset in datasets:
                print(f"   - {dataset['name']} ({dataset.get('total_queries', 'N/A')} queries)")
        else:
            print("⚠️ No benchmark datasets found")
            return False
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking benchmark datasets: {e}")
        return False


def check_retriever_configs():
    """Check available retriever configurations"""
    print("\n🔍 Checking retriever configurations...")
    
    try:
        response = requests.get(f"{EVAL_ENDPOINT}/test/list-datasets")
        response.raise_for_status()
        
        data = response.json()
        retrievers = data.get('retriever_configs', [])
        
        print(f"✅ Found {len(retrievers)} retriever configurations")
        
        if retrievers:
            for retriever in retrievers:
                print(f"   - {retriever['name']} ({retriever['config_type']})")
        else:
            print("⚠️ No retriever configurations found")
            return False
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking retriever configurations: {e}")
        return False


def create_sample_data():
    """Create sample benchmark datasets and retriever configs"""
    print("\n🔧 Creating sample data...")
    
    # Create sample benchmark datasets
    try:
        print("   Creating sample benchmark datasets...")
        response = requests.post(f"{EVAL_ENDPOINT}/benchmarks/sample")
        if response.status_code in [200, 201]:
            datasets = response.json()
            print(f"   ✅ Created {len(datasets)} sample benchmark datasets")
        else:
            print(f"   ⚠️ Sample datasets creation returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error creating sample datasets: {e}")
    
    # Note: Retriever configs would need to be created through a different endpoint
    # For now, we'll just report on what's needed
    print("   ℹ️ Retriever configurations need to be created separately")
    print("   ℹ️ You may need to create retriever configs through the retriever API")


def test_config_generation():
    """Test basic config generation"""
    print("\n🔍 Testing config generation...")
    
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
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(
            f"{EVAL_ENDPOINT}/test/config-only",
            json=sample_config
        )
        response.raise_for_status()
        
        data = response.json()
        print("✅ Config generation works")
        print(f"   Embedding Model: {data['config_info']['embedding_model']}")
        print(f"   VectorDB Path: {data['config_info']['vectordb_path']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Config generation failed: {e}")
        return False


def main():
    """Main status check function"""
    print("🧪 System Status Check")
    print("=" * 40)
    
    all_good = True
    
    # Check API health
    if not check_api_health():
        all_good = False
    
    # Check benchmark datasets
    has_datasets = check_benchmark_datasets()
    if not has_datasets:
        all_good = False
    
    # Check retriever configs
    has_retrievers = check_retriever_configs()
    if not has_retrievers:
        all_good = False
    
    # Test config generation
    if not test_config_generation():
        all_good = False
    
    # If missing data, offer to create samples
    if not has_datasets or not has_retrievers:
        print(f"\n❓ Some required data is missing. Create sample data? (y/N): ", end="")
        try:
            user_input = input().strip().lower()
            if user_input in ['y', 'yes']:
                create_sample_data()
                print("\n🔄 Please run this script again to verify the sample data was created.")
        except KeyboardInterrupt:
            print("\n⏭️ Skipping sample data creation")
    
    print(f"\n{'='*40}")
    if all_good:
        print("✅ System is ready for evaluation!")
        print("   You can now run: python test_full_evaluation.py")
    else:
        print("❌ System is not ready for evaluation")
        print("   Please address the issues above before running evaluations")
    print(f"{'='*40}")


if __name__ == "__main__":
    main() 