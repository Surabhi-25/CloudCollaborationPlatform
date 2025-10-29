from fastapi import FastAPI, Depends, HTTPException
import time
import requests
import os

# --- Configuration (Uses environment variable set in docker-compose.yaml) ---
METADATA_SERVICE_URL = os.environ.get("METADATA_SERVICE_URL", "http://metadata-service:80")

# The variable name 'app' is critical as it's what Uvicorn looks for.
app = FastAPI(title="File Handler Service (Port 8083)")

# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint for Docker/K8s."""
    return {"status": "ok", "service": "File Handler Service", "internal_time_ms": round(time.time() * 1000)}

# --- Inter-Service Test Endpoint ---
@app.get("/test-metadata-connection")
async def test_metadata_connection():
    """
    Tests internal connectivity to the Metadata Service using its internal Docker hostname.
    """
    try:
        # Use the internal Docker service name defined in docker-compose.yaml
        response = requests.get(f"{METADATA_SERVICE_URL}/health", timeout=5)
        response.raise_for_status()
        
        return {
            "message": "Successfully connected to Metadata Service internally.",
            "metadata_service_response": response.json()
        }
    except requests.exceptions.RequestException as e:
        # This will fail if the metadata-service container is down or unresponsive
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Metadata Service at {METADATA_SERVICE_URL}: {e}"
        )

# --- Placeholder Upload Endpoint ---
@app.post("/upload-url")
async def get_upload_url():
    """MOCK: Endpoint to generate a pre-signed S3 upload URL."""
    return {
        "message": "Upload URL generated (MOCK)",
        "presigned_url": "https://s3.mock.aws/temp-upload-link",
        "s3_key": "mock-file-123/v1/test.txt"
    }
