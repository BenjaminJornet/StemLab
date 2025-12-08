"""
Audio Converter Module
Handles audio file conversion using FFmpeg with robust error handling
"""

import os
import subprocess
import logging
import json
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Supported audio formats (input)
SUPPORTED_FORMATS = {
    '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.m4p', '.aac', '.wma', 
    '.aiff', '.aif', '.opus', '.webm', '.mp4', '.mkv', '.avi',
    '.mov', '.ape', '.wv', '.mpc', '.tta', '.dts', '.ac3', '.m4b', '.m4r'
}


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def check_ffprobe() -> bool:
    """Check if FFprobe is available"""
    try:
        result = subprocess.run(
            ['ffprobe', '-version'], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def get_audio_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get audio file information using FFprobe.
    
    Returns:
        Dictionary with audio info or None if failed
    """
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Could not get audio info: {e}")
    return None


def detect_real_format(file_path: str) -> Optional[str]:
    """
    Detect the real audio format of a file using FFprobe.
    Useful when file extension doesn't match actual format.
    
    Returns:
        Detected codec name or None
    """
    info = get_audio_info(file_path)
    if info and 'streams' in info:
        for stream in info['streams']:
            if stream.get('codec_type') == 'audio':
                return stream.get('codec_name')
    return None


def sanitize_filename(filename: str) -> str:
    """
    Clean filename by removing special characters that might cause issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem operations
    """
    safe_name = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).strip()
    return safe_name if safe_name else "audio"


def convert_to_wav(
    input_path: str, 
    output_dir: str,
    sample_rate: int = 44100,
    channels: int = 2,
    bit_depth: int = 16
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert any audio file to WAV format using FFmpeg.
    Uses multiple fallback strategies for maximum compatibility.
    
    Args:
        input_path: Path to input audio file
        output_dir: Directory for output file
        sample_rate: Output sample rate (default 44100)
        channels: Number of channels (default 2 for stereo)
        bit_depth: Bit depth (default 16)
    
    Returns:
        Tuple of (converted_file_path, error_message)
    """
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    safe_name = sanitize_filename(base_name)
    output_path = os.path.join(output_dir, f"{safe_name}_converted.wav")
    
    # Strategy 1: Standard conversion
    strategies = [
        # Strategy 1: Standard high-quality conversion
        {
            'name': 'standard',
            'cmd': [
                'ffmpeg', '-y', '-i', input_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                output_path
            ]
        },
        # Strategy 2: Force format detection (for misnamed files)
        {
            'name': 'force_decode',
            'cmd': [
                'ffmpeg', '-y',
                '-err_detect', 'ignore_err',  # Ignore errors
                '-i', input_path,
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                output_path
            ]
        },
        # Strategy 3: Re-encode with error correction
        {
            'name': 'error_correction',
            'cmd': [
                'ffmpeg', '-y',
                '-err_detect', 'ignore_err',
                '-fflags', '+genpts+igndts',
                '-i', input_path,
                '-vn',
                '-af', 'aresample=async=1000',  # Resample to fix sync issues
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                output_path
            ]
        },
        # Strategy 4: Raw PCM extraction (last resort)
        {
            'name': 'raw_extraction',
            'cmd': [
                'ffmpeg', '-y',
                '-err_detect', 'ignore_err',
                '-fflags', '+genpts+igndts+discardcorrupt',
                '-i', input_path,
                '-vn',
                '-af', 'aresample=async=1:min_hard_comp=0.100000:first_pts=0',
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                output_path
            ]
        }
    ]
    
    last_error = None
    
    for strategy in strategies:
        try:
            logger.info(f"Trying conversion strategy: {strategy['name']}")
            
            result = subprocess.run(
                strategy['cmd'],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for long files
            )
            
            # Check if output exists and is valid
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 44100:  # At least 1 second of audio at minimum
                    # Verify the file is valid using ffprobe
                    verify_result = subprocess.run(
                        ['ffprobe', '-v', 'error', output_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if verify_result.returncode == 0:
                        logger.info(f"Conversion successful with strategy '{strategy['name']}': {output_path} ({file_size} bytes)")
                        return output_path, None
                    else:
                        logger.warning(f"Strategy '{strategy['name']}' produced invalid output")
                else:
                    logger.warning(f"Strategy '{strategy['name']}' produced too small file: {file_size} bytes")
                    # Remove invalid output
                    os.remove(output_path)
            
            last_error = result.stderr if result.stderr else "No output produced"
            
        except subprocess.TimeoutExpired:
            last_error = f"Strategy '{strategy['name']}' timed out"
            logger.warning(last_error)
        except Exception as e:
            last_error = f"Strategy '{strategy['name']}' failed: {str(e)}"
            logger.warning(last_error)
    
    # All strategies failed
    logger.error(f"All conversion strategies failed. Last error: {last_error}")
    return None, f"Audio conversion failed: {last_error[:200] if last_error else 'Unknown error'}"


def validate_audio_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate that the audio file can be processed.
    
    Args:
        file_path: Path to audio file
    
    Returns:
        Tuple of (is_valid, message)
    """
    if not file_path:
        return False, "No file provided"
    
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    file_size = os.path.getsize(file_path)
    if file_size < 1000:
        return False, "File is too small (likely corrupted or empty)"
    
    # Check file size limit (2GB)
    max_size = 2 * 1024 * 1024 * 1024
    if file_size > max_size:
        return False, f"File is too large (max 2GB, got {file_size / (1024**3):.1f}GB)"
    
    # Get extension
    ext = os.path.splitext(file_path)[1].lower()
    
    # Accept any extension but warn for unknown ones
    if ext not in SUPPORTED_FORMATS:
        logger.warning(f"Unknown audio format: {ext}, will attempt conversion")
    
    # Try to probe the file
    if check_ffprobe():
        info = get_audio_info(file_path)
        if info is None:
            return False, "File could not be read - may be corrupted"
        
        # Check for audio streams
        has_audio = False
        if 'streams' in info:
            for stream in info['streams']:
                if stream.get('codec_type') == 'audio':
                    has_audio = True
                    break
        
        if not has_audio:
            return False, "No audio stream found in file"
    
    return True, "File validated"


def get_audio_duration(file_path: str) -> Optional[float]:
    """
    Get the duration of an audio file in seconds.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Duration in seconds or None if failed
    """
    info = get_audio_info(file_path)
    if info and 'format' in info:
        try:
            return float(info['format'].get('duration', 0))
        except (ValueError, TypeError):
            pass
    return None
