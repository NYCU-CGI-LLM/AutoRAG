import io
import logging
from typing import Optional, BinaryIO
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

class MinIOService:
    """Service class for handling MinIO operations"""
    
    def __init__(self):
        """Initialize MinIO client"""
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize storage")
    
    async def upload_file(
        self, 
        file: UploadFile, 
        library_id: UUID,
        file_id: Optional[UUID] = None
    ) -> dict:
        """
        Upload a file to MinIO
        
        Args:
            file: FastAPI UploadFile object
            library_id: UUID of the library
            file_id: Optional file UUID, generates new one if not provided
            
        Returns:
            dict: File metadata including file_id, object_name, and upload info
        """
        try:
            if file_id is None:
                file_id = uuid4()
            
            # Create object name with library_id/file_id/original_filename structure
            object_name = f"libraries/{library_id}/{file_id}/{file.filename}"
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Upload to MinIO
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(file_content),
                length=file_size,
                content_type=file.content_type or 'application/octet-stream'
            )
            
            # Reset file position for potential reuse
            await file.seek(0)
            
            logger.info(f"Uploaded file {file.filename} as {object_name}")
            
            return {
                "file_id": str(file_id),
                "object_name": object_name,
                "original_filename": file.filename,
                "file_size": file_size,
                "content_type": file.content_type,
                "etag": result.etag,
                "upload_timestamp": datetime.utcnow().isoformat()
            }
            
        except S3Error as e:
            logger.error(f"MinIO error uploading file: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    def get_file_stream(self, object_name: str, bucket_name: Optional[str] = None):
        """
        Get a raw file stream from MinIO for efficient streaming.
        
        Args:
            object_name: The object name in MinIO.
            bucket_name: Optional bucket name, uses default if not provided.
            
        Returns:
            A raw response object that can be streamed.
            The caller is responsible for closing the stream.
        """
        bucket = bucket_name or self.bucket_name
        try:
            response = self.client.get_object(bucket, object_name)
            return response
        except S3Error as e:
            logger.error(f"MinIO error getting file stream from bucket '{bucket}': {e}")
            if e.code == 'NoSuchKey':
                raise HTTPException(status_code=404, detail="File not found in storage")
            raise HTTPException(status_code=500, detail="Failed to retrieve file stream")
    
    def download_file(self, object_name: str, bucket_name: Optional[str] = None) -> BinaryIO:
        """
        Download a file from MinIO
        
        Args:
            object_name: The object name in MinIO
            bucket_name: Optional bucket name, uses default if not provided
            
        Returns:
            BinaryIO: File data stream
        """
        bucket = bucket_name or self.bucket_name
        try:
            response = self.client.get_object(bucket, object_name)
            return response
        except S3Error as e:
            logger.error(f"MinIO error downloading file from bucket '{bucket}': {e}")
            if e.code == 'NoSuchKey':
                raise HTTPException(status_code=404, detail="File not found")
            raise HTTPException(status_code=500, detail="Failed to download file")
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO
        
        Args:
            object_name: The object name in MinIO
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO error deleting file: {e}")
            if e.code == 'NoSuchKey':
                raise HTTPException(status_code=404, detail="File not found")
            raise HTTPException(status_code=500, detail="Failed to delete file")
    
    def list_library_files(self, library_id: UUID) -> list:
        """
        List all files in a library
        
        Args:
            library_id: UUID of the library
            
        Returns:
            list: List of file objects in the library
        """
        try:
            prefix = f"libraries/{library_id}/"
            objects = self.client.list_objects(
                self.bucket_name, 
                prefix=prefix, 
                recursive=True
            )
            
            files = []
            for obj in objects:
                # Extract file_id and filename from object name
                # Format: libraries/{library_id}/{file_id}/{filename}
                path_parts = obj.object_name.split('/')
                if len(path_parts) >= 4:
                    file_id = path_parts[2]
                    filename = '/'.join(path_parts[3:])  # Handle filenames with slashes
                    
                    files.append({
                        "file_id": file_id,
                        "object_name": obj.object_name,
                        "filename": filename,
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                        "etag": obj.etag
                    })
            
            return files
        except S3Error as e:
            logger.error(f"MinIO error listing files: {e}")
            raise HTTPException(status_code=500, detail="Failed to list files")
    
    def get_file_url(self, object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
        """
        Generate a presigned URL for file access
        
        Args:
            object_name: The object name in MinIO
            expires: URL expiration time
            
        Returns:
            str: Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name, 
                object_name, 
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"MinIO error generating URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate file URL")

# Create a singleton instance
minio_service = MinIOService() 