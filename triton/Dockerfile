# Use a Triton Inference Server base image with Python backend
FROM nvcr.io/nvidia/tritonserver:24.12-pyt-python-py3

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system packages (optional, but good for troubleshooting)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a directory for the Triton model repository inside the container
WORKDIR /models

# Copy the model repository into the container
# Ensure your local 'model_repository' directory is in the same location as the Dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Triton Inference Server runs on port 8000 (HTTP), 8001 (gRPC), 8002 (Metrics)
EXPOSE 8000
EXPOSE 8001
EXPOSE 8002

# Command to run Triton Inference Server
# --model-repository specifies the path where Triton should look for models
CMD ["tritonserver", "--model-repository=/models"]