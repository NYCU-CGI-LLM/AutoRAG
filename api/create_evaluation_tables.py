#!/usr/bin/env python3
"""
Migration script to create evaluation tables
"""

import sys
import os
from pathlib import Path

# Add the api directory to Python path
api_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(api_dir))

from app.core.database import create_db_and_tables
from app.models.evaluation import Evaluation, BenchmarkDataset

def main():
    """Create evaluation tables"""
    print("Creating evaluation tables...")
    
    try:
        create_db_and_tables()
        print("✅ Evaluation tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 