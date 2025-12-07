# StemLab v1.0

**Professional-grade AI stem separation. Local. Unlimited. One-time payment.**

StemLab is a powerful, local Windows application for separating audio tracks into individual stems (Vocals, Drums, Bass, Other). It leverages state-of-the-art AI models (Demucs and MDX-Net) to deliver studio-quality results without monthly subscriptions or cloud upload limits.

![StemLab Splash](resources/splash.png)

## Features

*   **100% Offline & Local**: No data leaves your machine. Privacy guaranteed.
*   **Unlimited Usage**: No credits, no timers, no subscriptions.
*   **Advanced AI Models**:
    *   **Hybrid Ensemble**: Combines `Demucs` (for instrument separation) and `MDX-Net` (for ultra-clean vocals).
    *   **De-Reverb & De-Echo**: Experimental post-processing to remove room ambiance.
*   **Multiple Stem Modes**:
    *   **2-Stem**: Vocals / Instrumental
    *   **4-Stem**: Vocals, Drums, Bass, Other
    *   **6-Stem**: Vocals, Drums, Bass, Guitar, Piano, Other
    *   **Vocals Only (Ultra Clean)**: Specialized pipeline for the cleanest possible acapellas.
    *   **Instrumental / Karaoke**: High-quality backing tracks.
*   **Professional Workflow**:
    *   **Batch Processing**: Drag & drop multiple files.
    *   **Format Support**: Export as WAV (Lossless) or MP3 (320kbps).
    *   **GPU Acceleration**: Auto-detects NVIDIA GPUs for faster processing. (Testing)
    *   **Smart Queue**: Manage your jobs with progress bars and cancellation.
*   **🐳 Docker Support**: Run without any local Python installation (CPU or GPU).

## Project Structure

```
StemLab/
├── main.py                 # Desktop application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Universal Docker image (auto GPU/CPU)
├── Dockerfile.cpu          # Docker image (CPU only)
├── Dockerfile.gpu          # Docker image (GPU/CUDA only)
├── docker-compose.yml      # Universal Docker Compose (auto GPU/CPU)
├── docker-compose.cpu.yml  # Docker Compose for CPU
├── docker-compose.gpu.yml  # Docker Compose for GPU
├── src/
│   ├── core/               # Audio processing core
│   │   ├── advanced_audio.py
│   │   ├── gpu_utils.py
│   │   └── splitter.py
│   ├── ui/                 # Desktop PyQt6 interface
│   │   ├── main_window.py
│   │   ├── splash.py
│   │   ├── style.py
│   │   └── widgets.py
│   ├── web/                # Web interface (Gradio)
│   │   └── app.py
│   └── utils/
│       └── logger.py
├── scripts/                # Build and run scripts
│   ├── docker-run.ps1      # Windows Docker launcher (auto GPU)
│   ├── docker-run.sh       # Linux/Mac Docker launcher (auto GPU)
│   ├── build_cpu.bat
│   ├── build_gpu.bat
│   └── run_cpu.bat
├── docs/                   # Documentation
│   └── DOCKER.md
├── resources/
│   └── splash.png
├── input/                  # (Docker) Place audio files here
├── output/                 # (Docker) Generated stems appear here
└── tests/
    └── test_splitter.py
```

## Requirements

*   **OS**: Windows 10 or 11 (64-bit)
*   **RAM**: 8GB minimum (16GB recommended)
*   **GPU (Optional)**: NVIDIA GPU with 4GB+ VRAM for accelerated processing. (Runs on CPU if no GPU is found).
*   **Python**: Python 3.10 (for building from source).
*   **Docker** (Optional): For containerized usage without local Python installation.

## Installation

### Option 1: Pre-built Executable
Purchase the ready-to-run `StemLab.exe` from **[Gumroad](https://justinmurray99.gumroad.com/l/StemLab)**.
(Instant download, no setup required).

### Option 2: Docker (Recommended)

Run StemLab without installing Python locally. Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

#### 🚀 Quick Start (Automatic GPU Detection)

**Windows (PowerShell):**
```powershell
.\scripts\docker-run.ps1
```

**Linux / macOS:**
```bash
chmod +x scripts/docker-run.sh
./scripts/docker-run.sh
```

The launcher automatically detects if you have an NVIDIA GPU and configures accordingly.

#### Manual Launch

```bash
# Auto-detect GPU/CPU
docker-compose up --build

# Force GPU mode
USE_GPU=true docker-compose --profile gpu up --build -d stemlab-gpu

# Force CPU mode
USE_GPU=false docker-compose up --build -d stemlab
```

#### 🌐 Web Interface

Open your browser at: **http://localhost:7860**

No VNC client needed - it's a clean web interface!

📖 See [docs/DOCKER.md](docs/DOCKER.md) for detailed Docker documentation.

### Option 3: Build from Source

If you want to modify the code or build it yourself, follow these steps:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/sunsetsacoustic/StemLab.git
    cd StemLab
    ```

2.  **Install Python 3.10**:
    Ensure you have Python 3.10 installed and added to your PATH.

3.  **Run the Build Script**:
    We provide a robust build script that handles virtual environment creation and dependency installation automatically.

    Double-click **`scripts/rebuild_cpu_robust.bat`**.

    This script will:
    *   Create a local virtual environment (`venv_cpu`).
    *   Install all required libraries (`PyQt6`, `torch`, `demucs`, `audio-separator`, etc.).
    *   Package the application into a single `.exe` file using PyInstaller.

4.  **Run the App**:
    *   **From Source**: Double-click `scripts/run_cpu.bat`.
    *   **Compiled EXE**: Check the `dist` folder for `StemLab.exe`.

## Usage

### Web Interface (Docker)

1. Open your browser at **http://localhost:7860**
2. **Upload** your audio file (drag & drop or click)
3. Select your separation mode (2-stem, 4-stem, 6-stem, etc.)
4. Choose quality settings (Fast, Balanced, Best)
5. Choose output format (WAV or MP3)
6. Click **🚀 Separate Stems**
7. Download your stems as a ZIP file

### Desktop Application

1. Launch `StemLab.exe` or run from source
2. **Drag & drop** audio files into the application window
3. Configure options and click **Start**

## Platform Support

| Platform | GPU Support | Notes |
|----------|-------------|-------|
| Windows + NVIDIA GPU | ✅ CUDA | Automatic detection |
| Windows (CPU only) | ✅ CPU | Automatic fallback |
| Linux + NVIDIA GPU | ✅ CUDA | Requires NVIDIA Container Toolkit |
| Linux (CPU only) | ✅ CPU | Automatic fallback |
| macOS Intel | ✅ CPU | GPU not supported in Docker |
| macOS Apple Silicon | ✅ CPU | MPS not available in Docker |

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/docker-run.ps1` | **Windows**: Auto-detect GPU and launch Docker |
| `scripts/docker-run.sh` | **Linux/Mac**: Auto-detect GPU and launch Docker |
| `scripts/build_cpu.bat` | Build EXE with CPU-only PyTorch |
| `scripts/build_gpu.bat` | Build EXE with CUDA GPU support |
| `scripts/run_cpu.bat` | Run from source (CPU) |

## Credits

*   **Demucs** by Meta Research
*   **Audio Separator** (MDX-Net implementation)
*   **PyQt6** for the User Interface

---
*Built with ❤️ by Sunsets Acoustic*
