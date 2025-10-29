from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time

# The variable name 'app' is critical as it's what Uvicorn looks for.
app = FastAPI(title="Auth Service (Port 8081)")

# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint for Docker/K8s."""
    return {"status": "ok", "service": "Auth Service", "internal_time_ms": round(time.time() * 1000)}

# --- Placeholder Login Endpoint ---

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    """
    MOCK: This endpoint simulates user authentication and token issuance.
    We'll integrate this with the PostgreSQL container later.
    """
    # MOCK Logic
    if request.username == "testuser" and request.password == "testpass":
        mock_token = f"jwt-token-for-{request.username}-12345"
        return {
            "message": "Login successful (MOCK)",
            "user_id": "mock-user-123",
            "token": mock_token
        }
    
    raise HTTPException(status_code=401, detail="Invalid Credentials (MOCK)")
