import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

# --- CONFIGURATION ---
# This dictionary simulates the database of file permissions (ACLs)
MOCK_ACLS = {
    # File ID: {User ID: [Permissions], ...}
    "secret_doc_456": {
        "user_aditya_id_102": ["READ"],         # Aditya only has READ
        "user_bob_id_103": ["READ", "WRITE"]    # Bob has READ/WRITE
    },
    "public_report_123": {
        "user_aditya_id_102": ["READ", "WRITE"],# Aditya has READ/WRITE
        "user_bob_id_103": ["READ"]
    },
}

# --- Pydantic Models ---
class PermissionCheckRequest(BaseModel):
    user_id: str
    file_id: str
    required_permission: str # e.g., "READ" or "WRITE"

class PermissionCheckResponse(BaseModel):
    is_authorized: bool
    user_id: str
    file_id: str

# --- Service Setup ---
app = FastAPI(
    title="Metadata Service (ACL Check)",
    description="Manages and validates file access control lists (ACLs).",
    version="1.0.0"
)

# --- API Endpoint ---

@app.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(request: PermissionCheckRequest):
    """
    Checks if a given user has the required permission (READ/WRITE) for a file.
    """
    file_acl = MOCK_ACLS.get(request.file_id)
    
    if not file_acl:
        # File not found or no ACL defined, deny access by default for security
        print(f"Access DENIED: File ID {request.file_id} not found in ACLs.")
        return PermissionCheckResponse(is_authorized=False, user_id=request.user_id, file_id=request.file_id)

    user_permissions: Optional[List[str]] = file_acl.get(request.user_id)
    
    if not user_permissions:
        # User not explicitly listed in the ACL, deny access
        print(f"Access DENIED: User {request.user_id} not listed for file {request.file_id}.")
        return PermissionCheckResponse(is_authorized=False, user_id=request.user_id, file_id=request.file_id)
    
    # Check if the required permission is in the user's list
    is_authorized = request.required_permission in user_permissions
    
    if is_authorized:
        print(f"Access GRANTED: User {request.user_id} has {request.required_permission} access for file {request.file_id}.")
    else:
        print(f"Access DENIED: User {request.user_id} lacks {request.required_permission} permission for file {request.file_id}.")

    return PermissionCheckResponse(
        is_authorized=is_authorized,
        user_id=request.user_id,
        file_id=request.file_id
    )

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8082)
