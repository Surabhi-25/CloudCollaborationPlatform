# Use the official lightweight Python image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code files (*.py) into the container
# This is more robust than listing files individually and ensures all services are copied.
COPY *.py . 

# The CMD to run the specific service (e.g., uvicorn auth_service:app) 
# is defined separately in the docker-compose.yml file.
