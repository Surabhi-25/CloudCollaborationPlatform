# Use the official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies first (for caching efficiency)
# This step is critical for caching: if requirements.txt doesn't change, Docker won't rerun pip install.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (including metadata_service.py)
# The "." refers to the build context, which is the ./metadata-service directory.
COPY . .

# Expose the port Uvicorn will listen on. 
# This port (80) is mapped to 8082 on the host via docker-compose.yaml.
EXPOSE 80
# The final CMD is specified in the docker-compose.yaml file to run Uvicorn.
