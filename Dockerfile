# StemLab - Universal Dockerfile
# Automatically adapts to GPU (NVIDIA CUDA) or CPU mode
# Build with: docker build --build-arg USE_GPU=true -t stemlab .

ARG USE_GPU=false

# ============================================
# GPU Base Image
# ============================================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS base-true

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# ============================================
# CPU Base Image
# ============================================
FROM python:3.10-slim-bookworm AS base-false

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================
# Select base based on USE_GPU argument
# ============================================
FROM base-${USE_GPU} AS base

# ============================================
# Common setup
# ============================================
LABEL maintainer="Sunsets Acoustic"
LABEL description="StemLab - AI Stem Separation (Universal)"
LABEL version="2.1"

ARG USE_GPU=false
ENV USE_GPU=${USE_GPU}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    soundfile \
    pydub \
    numpy \
    gradio

# Install PyTorch - GPU or CPU version
RUN if [ "$USE_GPU" = "true" ]; then \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    else \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Install Demucs and audio-separator
RUN if [ "$USE_GPU" = "true" ]; then \
        pip install --no-cache-dir demucs "audio-separator[gpu]" onnxruntime-gpu; \
    else \
        pip install --no-cache-dir demucs audio-separator onnxruntime; \
    fi

# Copy application source code
COPY main.py .
COPY src/ ./src/
COPY resources/ ./resources/
COPY start.sh /app/start.sh

# Make start script executable and fix line endings
RUN chmod +x /app/start.sh && \
    sed -i 's/\r$//' /app/start.sh

# Create directories for input/output
RUN mkdir -p /data/input /data/output

# Environment for CUDA (only used if GPU is available)
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Volume for audio files
VOLUME ["/data/input", "/data/output"]

# Expose Gradio port
EXPOSE 7860

# Default command
CMD ["/bin/bash", "/app/start.sh"]
