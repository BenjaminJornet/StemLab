#!/bin/bash
#
# StemLab Docker Launcher - Automatic GPU Detection
# Automatically detects NVIDIA GPU and launches StemLab with appropriate configuration
#
# Usage:
#   ./docker-run.sh          # Auto-detect GPU
#   ./docker-run.sh --gpu    # Force GPU mode
#   ./docker-run.sh --cpu    # Force CPU mode
#   ./docker-run.sh --down   # Stop containers
#   ./docker-run.sh --build  # Force rebuild

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  StemLab Docker Launcher${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Parse arguments
FORCE_GPU=false
FORCE_CPU=false
BUILD=false
DOWN=false

for arg in "$@"; do
    case $arg in
        --gpu)
            FORCE_GPU=true
            ;;
        --cpu)
            FORCE_CPU=true
            ;;
        --build)
            BUILD=true
            ;;
        --down)
            DOWN=true
            ;;
    esac
done

# Stop containers if requested
if [ "$DOWN" = true ]; then
    echo -e "${YELLOW}Stopping StemLab containers...${NC}"
    docker-compose down 2>/dev/null || true
    docker-compose --profile gpu down 2>/dev/null || true
    echo -e "${GREEN}Containers stopped.${NC}"
    exit 0
fi

# Create input/output directories
mkdir -p input output

# Detect GPU
USE_GPU=false
GPU_NAME=""

if [ "$FORCE_CPU" = true ]; then
    echo -e "${YELLOW}[MODE] Forced CPU mode${NC}"
    USE_GPU=false
elif [ "$FORCE_GPU" = true ]; then
    echo -e "${YELLOW}[MODE] Forced GPU mode${NC}"
    USE_GPU=true
else
    echo -e "Detecting GPU..."
    
    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        # nvidia-smi exists on host
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)
        if [ -n "$GPU_NAME" ]; then
            USE_GPU=true
            echo -e "${GREEN}[GPU DETECTED] $GPU_NAME${NC}"
        fi
    else
        # Try via Docker
        GPU_NAME=$(docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1) || true
        if [ -n "$GPU_NAME" ]; then
            USE_GPU=true
            echo -e "${GREEN}[GPU DETECTED] $GPU_NAME${NC}"
        else
            echo -e "${YELLOW}[NO GPU] Running in CPU mode${NC}"
        fi
    fi
    
    # Check for Apple Silicon (MPS)
    if [ "$(uname)" = "Darwin" ]; then
        if [ "$(uname -m)" = "arm64" ]; then
            echo -e "${YELLOW}[APPLE SILICON] Detected, using CPU mode (MPS not supported in Docker)${NC}"
            USE_GPU=false
        fi
    fi
fi

# Export environment variable
export USE_GPU=$USE_GPU

echo ""
echo -e "${CYAN}Configuration:${NC}"
echo -e "  - Mode: $([ "$USE_GPU" = true ] && echo 'GPU (CUDA)' || echo 'CPU')"
echo -e "  - Web UI: http://localhost:7860"
echo ""

# Build if requested or image doesn't exist
IMAGE_NAME="stemlab:$([ "$USE_GPU" = true ] && echo 'true' || echo 'cpu')"
IMAGE_EXISTS=$(docker images -q "$IMAGE_NAME" 2>/dev/null)

if [ "$BUILD" = true ] || [ -z "$IMAGE_EXISTS" ]; then
    echo -e "${YELLOW}Building Docker image...${NC}"
    docker-compose build --build-arg USE_GPU=$USE_GPU
fi

# Run the container
echo -e "${GREEN}Starting StemLab...${NC}"

docker-compose up -d stemlab

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  StemLab is running!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "  Open your browser at:"
    echo -e "  -> ${CYAN}http://localhost:7860${NC}"
    echo ""
    echo -e "  To stop: ./docker-run.sh --down"
    echo ""
    
    # Wait and show logs
    sleep 5
    echo -e "Container logs:"
    docker logs stemlab --tail 10 2>/dev/null || true
else
    echo -e "${RED}Failed to start container!${NC}"
    exit 1
fi
