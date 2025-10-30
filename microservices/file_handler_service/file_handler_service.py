from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import httpx 
import uuid
from typing import Optional

# --- FastAPI Initialization ---
app = FastAPI()

# --- CORS Configuration ---
origins = ["*",]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------

# --- Configuration (MUST MATCH auth_service.py) ---
SECRET_KEY = "your-secret-key-that-should-be-kept-safe"
ALGORITHM = "HS256"
METADATA_SERVICE_URL = "http://127.0.0.1:8082" 

# --- Request/Response Models ---
class UploadUrlRequest(BaseModel):
    file_name: str
    mime_type: str

class UploadUrlResponse(BaseModel):
    file_id: str
    upload_url: str
    user_id: str

# --- JWT Dependency Helper (CRITICAL CHECK) ---
def get_current_user_id(authorization: str = Header(None)) -> str:
    """Decodes and validates the JWT token from the Authorization header."""
    
    # 1. Check for token format
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid 'Bearer' token format.")
    
    token_value = authorization.replace("Bearer ", "")
    
    try:
        # 2. Decode the token using the shared secret key
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        
        # 3. Check if user_id exists in the payload
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized: Token payload is missing the required user_id claim.")
        
        return str(user_id) # Ensure user_id is returned as a string
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Unauthorized: Token expired.")
    except jwt.InvalidSignatureError:
        # Indicates SECRET_KEY mismatch or token manipulation
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token signature (Check SECRET_KEY consistency).")
    except jwt.InvalidTokenError as e:
        # Catches other malformed token issues
        raise HTTPException(status_code=401, detail=f"Unauthorized: Invalid token format. {e}")

# ==============================================================================
# Mock S3 Endpoint 
# ==============================================================================
@app.put("/mock-s3-upload/{s3_key:path}", tags=["Mock S3 Upload"])
async def mock_s3_upload(s3_key: str, content_type: Optional[str] = Header(None)):
    """Simulates the successful receipt of a file by an S3-like endpoint."""
    print(f"--- MOCK S3 RECEIVED --- Key: {s3_key}, Content-Type: {content_type}")
    return {"status": "S3 Mock Success", "key": s3_key, "message": "File received by mock S3 endpoint."}


@app.post("/upload_url", response_model=UploadUrlResponse, tags=["File Handler"])
async def request_upload_url(
    request_data: UploadUrlRequest, 
    user_id: str = Depends(get_current_user_id) # Token validation happens here
):
    """Orchestrates token validation and metadata creation."""
    print(f"User {user_id} requested upload URL for: {request_data.file_name}")

    # Prepare the payload for the Metadata Service
    metadata_payload = {
        "file_name": request_data.file_name,
        "mime_type": request_data.mime_type,
        "user_id": user_id # Passed from the successfully decoded JWT
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{METADATA_SERVICE_URL}/file_metadata",
                json=metadata_payload
            )
            
            if response.status_code != 200:
                print(f"Error from Metadata Service: {response.status_code} - {response.text}")
                
                # --- FIX FOR "detail not found" ---
                # Attempt to extract the 'detail' from the error response
                detail_message = response.text
                try:
                    # If the response is valid JSON, get the 'detail' or provide a fallback
                    detail_message = response.json().get('detail', f"Non-standard JSON error: {response.text}")
                except:
                    pass # Keep the full response text if JSON parsing fails
                
                # Propagate the error clearly
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Metadata Service Error ({response.status_code}): {detail_message}"
                )
                # ------------------------------------
            
            metadata_response = response.json()
            file_id = metadata_response['file_id']
            
            # Construct the mock S3 key for the client upload
            s3_key = f"{user_id}/{file_id}/{request_data.file_name}"
            mock_s3_upload_url = f"http://127.0.0.1:8083/mock-s3-upload/{s3_key}"
            
            print(f"Mapped Mock S3 Upload URL for client: {mock_s3_upload_url}")

            return UploadUrlResponse(
                file_id=file_id,
                upload_url=mock_s3_upload_url,
                user_id=user_id
            )

    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Metadata Service at {METADATA_SERVICE_URL}. Is it running?")
    except Exception as e:
        print(f"Unexpected error during Metadata Service call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during upload request.")

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "service": "File Handler Service"}
