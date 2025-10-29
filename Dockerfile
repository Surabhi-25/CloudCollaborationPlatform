# Use the official lightweight Python image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# We install dependencies here because this step is often cached, speeding up later builds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all local microservice code into the container
# This copies all three Python files into the /app directory defined above
COPY auth_service.py metadata_service.py file_handler_service.py .

# The CMD to run the specific service (e.g., uvicorn auth_service:app) 
# is defined separately in the docker-compose.yaml file, 
# which makes this one image reusable for all three services.
