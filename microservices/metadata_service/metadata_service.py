from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import time
from typing import Dict

app = FastAPI()

# In-memory storage for file metadata (simulating a database)
FILE_METADATA_STORE: Dict[str, dict] = {}

class FileMetadata(BaseModel):
    file_name: str
    mime_type: str
    user_id: str 

@app.get("/")
async def root():
    return {"message": "Metadata Service is running on port 8082"}

@app.post("/file_metadata")
async def create_file_metadata(metadata: FileMetadata):
    """Creates a new file record and returns a mock upload URL."""
    # CRITICAL: If user_id is missing (e.g., None from a failed JWT decode)
    if not metadata.user_id:
        raise HTTPException(status_code=400, detail="Metadata Storage Error: User ID is required.")

    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    
    # Simulate a presigned URL generation (real apps use S3 SDK here)
    presigned_url = f"https://mock-upload.com/storage/{file_id}?token={int(time.time())}"
    
    data_to_store = {
        "file_id": file_id,
        "user_id": metadata.user_id,
        "file_name": metadata.file_name,
        "mime_type": metadata.mime_type,
        "created_at": time.time()
    }

    # Store the metadata
    FILE_METADATA_STORE[file_id] = data_to_store
    
    return {
        "file_id": file_id,
        "upload_url": presigned_url,
        "user_id": metadata.user_id
    }

@app.get("/file_metadata/{file_id}")
async def get_file_metadata(file_id: str):
    if file_id not in FILE_METADATA_STORE:
        raise HTTPException(status_code=404, detail="File metadata not found")
    return FILE_METADATA_STORE[file_id]

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "service": "Metadata Service"}
