#!/bin/bash
set -e

echo "==================================="
echo "StemLab Docker Container Starting"
echo "==================================="

# Check for GPU
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "Running in CPU mode"
fi

echo "==================================="
echo "Starting StemLab Web Interface..."
echo "Access the UI at: http://localhost:7860"
echo "==================================="

# Launch Gradio web interface
exec python -m src.web.app
