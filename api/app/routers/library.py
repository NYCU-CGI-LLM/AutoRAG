from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from typing import List
from uuid import UUID
from sqlmodel import Session

from app.schemas.library import (
    Library,
    LibraryCreate,
    LibraryDetail,
    LibraryUpdateRequest,
    FileInfo,
    FileUploadResponse,
    FileDownloadResponse
)
from app.schemas.common import (
    ErrorResponse,
    ValidationErrorResponse,
    NotFoundErrorResponse,
    ConflictErrorResponse,
    ServerErrorResponse
)
from app.services.minio_service import minio_service
from app.services.library_service import library_service
from app.core.database import get_session

router = APIRouter(
    prefix="/library",
    tags=["Library"],
)


@router.post("/", response_model=Library, status_code=status.HTTP_201_CREATED)
async def create_library(
    library_create: LibraryCreate, 
    session: Session = Depends(get_session)
):
    """
    Create a new library.
    
    Create a new library with the provided name and description.
    The library will be initialized with empty file collections.
    
    **Request Body:**
    - library_name: Name of the library (required, max 100 chars)
    - description: Optional description (max 500 chars)
    
    **Returns:**
    - Complete library object with ID, timestamps, and stats
    
    **Errors:**
    - 409: Library name already exists
    - 422: Validation error (invalid input)
    - 500: Internal server error
    """
    try:
        library = library_service.create_library(library_create, session)
        return library
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create library: {str(e)}")


@router.get("/", response_model=List[Library])
async def list_libraries(session: Session = Depends(get_session)):
    """
    List all libraries.
    
    Returns a list of all libraries with basic metadata and file counts.
    Libraries are sorted by creation date (newest first).
    
    **Returns:**
    - List of libraries with statistics
    
    **Errors:**
    - 500: Internal server error
    """
    try:
        libraries = library_service.list_libraries(session)
        return libraries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list libraries: {str(e)}")


@router.get("/{library_id}", response_model=LibraryDetail)
async def get_library(
    library_id: UUID, 
    session: Session = Depends(get_session)
):
    """
    Get single library details with files.
    
    Returns detailed information about a specific library,
    including complete file list and metadata. File statistics
    are updated in real-time from MinIO storage.
    
    **Path Parameters:**
    - library_id: UUID of the library
    
    **Returns:**
    - Complete library details with file list and current statistics
    
    **Errors:**
    - 404: Library not found
    - 500: Internal server error
    """
    try:
        library_detail = library_service.get_library_detail(library_id, session)
        return library_detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve library: {str(e)}")


@router.post("/{library_id}/file", response_model=FileUploadResponse)
async def upload_file(
    library_id: UUID, 
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    Upload one file into the library.
    
    Upload a single file to the specified library for raw data storage.
    Files are stored in MinIO object storage with organized folder structure.
    
    **Path Parameters:**
    - library_id: UUID of the target library
    
    **Form Data:**
    - file: The file to upload
    
    **File Restrictions:**
    - Maximum size: 100MB
    - Allowed types: PDF, DOC, DOCX, TXT, CSV, JSON, MD
    
    **Returns:**
    - File upload response with complete metadata
    
    **Errors:**
    - 400: Invalid file type or other validation error
    - 404: Library not found
    - 413: File too large (>100MB)
    - 500: Internal server error
    """
    try:
        # Validate library exists
        if not library_service.library_exists(library_id, session):
            raise HTTPException(
                status_code=404,
                detail=f"Library with ID {library_id} not found"
            )
        
        # Check file size (100MB limit)
        if file.size and file.size > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 100MB")
        
        # Check file type restrictions
        allowed_types = {
            'text/plain', 'text/csv', 'application/pdf', 
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/json', 'text/markdown'
        }
        if file.content_type and file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file.content_type} not supported. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Upload file to MinIO
        upload_result = await minio_service.upload_file(file, library_id)
        
        # Create file record in database with complete metadata
        file_id = UUID(upload_result["file_id"])
        db_file = library_service.create_file_record(
            library_id,
            file_id,
            upload_result["original_filename"],
            upload_result["content_type"],
            upload_result["file_size"],
            "rag-files",  # bucket
            upload_result.get("object_name", ""),
            upload_result.get("checksum_md5"),
            None,  # uploader_id
            session
        )
        
        # Return response with complete file metadata
        return FileUploadResponse(
            file_id=file_id,
            file_name=db_file.file_name,
            file_size=db_file.size_bytes,
            mime_type=db_file.mime_type,
            bucket=db_file.bucket,
            object_key=db_file.object_key,
            status=str(db_file.status),
            uploaded_at=db_file.uploaded_at,
            checksum_md5=db_file.checksum_md5,
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/{library_id}/files", include_in_schema=False)
async def list_library_files(
    library_id: UUID, 
    session: Session = Depends(get_session)
):
    """
    List all files in a library.
    
    Returns all files stored in the specified library from the database.
    Files are returned with complete metadata including size, upload time, and status.
    
    **Path Parameters:**
    - library_id: UUID of the library
    
    **Returns:**
    - List of files with complete metadata
    
    **Errors:**
    - 404: Library not found
    - 500: Internal server error
    """
    try:
        # Validate library exists
        if not library_service.library_exists(library_id, session):
            raise HTTPException(
                status_code=404,
                detail=f"Library with ID {library_id} not found"
            )
        
        # Get library detail which includes files
        library_detail = library_service.get_library_detail(library_id, session)
        return {"files": library_detail.files}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/{library_id}/file/{file_id}/download", response_model=FileDownloadResponse)
async def download_file(
    library_id: UUID, 
    file_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Download a file from the library.
    
    Generate a presigned URL for downloading the file from MinIO.
    The URL is valid for 1 hour and allows temporary access without credentials.
    
    **Path Parameters:**
    - library_id: UUID of the library
    - file_id: UUID of the file
    
    **Returns:**
    - Presigned URL for file download with complete metadata
    
    **Errors:**
    - 404: Library or file not found
    - 500: Internal server error
    """
    try:
        # Validate library exists
        if not library_service.library_exists(library_id, session):
            raise HTTPException(
                status_code=404,
                detail=f"Library with ID {library_id} not found"
            )
        
        # Get file from database
        db_file = library_service.get_file_by_id(file_id, session)
        if not db_file or db_file.library_id != library_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Generate presigned URL using MinIO object key
        download_url = minio_service.get_file_url(db_file.object_key)
        
        return FileDownloadResponse(
            download_url=download_url,
            file_name=db_file.file_name,
            file_size=db_file.size_bytes,
            mime_type=db_file.mime_type,
            expires_in="1 hour"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")


# Hidden endpoints for future implementation
@router.put("/{library_id}", response_model=Library, include_in_schema=False)
async def update_library(
    library_id: UUID, 
    library_update: LibraryUpdateRequest,
    session: Session = Depends(get_session)
):
    """
    Update library information.
    
    Update the metadata of an existing library. Only provided fields will be updated.
    This endpoint is hidden from API documentation and will be implemented in the future.
    """
    try:
        library = library_service.update_library(
            library_id, 
            library_update.library_name, 
            library_update.description,
            session
        )
        return library
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update library: {str(e)}")


@router.delete("/{library_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_library(
    library_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Delete a library.
    
    Permanently delete a library and all its associated files from MinIO.
    This operation cannot be undone.
    This endpoint is hidden from API documentation and will be implemented in the future.
    """
    try:
        library_service.delete_library(library_id, session)
        return
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete library: {str(e)}")


@router.delete("/{library_id}/file/{file_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_file(
    library_id: UUID, 
    file_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Delete a specific file from the library.
    
    Remove a single file from the library's file collection in MinIO.
    This operation cannot be undone.
    This endpoint is hidden from API documentation and will be implemented in the future.
    """
    try:
        # Validate library exists
        if not library_service.library_exists(library_id, session):
            raise HTTPException(
                status_code=404,
                detail=f"Library with ID {library_id} not found"
            )
        
        # Get file metadata to construct object name
        files = minio_service.list_library_files(library_id)
        file_info = next((f for f in files if f["file_id"] == str(file_id)), None)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete file from MinIO
        minio_service.delete_file(file_info["object_name"])
        
        # Delete file record from database
        from sqlmodel import select
        from app.models.file import File as FileModel
        
        file_statement = select(FileModel).where(FileModel.id == file_id, FileModel.library_id == library_id)
        db_file = session.exec(file_statement).first()
        
        if db_file:
            session.delete(db_file)
            session.commit()
        
        return
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}") 