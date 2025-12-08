"""
StemLab Web Interface - Main Entry Point
A clean, modern web interface for AI stem separation

This module serves as the main entry point for the web application.
The application is modularly organized into:
- audio_converter.py: FFmpeg-based audio conversion
- separator.py: Demucs stem separation logic
- ui.py: Gradio web interface
"""

import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main entry point for web interface"""
    from .ui import launch_app
    
    # Get configuration from environment
    server_name = os.environ.get("STEMLAB_HOST", "0.0.0.0")
    server_port = int(os.environ.get("STEMLAB_PORT", "7860"))
    share = os.environ.get("STEMLAB_SHARE", "false").lower() == "true"
    
    launch_app(
        server_name=server_name,
        server_port=server_port,
        share=share
    )


if __name__ == "__main__":
    main()
