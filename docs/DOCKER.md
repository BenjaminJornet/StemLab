# StemLab Docker Guide

## 🚀 Quick Start

StemLab Docker détecte automatiquement votre GPU et configure l'environnement approprié.

### Windows (PowerShell)
```powershell
.\scripts\docker-run.ps1
```

### Linux / macOS
```bash
chmod +x scripts/docker-run.sh
./scripts/docker-run.sh
```

Puis ouvrez votre navigateur à : **http://localhost:7860**

## Prérequis

### Minimum
- Docker Desktop installé et fonctionnel

### Pour l'accélération GPU
- NVIDIA GPU avec pilotes récents
- NVIDIA Container Toolkit installé
- Docker Desktop avec support GPU activé

## Options de lancement

### Script automatique (recommandé)

```powershell
# Windows - Détection auto
.\scripts\docker-run.ps1

# Forcer le mode GPU
.\scripts\docker-run.ps1 -ForceGPU

# Forcer le mode CPU
.\scripts\docker-run.ps1 -ForceCPU

# Reconstruire l'image
.\scripts\docker-run.ps1 -Build

# Arrêter les conteneurs
.\scripts\docker-run.ps1 -Down
```

```bash
# Linux/Mac - Détection auto
./scripts/docker-run.sh

# Forcer le mode GPU
./scripts/docker-run.sh --gpu

# Forcer le mode CPU
./scripts/docker-run.sh --cpu

# Reconstruire l'image
./scripts/docker-run.sh --build

# Arrêter les conteneurs
./scripts/docker-run.sh --down
```

### Docker Compose manuel

```bash
# Avec détection automatique
docker-compose up --build

# Forcer GPU
USE_GPU=true docker-compose --profile gpu up --build -d stemlab-gpu

# Forcer CPU
USE_GPU=false docker-compose up --build -d stemlab
```

### Anciennes configurations (toujours disponibles)

```bash
# GPU uniquement
docker-compose -f docker-compose.gpu.yml up --build

# CPU uniquement
docker-compose -f docker-compose.cpu.yml up --build
```

## Interface Web

L'interface est accessible à **http://localhost:7860**

Fonctionnalités :
- Upload par glisser-déposer
- Choix du mode de séparation (2, 4, 6 stems)
- Choix de la qualité (Fast, Balanced, Best)
- Format de sortie (WAV ou MP3)
- Téléchargement ZIP des stems
- Prévisualisation audio

## Volumes de données

- `./input/` : Placez vos fichiers audio ici (optionnel, vous pouvez aussi uploader via l'interface)
- `./output/` : Les stems générés seront ici

## Dépannage

### GPU non détecté

1. Vérifiez que Docker Desktop a le support GPU activé
2. Testez : `docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi`
3. Installez NVIDIA Container Toolkit si nécessaire

### L'interface ne s'affiche pas

1. Vérifiez que le conteneur tourne : `docker ps`
2. Vérifiez les logs : `docker logs stemlab`
3. Essayez un autre port : modifiez `7860:7860` dans docker-compose.yml

### Erreurs de mémoire

Pour les fichiers audio longs, augmentez la mémoire Docker :
- Docker Desktop > Settings > Resources > Memory

### Apple Silicon (M1/M2/M3)

Les Mac Apple Silicon utilisent automatiquement le mode CPU car CUDA n'est pas supporté.
MPS (Metal Performance Shaders) n'est pas disponible dans Docker.

## Architecture des fichiers Docker

```
StemLab/
├── Dockerfile              # Image universelle (auto GPU/CPU)
├── Dockerfile.cpu          # Image CPU uniquement
├── Dockerfile.gpu          # Image GPU uniquement
├── docker-compose.yml      # Config universelle (auto GPU/CPU)
├── docker-compose.cpu.yml  # Config CPU uniquement
├── docker-compose.gpu.yml  # Config GPU uniquement
├── scripts/
│   ├── docker-run.ps1      # Launcher Windows
│   └── docker-run.sh       # Launcher Linux/Mac
└── start.sh                # Script de démarrage interne
```
