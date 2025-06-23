#!/usr/bin/env python3
"""Reset MinIO buckets script (non-interactive version) - deletes all buckets and recreates them"""

import sys
import logging
from pathlib import Path

# Add the parent directory (api/) to Python path for imports
api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from reset_minio import reset_minio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function - force reset without confirmation"""
    logger.info("🚨 FORCE RESET: Resetting MinIO without confirmation")
    
    success = reset_minio()
    
    if success:
        logger.info("✅ MinIO reset completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ MinIO reset failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 