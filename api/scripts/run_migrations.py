#!/usr/bin/env python3
"""
Script to run database migrations using Alembic
"""
import os
import subprocess
import sys
from pathlib import Path

def run_migrations():
    """Run Alembic migrations"""
    print("Running database migrations...")
    
    try:
        # Change to the directory containing alembic.ini
        os.chdir(Path(__file__).parent)
        
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Migrations completed successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print("❌ Migration failed!")
        print(f"Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations() 