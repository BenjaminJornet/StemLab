<#
.SYNOPSIS
    StemLab Docker Launcher - Automatic GPU Detection
.DESCRIPTION
    Automatically detects NVIDIA GPU and launches StemLab with appropriate configuration
.EXAMPLE
    .\docker-run.ps1
    .\docker-run.ps1 -ForceGPU
    .\docker-run.ps1 -ForceCPU
#>

param(
    [switch]$ForceGPU,
    [switch]$ForceCPU,
    [switch]$Build,
    [switch]$Down
)

$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  StemLab Docker Launcher" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Stop container if requested
if ($Down) {
    Write-Host "Stopping StemLab containers..." -ForegroundColor Yellow
    docker-compose down 2>$null
    docker-compose --profile gpu down 2>$null
    Write-Host "Containers stopped." -ForegroundColor Green
    exit 0
}

# Create input/output directories
if (-not (Test-Path "input")) { New-Item -ItemType Directory -Path "input" -Force | Out-Null }
if (-not (Test-Path "output")) { New-Item -ItemType Directory -Path "output" -Force | Out-Null }

# Detect GPU
$UseGPU = $false
$GPUName = ""

if ($ForceCPU) {
    Write-Host "[MODE] Forced CPU mode" -ForegroundColor Yellow
    $UseGPU = $false
} elseif ($ForceGPU) {
    Write-Host "[MODE] Forced GPU mode" -ForegroundColor Yellow
    $UseGPU = $true
} else {
    Write-Host "Detecting GPU..." -ForegroundColor Gray
    
    # Check if nvidia-smi is available
    try {
        $nvidiaCheck = docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
        if ($LASTEXITCODE -eq 0 -and $nvidiaCheck) {
            $UseGPU = $true
            $GPUName = $nvidiaCheck.Trim()
            Write-Host "[GPU DETECTED] $GPUName" -ForegroundColor Green
        } else {
            Write-Host "[NO GPU] Running in CPU mode" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[NO GPU] NVIDIA drivers not found, running in CPU mode" -ForegroundColor Yellow
    }
}

# Set environment variable
$env:USE_GPU = if ($UseGPU) { "true" } else { "false" }

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  - Mode: $(if ($UseGPU) { 'GPU (CUDA)' } else { 'CPU' })" -ForegroundColor White
Write-Host "  - Web UI: http://localhost:7860" -ForegroundColor White
Write-Host ""

# Build if requested or image doesn't exist
$imageName = "stemlab:$(if ($UseGPU) { 'true' } else { 'cpu' })"
$imageExists = docker images -q $imageName 2>$null

if ($Build -or -not $imageExists) {
    Write-Host "Building Docker image..." -ForegroundColor Yellow
    docker-compose build --build-arg USE_GPU=$env:USE_GPU
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
}

# Run with appropriate profile
Write-Host "Starting StemLab..." -ForegroundColor Green

docker-compose up -d stemlab

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  StemLab is running!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Open your browser at:" -ForegroundColor White
    Write-Host "  -> http://localhost:7860" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  To stop: .\docker-run.ps1 -Down" -ForegroundColor Gray
    Write-Host ""
    
    # Wait a bit and show logs
    Start-Sleep -Seconds 5
    Write-Host "Container logs:" -ForegroundColor Gray
    docker logs stemlab --tail 10 2>$null
} else {
    Write-Host "Failed to start container!" -ForegroundColor Red
    exit 1
}
