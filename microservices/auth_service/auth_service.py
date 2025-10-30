from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import datetime
import uuid

# --- FastAPI Initialization ---
app = FastAPI()

# --- CORS Configuration ---
origins = ["*",] # Allow all origins for local development

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------

# --- Configuration (MUST MATCH file_handler_service.py) ---
SECRET_KEY = "your-secret-key-that-should-be-kept-safe" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 # 24 Hours

class Token(BaseModel):
    token: str

@app.get("/login/{user_id}", response_model=Token, tags=["Authentication"])
async def login_for_access_token(user_id: str):
    """Generates a new JWT token for the given user_id."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expiration = now + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)

    to_encode = {
        "sub": user_id, 
        "user_id": user_id, # Crucial key for the File Handler
        "team_id": "team-alpha-123", 
        "iat": now.timestamp(),
        "exp": expiration.timestamp()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"token": encoded_jwt}

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "service": "Auth Service"}
