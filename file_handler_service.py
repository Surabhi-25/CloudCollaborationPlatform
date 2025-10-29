import os
import jwt
import requests
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

# --- CONFIGURATION ---
# IMPORTANT: This secret MUST match the secret in auth_service.py
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-key-for-jwt-signing-12345")
JWT_ALGORITHM = "HS256"

# Environment URL for the Metadata Service
METADATA_SERVICE_URL = os.environ.get("METADATA_SERVICE_URL", "http://127.0.0.1:8082")

# --- Utility Functions ---

def get_required_permission(action: str) -> Optional[str]:
    """Maps the requested action (upload/download) to the required permission (WRITE/READ)."""
    # WRITE actions
    if action.lower() in ["upload", "delete", "write"]:
        return "WRITE"
    # READ actions
    elif action.lower() in ["download", "read"]:
        return "READ"
    return None

def verify_jwt(token: str) -> Optional[str]:
    """Decodes and validates JWT, returning the user_id (sub claim)."""
    try:
        # We only need to check the signature and expiration here
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('sub') # 'sub' holds the user_id
    except jwt.PyJWTError as e:
        print(f"JWT Verification failed: {e}")
        return None

# --- Pydantic Models ---
class GenerateUrlRequest(BaseModel):
    file_id: str
    s3_key: str
    action: str # "upload" or "download"
    
class GenerateUrlResponse(BaseModel):
    url: str
    key: str

# --- Service Setup ---
app = FastAPI(
    title="File Handler Service (S3 Simulator)",
    description="Generates S3 Presigned URLs after verifying permissions.",
    version="1.0.0"
)

# --- API Endpoint ---

@app.post("/generate-url", response_model=GenerateUrlResponse)
async def generate_presigned_url(
    request: GenerateUrlRequest,
    authorization: Optional[str] = Header(None)
):
    """
    1. Authenticates user via JWT.
    2. Checks required permissions with Metadata Service (8082).
    3. Simulates S3 URL generation if authorized.
    """
    # --- Step 1: Authentication and User ID Extraction ---
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    
    token = authorization.split(" ")[1]
    user_id = verify_jwt(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token"
        ) 
        
    required_permission = get_required_permission(request.action)
    if not required_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action specified. Use 'upload' or 'download'."
        )

    # --- Step 2: Authorization Check with Metadata Service (8082) ---
    check_payload = {
        "user_id": user_id,
        "file_id": request.file_id,
        "required_permission": required_permission
    }
    
    try:
        response = requests.post(
            f"{METADATA_SERVICE_URL}/check-permission",
            json=check_payload,
            timeout=5
        )
        response.raise_for_status() # Raises HTTPError for bad status codes (4xx or 5xx)
        
        permission_data = response.json()
        
        if not permission_data.get('is_authorized'):
            # This is the actual denial point
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User {user_id} has no access to file {request.file_id} for action {request.action}."
            )
            
    except requests.exceptions.RequestException as e:
        print(f"Metadata Service communication error: {e}")
        # Note: If this fails, it often means the Metadata Service (8082) is down or unreachable.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot verify permissions: Metadata Service is unavailable."
        )

    # --- Step 3: Simulation of Presigned URL Generation (If Authorized) ---
    print(f"Permissions GRANTED. Simulating S3 URL generation for {user_id} to {request.s3_key} with action {request.action}.")

    url_action = "PUT" if required_permission == "WRITE" else "GET"
    simulated_url = f"SIMULATED_S3_PRESIGNED_URL_{url_action}_FOR_{request.file_id}_WITH_EXPIRATION"
    
    return GenerateUrlResponse(
        url=simulated_url,
        key=request.s3_key
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
