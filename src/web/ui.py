"""
Gradio UI Module
Handles the web interface for StemLab
"""

import os
import logging
from typing import List, Optional, Tuple

import gradio as gr

from .separator import separate_stems, get_device_info, StemSeparator

logger = logging.getLogger(__name__)


def create_ui() -> gr.Blocks:
    """
    Create the Gradio interface.
    
    Returns:
        Gradio Blocks application
    """
    
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
        
        # Supported formats info
        gr.Markdown(
            """
            **Supported formats**: MP3, WAV, FLAC, OGG, M4A, AAC, WMA, AIFF, OPUS, and more.
            Files are automatically converted for optimal compatibility.
            """
        )
        
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
                    choices=list(StemSeparator.MODES.keys()),
                    value="4 Stems (Vocals/Drums/Bass/Other)",
                    info="Choose how many stems to extract"
                )
                
                quality = gr.Radio(
                    label="Quality",
                    choices=list(StemSeparator.QUALITY.keys()),
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
        
        # Store stems list for preview selection
        stems_state = gr.State([])
        
        def on_separate_full(
            audio: str, 
            mode: str, 
            qual: str, 
            fmt: str, 
            progress: gr.Progress = gr.Progress()
        ) -> Tuple[Optional[str], str, dict, Optional[str], List[str]]:
            """Handle separation with progress updates"""
            
            def progress_callback(p: float, msg: str):
                progress(p, desc=msg)
            
            zip_file, message, stems = separate_stems(
                audio_file=audio,
                stem_mode=mode,
                quality=qual,
                output_format=fmt,
                progress_callback=progress_callback
            )
            
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
        
        def on_stem_select(selected: str, stems: List[str]) -> Optional[str]:
            """Handle stem selection for preview"""
            if selected and stems:
                for s in stems:
                    if os.path.basename(s) == selected:
                        return s
            return None
        
        # Wire up event handlers
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


def launch_app(
    server_name: str = "0.0.0.0",
    server_port: int = 7860,
    share: bool = False
) -> None:
    """
    Launch the Gradio application.
    
    Args:
        server_name: Server hostname
        server_port: Server port
        share: Whether to create a public link
    """
    print("=" * 50)
    print("StemLab Web Interface")
    print("=" * 50)
    print(f"Device: {get_device_info()}")
    print("=" * 50)
    
    app = create_ui()
    
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True,
        favicon_path=None
    )
