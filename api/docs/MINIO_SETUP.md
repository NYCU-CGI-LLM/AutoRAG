# MinIO Integration Setup Guide

This guide explains how to set up and use MinIO for file management in the AUO-RAG API.

## What is MinIO?

MinIO is a high-performance, S3-compatible object storage system. It's perfect for storing and managing files uploaded through your API, providing:

- **Scalable storage**: Handle large files and lots of them
- **S3 compatibility**: Use familiar S3 APIs and tools
- **Web interface**: Browse and manage files through a web UI
- **Presigned URLs**: Secure file sharing with expiring links
- **Organized storage**: Files are organized by library and file ID

## Quick Start

### 1. Start All Services (Including MinIO)

```bash
# Start all services including MinIO with a single command
docker-compose up -d

# This will start:
# - PostgreSQL (database)
# - Redis (cache/message broker)
# - MinIO (object storage) on ports 9000 (API) and 9001 (Console)
# - Adminer (database admin) on port 8080
# - Automatic bucket creation
```

### 2. Install Dependencies

```bash
# Install the MinIO Python client
cd api
pip install -r requirements.txt
```

### 3. Configure Environment

The MinIO configuration is already set in `api/.env.dev`:

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_NAME=autorag-files
```

**Note**: When running the API in Docker containers, the endpoint automatically changes to `minio:9000` for internal container communication.

### 4. Start Your API

```bash
cd api
uvicorn app.main:app --reload
```

## Using the File Upload API

### Upload a File

```bash
curl -X POST \
  "http://localhost:8000/api/v1/library/{library_id}/file" \
  -F "file=@/path/to/your/file.pdf"
```

Response:
```json
{
  "file_id": "12345678-1234-1234-1234-123456789abc",
  "filename": "file.pdf",
  "file_size": 1024000,
  "content_type": "application/pdf",
  "upload_timestamp": "2024-01-01T12:00:00"
}
```

### List Files in a Library

```bash
curl "http://localhost:8000/api/v1/library/{library_id}/files"
```

### Download a File

```bash
curl "http://localhost:8000/api/v1/library/{library_id}/file/{file_id}/download"
```

This returns a presigned URL that's valid for 1 hour:
```json
{
  "download_url": "http://localhost:9000/autorag-files/libraries/...",
  "filename": "file.pdf",
  "expires_in": "1 hour"
}
```

## MinIO Web Console

Access the MinIO web interface at: http://localhost:9001

- **Username**: minioadmin
- **Password**: minioadmin

Here you can:
- Browse uploaded files
- View file metadata
- Monitor storage usage
- Manage buckets and policies

## Service Architecture

With the integrated Docker Compose setup, your services work together:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your API      │    │     MinIO       │    │   PostgreSQL    │
│  (Port 8000)    │◄───┤  (Port 9000)    │    │  (Port 5432)    │
│                 │    │  Console: 9001  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │  (Port 6379)    │
                    └─────────────────┘
```

## Development vs Production

### Development (Current Setup)
- MinIO endpoint: `localhost:9000`
- All services on localhost
- Default credentials for easy setup

### When Running API in Docker
- MinIO endpoint: `minio:9000` (internal Docker networking)
- Environment variables in the commented API service configuration
- All services in the same Docker network

### Production Recommendations
- Change default MinIO credentials
- Use external MinIO cluster for scalability
- Enable TLS/SSL encryption
- Set up proper backup and replication

## File Organization

Files are stored in MinIO with this structure:

```
autorag-files/                    # Bucket name
├── libraries/
│   ├── {library_id_1}/
│   │   ├── {file_id_1}/
│   │   │   └── original_filename.pdf
│   │   ├── {file_id_2}/
│   │   │   └── document.docx
│   │   └── ...
│   ├── {library_id_2}/
│   │   └── ...
│   └── ...
```

This organization provides:
- **Library isolation**: Each library's files are separate
- **Unique file IDs**: No filename conflicts
- **Original names preserved**: Easy identification
- **Easy cleanup**: Delete entire library folders

## Supported File Types

Currently configured file types:
- **Text**: `.txt`, `.csv`, `.json`, `.md`
- **Documents**: `.pdf`, `.doc`, `.docx`

To modify supported types, edit the `allowed_types` set in `api/app/routers/library.py`.

## File Size Limits

- **Current limit**: 100MB per file
- **Configurable**: Modify in `api/app/routers/library.py`

## Security Features

### Presigned URLs
- **Temporary access**: URLs expire after 1 hour
- **No credentials needed**: Safe to share URLs temporarily
- **Configurable expiration**: Change in `MinIOService.get_file_url()`

### Access Control
- Files are not publicly accessible by default
- Access only through API endpoints
- Database can track file ownership and permissions

## Command Reference

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f minio

# Stop all services
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v

# Check service status
docker-compose ps

# Restart just MinIO
docker-compose restart minio
```

## Troubleshooting

### Connection Issues

1. **Check all services are running**:
   ```bash
   docker-compose ps
   ```

2. **Check MinIO health**:
   ```bash
   curl http://localhost:9000/minio/health/live
   ```

3. **Check bucket exists**:
   - Visit MinIO console at http://localhost:9001
   - Login with minioadmin/minioadmin
   - Verify 'autorag-files' bucket exists

### Permission Issues

1. **Bucket policy**: Ensure bucket has proper read/write permissions
2. **Access keys**: Verify MINIO_ACCESS_KEY and MINIO_SECRET_KEY are correct
3. **Network**: Ensure API can reach MinIO (check Docker network)

### Development Environment

1. **Local development**: Use `localhost:9000` in `.env.dev`
2. **Docker development**: Use `minio:9000` when API runs in container
3. **Mixed setup**: API local, MinIO in Docker - use `localhost:9000`

## API Integration Examples

### Python Client Example

```python
from app.services.minio_service import minio_service
from uuid import uuid4

# Upload a file
async def upload_example():
    library_id = uuid4()
    # file is a FastAPI UploadFile
    result = await minio_service.upload_file(file, library_id)
    print(f"Uploaded: {result['file_id']}")

# List files
def list_example():
    library_id = uuid4()
    files = minio_service.list_library_files(library_id)
    for file_info in files:
        print(f"File: {file_info['filename']}")

# Generate download URL
def download_example():
    object_name = "libraries/lib-id/file-id/filename.pdf"
    url = minio_service.get_file_url(object_name)
    print(f"Download URL: {url}")
```

## Benefits of Integrated Setup

1. **Single Command Start**: `docker-compose up -d` starts everything
2. **Unified Networking**: All services can communicate internally
3. **Simplified Configuration**: One file to manage all services
4. **Easy Development**: Consistent environment across team
5. **Production Ready**: Easy to deploy same configuration

## Next Steps

1. **Database Integration**: Store file metadata in PostgreSQL
2. **File Processing**: Add text extraction for RAG pipeline
3. **Thumbnails**: Generate preview images for documents
4. **Virus Scanning**: Integrate antivirus scanning
5. **Compression**: Implement file compression for storage efficiency

## Support

For issues with MinIO integration:
1. Check service logs: `docker-compose logs minio`
2. Review API logs for detailed error messages
3. Verify environment configuration
4. Test with MinIO console first 