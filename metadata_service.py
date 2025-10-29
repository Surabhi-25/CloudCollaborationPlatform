from fastapi import FastAPI
import time

# The variable name 'app' is critical as it's what Uvicorn looks for.
app = FastAPI(title="Metadata Service (Port 8082)")

# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint for Docker/K8s."""
    return {"status": "ok", "service": "Metadata Service", "internal_time_ms": round(time.time() * 1000)}

# --- Placeholder Endpoint ---
@app.get("/metadata/list")
async def list_files():
    """MOCK: Endpoint to list all file metadata records."""
    return {
        "message": "Metadata list endpoint is reachable.",
        "data": [{"file_id": "mock-f1", "name": "document.pdf", "version": 1}]
    }
