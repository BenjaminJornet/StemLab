"""
Stem Separator Module
Handles audio stem separation using Demucs with robust error handling
"""

import os
import sys
import shutil
import tempfile
import zipfile
import logging
from typing import Optional, Tuple, List, Callable

import torch
import demucs.separate
import torchaudio
import soundfile as sf

from .audio_converter import (
    convert_to_wav,
    validate_audio_file,
    check_ffmpeg,
    sanitize_filename,
    SUPPORTED_FORMATS
)

logger = logging.getLogger(__name__)

# Monkeypatch torchaudio for better compatibility
def _custom_load(filepath, *args, **kwargs):
    """Custom audio loader using soundfile for better format support"""
    wav, sr = sf.read(filepath)
    wav = torch.tensor(wav).float()
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    else:
        wav = wav.t()
    return wav, sr


def _custom_save(filepath, src, sample_rate, **kwargs):
    """Custom audio saver using soundfile"""
    src = src.detach().cpu().t().numpy()
    sf.write(filepath, src, sample_rate)


# Apply monkeypatch
torchaudio.load = _custom_load
torchaudio.save = _custom_save


def get_device_info() -> str:
    """Get GPU/CPU info for display"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return f"🚀 GPU: {gpu_name} ({vram:.1f} GB VRAM)"
    else:
        return "💻 CPU Mode (Slower processing)"


def is_gpu_available() -> bool:
    """Check if GPU is available for processing"""
    return torch.cuda.is_available()


class StemSeparator:
    """
    Stem separator class using Demucs.
    Handles audio preprocessing, separation, and output organization.
    """
    
    # Available separation modes
    MODES = {
        "2 Stems (Vocals/Instrumental)": {
            "stem_count": 2,
            "model": "htdemucs",
            "two_stems": "vocals"
        },
        "4 Stems (Vocals/Drums/Bass/Other)": {
            "stem_count": 4,
            "model": "htdemucs",
            "two_stems": None
        },
        "6 Stems (Full Separation)": {
            "stem_count": 6,
            "model": "htdemucs_6s",
            "two_stems": None
        },
        "Vocals Only (Ultra Clean)": {
            "stem_count": 2,
            "model": "htdemucs",
            "two_stems": "vocals",
            "filter": lambda f: "vocals" in f.lower()
        },
        "Instrumental Only (Karaoke)": {
            "stem_count": 2,
            "model": "htdemucs",
            "two_stems": "vocals",
            "filter": lambda f: "no_vocals" in f.lower()
        }
    }
    
    # Quality presets
    QUALITY = {
        "Fast": {"shifts": 0, "overlap": 0.1},
        "Balanced": {"shifts": 1, "overlap": 0.25},
        "Best": {"shifts": 2, "overlap": 0.25, "model_upgrade": "htdemucs_ft"}
    }
    
    def __init__(self):
        self.output_dir = None
        self.converted_file = None
        
    def separate(
        self,
        audio_file: str,
        stem_mode: str,
        quality: str,
        output_format: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[Optional[str], str, List[str]]:
        """
        Main separation function with robust error handling.
        
        Args:
            audio_file: Path to input audio file
            stem_mode: Separation mode (see MODES)
            quality: Quality preset (Fast/Balanced/Best)
            output_format: Output format (WAV/MP3)
            progress_callback: Optional callback for progress updates (progress, message)
        
        Returns:
            Tuple of (zip_path, status_message, list_of_stem_paths)
        """
        if audio_file is None:
            return None, "❌ Please upload an audio file first.", []
        
        def update_progress(p: float, msg: str):
            if progress_callback:
                progress_callback(p, msg)
        
        try:
            # Validate input file
            update_progress(0.05, "🔍 Validating audio file...")
            is_valid, validation_msg = validate_audio_file(audio_file)
            if not is_valid:
                return None, f"❌ **Invalid file**: {validation_msg}", []
            
            # Create temp output directory
            self.output_dir = tempfile.mkdtemp(prefix="stemlab_")
            input_path = audio_file
            original_filename = os.path.basename(input_path)
            base_name = os.path.splitext(original_filename)[0]
            safe_base_name = sanitize_filename(base_name)
            
            update_progress(0.1, "🔧 Preparing audio...")
            
            # Convert to WAV if needed
            input_path = self._prepare_audio(input_path, update_progress)
            
            update_progress(0.2, "🤖 Loading AI model...")
            
            # Get mode configuration
            mode_config = self.MODES.get(stem_mode, self.MODES["4 Stems (Vocals/Drums/Bass/Other)"])
            quality_config = self.QUALITY.get(quality, self.QUALITY["Balanced"])
            
            # Determine model
            model = mode_config["model"]
            if quality == "Best" and mode_config["stem_count"] == 4:
                model = quality_config.get("model_upgrade", model)
            
            # Build Demucs arguments
            args = self._build_demucs_args(
                input_path=input_path,
                model=model,
                shifts=quality_config["shifts"],
                overlap=quality_config["overlap"],
                two_stems=mode_config.get("two_stems"),
                output_format=output_format
            )
            
            update_progress(0.3, "🎵 Separating audio (this may take a while)...")
            
            # Run Demucs
            success, error = self._run_demucs(args)
            if not success:
                return None, f"❌ **Processing error**: {error}", []
            
            update_progress(0.8, "📦 Organizing output files...")
            
            # Find and organize output files
            ext = "mp3" if output_format == "MP3 (320kbps)" else "wav"
            stem_filter = mode_config.get("filter")
            
            stem_files, zip_path = self._organize_output(
                model=model,
                safe_base_name=safe_base_name,
                base_name=base_name,
                stem_filter=stem_filter,
                update_progress=update_progress
            )
            
            if not stem_files:
                return None, "❌ **Error**: No stem files were generated.", []
            
            update_progress(1.0, "✅ Complete!")
            
            # Build success message
            device = "GPU" if is_gpu_available() else "CPU"
            message = f"✅ **Separation complete!**\n\n"
            message += f"- **Device**: {device}\n"
            message += f"- **Model**: {model}\n"
            message += f"- **Stems**: {len(stem_files)} files\n"
            message += f"- **Format**: {ext.upper()}\n\n"
            message += "Download your stems using the button below."
            
            return zip_path, message, stem_files
        
        except Exception as e:
            logger.exception(f"Unexpected error in separate: {e}")
            error_msg = str(e)
            if "sys.exit" in error_msg.lower() or "systemexit" in error_msg.lower():
                return None, self._get_file_error_message(), []
            return None, f"❌ **Error**: {error_msg}", []
    
    def _prepare_audio(
        self, 
        input_path: str, 
        update_progress: Callable[[float, str], None]
    ) -> str:
        """Prepare audio file - convert to WAV if needed"""
        has_ffmpeg = check_ffmpeg()
        file_ext = os.path.splitext(input_path)[1].lower()
        
        # Always convert non-WAV files
        needs_conversion = file_ext != '.wav'
        
        if needs_conversion and has_ffmpeg:
            update_progress(0.15, "🔄 Converting audio format...")
            self.converted_file, error = convert_to_wav(input_path, self.output_dir)
            if self.converted_file:
                logger.info(f"Using converted file: {self.converted_file}")
                return self.converted_file
            else:
                logger.warning(f"Conversion failed ({error}), trying original file...")
        elif needs_conversion and not has_ffmpeg:
            logger.warning("FFmpeg not available, processing original file directly")
        
        return input_path
    
    def _build_demucs_args(
        self,
        input_path: str,
        model: str,
        shifts: int,
        overlap: float,
        two_stems: Optional[str],
        output_format: str
    ) -> List[str]:
        """Build Demucs command line arguments"""
        args = [
            "-n", model,
            "--shifts", str(shifts),
            "--overlap", str(overlap),
            "-o", self.output_dir,
            "--filename", "{track}/{stem}.{ext}",
            input_path
        ]
        
        if two_stems:
            args.append(f"--two-stems={two_stems}")
        
        if output_format == "MP3 (320kbps)":
            args.extend(["--mp3", "--mp3-bitrate", "320"])
        
        if not is_gpu_available():
            args.extend(["-d", "cpu"])
        
        return args
    
    def _run_demucs(self, args: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Run Demucs with sys.exit override to prevent crashes.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Override sys.exit to prevent crash
            original_exit = sys.exit
            
            def safe_exit(code=0):
                raise SystemExit(code)
            
            sys.exit = safe_exit
            
            try:
                demucs.separate.main(args)
                return True, None
            except SystemExit as e:
                if e.code != 0:
                    return False, f"Demucs failed with exit code {e.code}. The audio file may be corrupted or in an unsupported format."
                return True, None
            finally:
                sys.exit = original_exit
                
        except Exception as e:
            logger.exception(f"Demucs error: {e}")
            return False, str(e)
    
    def _organize_output(
        self,
        model: str,
        safe_base_name: str,
        base_name: str,
        stem_filter: Optional[Callable[[str], bool]],
        update_progress: Callable[[float, str], None]
    ) -> Tuple[List[str], Optional[str]]:
        """
        Find and organize output files into a ZIP archive.
        
        Returns:
            Tuple of (stem_file_list, zip_path)
        """
        # Find the output directory
        demucs_output = self._find_demucs_output(model, safe_base_name, base_name)
        
        if not demucs_output or not os.path.exists(demucs_output):
            return [], None
        
        final_output = os.path.join(self.output_dir, f"{safe_base_name}_stems")
        os.makedirs(final_output, exist_ok=True)
        
        stem_files = []
        
        for stem_file in os.listdir(demucs_output):
            src = os.path.join(demucs_output, stem_file)
            
            if not os.path.isfile(src):
                continue
            
            # Apply filter if specified
            if stem_filter and not stem_filter(stem_file):
                continue
            
            dst = os.path.join(final_output, stem_file)
            shutil.copy(src, dst)
            stem_files.append(dst)
        
        if not stem_files:
            return [], None
        
        update_progress(0.9, "🗜️ Creating ZIP archive...")
        
        # Create ZIP file
        zip_path = os.path.join(self.output_dir, f"{safe_base_name}_stems.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for stem_file in stem_files:
                zipf.write(stem_file, os.path.basename(stem_file))
        
        return stem_files, zip_path
    
    def _find_demucs_output(
        self, 
        model: str, 
        safe_base_name: str, 
        base_name: str
    ) -> Optional[str]:
        """Find the Demucs output directory"""
        possible_outputs = [
            os.path.join(self.output_dir, model, safe_base_name),
            os.path.join(self.output_dir, model, base_name),
            os.path.join(self.output_dir, model, f"{safe_base_name}_converted"),
        ]
        
        for possible_path in possible_outputs:
            if os.path.exists(possible_path):
                return possible_path
        
        # Search for any directory in the model output
        model_dir = os.path.join(self.output_dir, model)
        if os.path.exists(model_dir):
            subdirs = [d for d in os.listdir(model_dir) 
                      if os.path.isdir(os.path.join(model_dir, d))]
            if subdirs:
                return os.path.join(model_dir, subdirs[0])
        
        return None
    
    def _get_file_error_message(self) -> str:
        """Get a helpful error message for file issues"""
        return (
            "❌ **Error**: The audio file could not be processed.\n\n"
            "**Possible causes:**\n"
            "1. The file is corrupted\n"
            "2. The file extension doesn't match its actual format\n"
            "3. The audio format is not supported\n\n"
            "**Solutions:**\n"
            "1. Try converting the file to WAV using another tool\n"
            "2. Re-download or re-rip the audio file\n"
            "3. Try a different audio file"
        )


# Module-level convenience function
def separate_stems(
    audio_file: str,
    stem_mode: str,
    quality: str,
    output_format: str,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[Optional[str], str, List[str]]:
    """
    Convenience function for stem separation.
    
    Args:
        audio_file: Path to input audio file
        stem_mode: Separation mode
        quality: Quality preset
        output_format: Output format
        progress_callback: Optional progress callback
    
    Returns:
        Tuple of (zip_path, status_message, list_of_stem_paths)
    """
    separator = StemSeparator()
    return separator.separate(
        audio_file=audio_file,
        stem_mode=stem_mode,
        quality=quality,
        output_format=output_format,
        progress_callback=progress_callback
    )
