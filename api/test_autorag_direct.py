#!/usr/bin/env python3
"""
Direct AutoRAG Evaluation Test Script

Usage: python test_autorag_direct.py /path/to/eval/directory

This script will:
1. Check if the evaluation directory exists and has required files
2. Run AutoRAG evaluation directly
3. Show results
"""

import os
import sys
import yaml
from pathlib import Path
import pandas as pd

def check_directory_structure(eval_dir: Path):
    """Check if the evaluation directory has the required structure"""
    print(f"🔍 Checking directory structure: {eval_dir}")
    
    required_files = [
        "data/qa.parquet",
        "data/corpus.parquet", 
        "config.yaml"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = eval_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"   ✅ Found: {file_path}")
    
    if missing_files:
        print(f"   ❌ Missing files: {missing_files}")
        return False
    
    return True

def show_config(config_path: Path):
    """Display the AutoRAG configuration"""
    print(f"\n📋 AutoRAG Configuration:")
    print("-" * 50)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(yaml.dump(config, default_flow_style=False, indent=2))
    print("-" * 50)

def show_data_info(eval_dir: Path):
    """Show information about the data files"""
    print(f"\n📊 Data Information:")
    print("-" * 30)
    
    qa_path = eval_dir / "data" / "qa.parquet"
    corpus_path = eval_dir / "data" / "corpus.parquet"
    
    if qa_path.exists():
        qa_df = pd.read_parquet(qa_path)
        print(f"   QA Dataset: {len(qa_df)} rows")
        print(f"   QA Columns: {list(qa_df.columns)}")
    
    if corpus_path.exists():
        corpus_df = pd.read_parquet(corpus_path)
        print(f"   Corpus Dataset: {len(corpus_df)} rows") 
        print(f"   Corpus Columns: {list(corpus_df.columns)}")

def run_autorag_evaluation(eval_dir: Path):
    """Run AutoRAG evaluation"""
    print(f"\n🚀 Running AutoRAG Evaluation...")
    print("-" * 40)
    
    try:
        # Add AutoRAG to path - need to add the correct autorag module path
        autorag_path = Path(__file__).parent.parent / "autorag"
        sys.path.insert(0, str(autorag_path))
        
        from autorag.evaluator import Evaluator
        
        # Set up paths
        qa_data_path = str(eval_dir / "data" / "qa.parquet")
        corpus_data_path = str(eval_dir / "data" / "corpus.parquet")
        config_path = str(eval_dir / "config.yaml")
        
        print(f"   QA Data: {qa_data_path}")
        print(f"   Corpus Data: {corpus_data_path}")
        print(f"   Config: {config_path}")
        print(f"   Project Dir: {eval_dir}")
        
        # Initialize AutoRAG Evaluator
        evaluator = Evaluator(
            qa_data_path=qa_data_path,
            corpus_data_path=corpus_data_path,
            project_dir=str(eval_dir)
        )
        
        print(f"\n   ⏳ Starting AutoRAG trial...")
        
        # Run evaluation
        evaluator.start_trial(
            yaml_path=config_path,
            skip_validation=True,  # Skip validation for faster execution
            full_ingest=False  # Only ingest retrieval_gt corpus for faster execution
        )
        
        print(f"   ✅ AutoRAG evaluation completed!")
        return True
        
    except Exception as e:
        print(f"   ❌ AutoRAG evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_results(eval_dir: Path):
    """Show evaluation results if available"""
    print(f"\n📈 Evaluation Results:")
    print("-" * 30)
    
    # Look for trial directories
    trial_dirs = [d for d in eval_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    
    if not trial_dirs:
        print("   ❌ No trial directories found")
        return
    
    # Get the latest trial
    latest_trial = max(trial_dirs, key=lambda x: int(x.name))
    print(f"   📁 Latest trial: {latest_trial.name}")
    
    # Check for summary.csv
    summary_path = latest_trial / "summary.csv"
    if summary_path.exists():
        print(f"   ✅ Found summary.csv")
        summary_df = pd.read_csv(summary_path)
        print(f"   📊 Summary:")
        print(summary_df.to_string(index=False))
    else:
        print(f"   ❌ No summary.csv found")
    
    # List all files in trial directory
    print(f"\n   📂 Trial directory contents:")
    for item in latest_trial.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(latest_trial)
            print(f"      {rel_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_autorag_direct.py /path/to/eval/directory")
        print("Example: python test_autorag_direct.py /tmp/eval_debug_3mv8uwo2")
        sys.exit(1)
    
    eval_dir = Path(sys.argv[1])
    
    if not eval_dir.exists():
        print(f"❌ Directory does not exist: {eval_dir}")
        sys.exit(1)
    
    print(f"🧪 AutoRAG Direct Evaluation Test")
    print(f"=" * 50)
    print(f"Target Directory: {eval_dir}")
    
    # Step 1: Check directory structure
    if not check_directory_structure(eval_dir):
        print("❌ Directory structure check failed")
        sys.exit(1)
    
    # Step 2: Show configuration
    config_path = eval_dir / "config.yaml"
    show_config(config_path)
    
    # Step 3: Show data information
    show_data_info(eval_dir)
    
    # Step 4: Run AutoRAG evaluation
    success = run_autorag_evaluation(eval_dir)
    
    # Step 5: Show results
    if success:
        show_results(eval_dir)
    
    print(f"\n{'✅ Test completed successfully!' if success else '❌ Test failed!'}")

if __name__ == "__main__":
    main() 