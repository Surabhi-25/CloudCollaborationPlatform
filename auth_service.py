import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- CONFIGURATION ---
# This secret MUST match the secret used in file_handler_service.py
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-key-for-jwt-signing-12345")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = 60 * 24 # 24 hours

# --- Mock User Database (Replace with DynamoDB/RDS in production) ---
MOCK_USERS = {
    "user_aditya": {
        "password": "secure_pass_aditya", 
        "user_id": "user_aditya_id_102"
    },
    "user_bob": {
        "password": "secure_pass_bob", 
        "user_id": "user_bob_id_103"
    },
}

# --- JWT Generation Helper ---

def create_access_token(user_id: str) -> str:
    """Generates a signed JWT token with an expiration time."""
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
    
    # The 'sub' (subject) claim is used to hold the user identifier, 
    # which the File Handler Service will extract.
    payload = {
        'exp': int(expiration.timestamp()),
        'iat': int(now.timestamp()),
        'sub': user_id, 
        # Add other claims like 'role' or 'team_id' here if needed
    }
    
    encoded_jwt = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

# --- Pydantic Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    expires_in_minutes: int = TOKEN_EXPIRATION_MINUTES

# --- Service Setup ---
app = FastAPI(
    title="Auth Service (JWT Issuer)",
    description="Handles user login and issues JWT access tokens.",
    version="1.0.0"
)

# --- API Endpoint ---

@app.post("/login", response_model=TokenResponse)
async def login_for_access_token(form_data: LoginRequest):
    """
    Authenticates user against the mock database and returns a JWT token.
    """
    user_data = MOCK_USERS.get(form_data.username)
    
    if not user_data or user_data["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    user_id = user_data["user_id"]
    access_token = create_access_token(user_id=user_id)
    
    print(f"User {form_data.username} logged in, token issued.")
    
    return TokenResponse(
        access_token=access_token,
        user_id=user_id
    )

if __name__ == "__main__":
    import uvicorn
    print("--- Auth Service Ready ---")
    print(f"JWT Secret: {JWT_SECRET}")
    # uvicorn.run(app, host="0.0.0.0", port=8081)
