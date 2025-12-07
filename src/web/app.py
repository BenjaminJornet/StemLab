"""
StemLab Web Interface - Gradio Frontend
A clean, modern web interface for AI stem separation
"""

import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple, List
import gradio as gr

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import demucs.separate
import torchaudio
import soundfile as sf

# Monkeypatch torchaudio (same as in splitter.py)
def custom_load(filepath, *args, **kwargs):
    wav, sr = sf.read(filepath)
    wav = torch.tensor(wav).float()
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    else:
        wav = wav.t()
    return wav, sr

def custom_save(filepath, src, sample_rate, **kwargs):
    src = src.detach().cpu().t().numpy()
    sf.write(filepath, src, sample_rate)

torchaudio.load = custom_load
torchaudio.save = custom_save


def get_device_info() -> str:
    """Get GPU/CPU info for display"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return f"🚀 GPU: {gpu_name} ({vram:.1f} GB VRAM)"
    else:
        return "💻 CPU Mode (Slower processing)"


def separate_stems(
    audio_file: str,
    stem_mode: str,
    quality: str,
    output_format: str,
    progress: gr.Progress = gr.Progress()
) -> Tuple[Optional[str], str, List[str]]:
    """
    Main separation function
    
    Returns:
        - Path to zip file with stems
        - Status message
        - List of individual stem paths for preview
    """
    if audio_file is None:
        return None, "❌ Please upload an audio file first.", []
    
    try:
        # Create temp output directory
        output_dir = tempfile.mkdtemp(prefix="stemlab_")
        input_path = audio_file
        filename = os.path.basename(input_path)
        base_name = os.path.splitext(filename)[0]
        
        progress(0.1, desc="🔧 Preparing...")
        
        # Determine model and settings based on stem mode
        stem_count = 4
        model = "htdemucs"
        two_stems = None
        
        if stem_mode == "2 Stems (Vocals/Instrumental)":
            stem_count = 2
            two_stems = "vocals"
        elif stem_mode == "4 Stems (Vocals/Drums/Bass/Other)":
            stem_count = 4
            model = "htdemucs"
        elif stem_mode == "6 Stems (Full Separation)":
            stem_count = 6
            model = "htdemucs_6s"
        elif stem_mode == "Vocals Only (Ultra Clean)":
            stem_count = 2
            two_stems = "vocals"
        elif stem_mode == "Instrumental Only (Karaoke)":
            stem_count = 2
            two_stems = "vocals"
        
        # Quality settings
        shifts = 1
        overlap = 0.25
        
        if quality == "Fast":
            shifts = 0
            overlap = 0.1
        elif quality == "Best":
            if stem_count == 4:
                model = "htdemucs_ft"
            shifts = 2
            overlap = 0.25
        
        progress(0.2, desc="🤖 Loading AI model...")
        
        # Build Demucs arguments
        args = [
            "-n", model,
            "--shifts", str(shifts),
            "--overlap", str(overlap),
            "-o", output_dir,
            "--filename", "{track}/{stem}.{ext}",
            input_path
        ]
        
        if two_stems:
            args.append(f"--two-stems={two_stems}")
        
        if output_format == "MP3 (320kbps)":
            args.extend(["--mp3", "--mp3-bitrate", "320"])
        
        if not torch.cuda.is_available():
            args.extend(["-d", "cpu"])
        
        progress(0.3, desc="🎵 Separating audio (this may take a while)...")
        
        # Run Demucs
        demucs.separate.main(args)
        
        progress(0.8, desc="📦 Organizing output files...")
        
        # Find and organize output files
        ext = "mp3" if output_format == "MP3 (320kbps)" else "wav"
        demucs_output = os.path.join(output_dir, model, base_name)
        final_output = os.path.join(output_dir, f"{base_name}_stems")
        os.makedirs(final_output, exist_ok=True)
        
        stem_files = []
        
        if os.path.exists(demucs_output):
            for stem_file in os.listdir(demucs_output):
                src = os.path.join(demucs_output, stem_file)
                
                # Filter for specific modes
                if stem_mode == "Vocals Only (Ultra Clean)" and "vocals" not in stem_file.lower():
                    continue
                if stem_mode == "Instrumental Only (Karaoke)" and "vocals" in stem_file.lower():
                    # For karaoke, we want "no_vocals" which is the instrumental
                    if "no_vocals" not in stem_file.lower():
                        continue
                
                dst = os.path.join(final_output, stem_file)
                shutil.copy(src, dst)
                stem_files.append(dst)
        
        progress(0.9, desc="🗜️ Creating ZIP archive...")
        
        # Create ZIP file
        zip_path = os.path.join(output_dir, f"{base_name}_stems.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for stem_file in stem_files:
                zipf.write(stem_file, os.path.basename(stem_file))
        
        progress(1.0, desc="✅ Complete!")
        
        # Build success message
        device = "GPU" if torch.cuda.is_available() else "CPU"
        message = f"✅ **Separation complete!**\n\n"
        message += f"- **Device**: {device}\n"
        message += f"- **Model**: {model}\n"
        message += f"- **Stems**: {len(stem_files)} files\n"
        message += f"- **Format**: {ext.upper()}\n\n"
        message += "Download your stems using the button below."
        
        return zip_path, message, stem_files
        
    except Exception as e:
        return None, f"❌ **Error**: {str(e)}", []


def create_ui():
    """Create the Gradio interface"""
    
    with gr.Blocks(
        title="StemLab - AI Stem Separation"
    ) as app:
        
        # Header
        gr.Markdown(
            """
            # 🎵 StemLab
            ### Professional AI Stem Separation
            
            Separate your audio tracks into individual stems using state-of-the-art AI models.
            """
        )
        
        # Device info
        device_info = get_device_info()
        gr.Markdown(f"**{device_info}**")
        
        gr.Markdown("---")
        
        with gr.Row():
            # Left column - Input
            with gr.Column(scale=1):
                gr.Markdown("### 📁 Input")
                
                audio_input = gr.Audio(
                    label="Upload Audio File",
                    type="filepath",
                    sources=["upload"],
                )
                
                gr.Markdown("### ⚙️ Settings")
                
                stem_mode = gr.Dropdown(
                    label="Separation Mode",
                    choices=[
                        "2 Stems (Vocals/Instrumental)",
                        "4 Stems (Vocals/Drums/Bass/Other)",
                        "6 Stems (Full Separation)",
                        "Vocals Only (Ultra Clean)",
                        "Instrumental Only (Karaoke)"
                    ],
                    value="4 Stems (Vocals/Drums/Bass/Other)",
                    info="Choose how many stems to extract"
                )
                
                quality = gr.Radio(
                    label="Quality",
                    choices=["Fast", "Balanced", "Best"],
                    value="Balanced",
                    info="Higher quality = longer processing time"
                )
                
                output_format = gr.Radio(
                    label="Output Format",
                    choices=["WAV (Lossless)", "MP3 (320kbps)"],
                    value="WAV (Lossless)",
                    info="WAV for maximum quality, MP3 for smaller files"
                )
                
                separate_btn = gr.Button(
                    "🚀 Separate Stems",
                    variant="primary",
                    size="lg"
                )
            
            # Right column - Output
            with gr.Column(scale=1):
                gr.Markdown("### 📤 Output")
                
                status_output = gr.Markdown(
                    value="Upload an audio file and click 'Separate Stems' to begin.",
                    label="Status"
                )
                
                download_output = gr.File(
                    label="Download Stems (ZIP)",
                    visible=True
                )
                
                gr.Markdown("### 🎧 Preview Stems")
                
                with gr.Accordion("Preview individual stems", open=False):
                    preview_audio = gr.Audio(
                        label="Stem Preview",
                        type="filepath",
                        interactive=False
                    )
                    stem_selector = gr.Dropdown(
                        label="Select stem to preview",
                        choices=[],
                        interactive=True
                    )
        
        # Footer
        gr.Markdown("---")
        gr.Markdown(
            """
            **StemLab** - Powered by [Demucs](https://github.com/facebookresearch/demucs) by Meta AI
            
            Built with ❤️ by Sunsets Acoustic
            """
        )
        
        # Event handlers
        def on_separate(audio, mode, qual, fmt, progress=gr.Progress()):
            zip_file, message, stems = separate_stems(audio, mode, qual, fmt, progress)
            
            # Update stem selector choices
            if stems:
                stem_names = [os.path.basename(s) for s in stems]
                return zip_file, message, gr.update(choices=stem_names, value=stem_names[0] if stem_names else None), stems[0] if stems else None
            return zip_file, message, gr.update(choices=[]), None
        
        # Store stems list for preview selection
        stems_state = gr.State([])
        
        def on_separate_full(audio, mode, qual, fmt, progress=gr.Progress()):
            zip_file, message, stems = separate_stems(audio, mode, qual, fmt, progress)
            
            if stems:
                stem_names = [os.path.basename(s) for s in stems]
                return (
                    zip_file, 
                    message, 
                    gr.update(choices=stem_names, value=stem_names[0] if stem_names else None), 
                    stems[0] if stems else None,
                    stems
                )
            return zip_file, message, gr.update(choices=[]), None, []
        
        def on_stem_select(selected, stems):
            if selected and stems:
                for s in stems:
                    if os.path.basename(s) == selected:
                        return s
            return None
        
        separate_btn.click(
            fn=on_separate_full,
            inputs=[audio_input, stem_mode, quality, output_format],
            outputs=[download_output, status_output, stem_selector, preview_audio, stems_state],
            show_progress=True
        )
        
        stem_selector.change(
            fn=on_stem_select,
            inputs=[stem_selector, stems_state],
            outputs=[preview_audio]
        )
    
    return app


def main():
    """Main entry point for web interface"""
    print("=" * 50)
    print("StemLab Web Interface")
    print("=" * 50)
    print(f"Device: {get_device_info()}")
    print("=" * 50)
    
    app = create_ui()
    
    # Launch with settings optimized for Docker
    app.launch(
        server_name="0.0.0.0",  # Bind to all interfaces
        server_port=7860,
        share=False,
        show_error=True,
        favicon_path=None
    )


if __name__ == "__main__":
    main()
