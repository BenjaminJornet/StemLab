@echo off
echo ==========================================
echo StemLab Docker - CPU Version
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

REM Set DISPLAY for Windows
set DISPLAY=host.docker.internal:0

REM Create input/output directories if they don't exist
if not exist "input" mkdir input
if not exist "output" mkdir output

echo Building Docker image...
docker-compose -f docker-compose.cpu.yml build

echo.
echo Starting StemLab (CPU)...
echo Placez vos fichiers audio dans le dossier 'input'
echo Les stems seront generes dans le dossier 'output'
echo.
docker-compose -f docker-compose.cpu.yml up

pause
