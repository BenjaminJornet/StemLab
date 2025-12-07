@echo off
echo ==========================================
echo StemLab Docker - GPU Version (NVIDIA CUDA)
echo ==========================================
echo.

REM Check if VcXsrv is running
tasklist /FI "IMAGENAME eq vcxsrv.exe" 2>NUL | find /I /N "vcxsrv.exe">NUL
if %ERRORLEVEL% neq 0 (
    echo [WARNING] VcXsrv n'est pas detecte en cours d'execution.
    echo Pour afficher l'interface graphique, lancez VcXsrv avec:
    echo   - Multiple windows
    echo   - Display number: 0
    echo   - "Disable access control" coche
    echo.
)

REM Check NVIDIA GPU
echo Verification du GPU NVIDIA...
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] GPU NVIDIA non detecte ou NVIDIA Container Toolkit non installe.
    echo Verifiez que:
    echo   1. Docker Desktop a le support GPU active
    echo   2. NVIDIA Container Toolkit est installe
    echo   3. Vos pilotes NVIDIA sont a jour
    echo.
    pause
    exit /b 1
)
echo [OK] GPU NVIDIA detecte!
echo.

REM Set DISPLAY for Windows
set DISPLAY=host.docker.internal:0

REM Create input/output directories if they don't exist
if not exist "input" mkdir input
if not exist "output" mkdir output

echo Building Docker image (GPU)...
docker-compose -f docker-compose.gpu.yml build

echo.
echo Starting StemLab (GPU)...
echo Placez vos fichiers audio dans le dossier 'input'
echo Les stems seront generes dans le dossier 'output'
echo.
docker-compose -f docker-compose.gpu.yml up

pause
