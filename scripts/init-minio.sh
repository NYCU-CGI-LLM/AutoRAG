#!/bin/bash

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
until curl -f http://minio:9000/minio/health/live > /dev/null 2>&1; do
    echo "MinIO is not ready yet. Waiting..."
    sleep 5
done

echo "MinIO is ready. Setting up buckets..."

# Configure MinIO client
mc alias set myminio http://minio:9000 adminadmin adminadmin

# Create autorag bucket if it doesn't exist
mc mb myminio/autorag-files --ignore-existing

# Set public policy for the bucket
mc policy set public myminio/autorag-files

echo "MinIO bucket setup completed successfully!" 