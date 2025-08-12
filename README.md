# PAIME - AI-Powered Mobile Game Testing Platform by Playmetric

## Overview
PAIME is an automated mobile game testing platform that uses AI to test Android games, detect bugs, and provide comprehensive analytics. Developed by Playmetric, PAIME revolutionizes mobile game quality assurance.

## Quick Start

## Quick Start

### Prerequisites
- Docker Desktop installed
- At least 16GB RAM
- 50GB free disk space

### 🚀 Optimized Build System (Recommended)

PAIME includes a smart caching system that dramatically speeds up builds:

**First Time Setup:**
```cmd
# Clean any existing setup and build everything with caching
cleanup.bat
smart-build.bat
docker-compose up -d
```

**Development Workflow:**
```cmd
# For daily development - only rebuilds changed services
dev-build.bat [service_name]

# Examples:
dev-build.bat                    # Rebuild all dev services
dev-build.bat ai_agent          # Rebuild only AI agent
dev-build.bat backend dashboard # Rebuild backend and dashboard

# Restart services after rebuild
docker-compose restart [service_name]
```

**Cache System Benefits:**
- **534MB pip dependencies** cached and reused
- **Base Docker image** with all system dependencies cached
- **Build time**: ~20+ minutes → ~2-3 minutes for subsequent builds
- **Development builds**: Complete in seconds

### Build Scripts Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `fresh-start.bat` | Complete reset with clean database | Starting completely fresh |
| `smart-build.bat` | Intelligent build with caching | First build or major changes |
| `dev-build.bat` | Quick development builds | Daily development |
| `cleanup.bat` | Clean temporary files | Before commits, maintenance |
| `reset-db.bat` | Reset database only | Clear data, keep services |

### Legacy Installation (Not Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/paime.git
cd paime
```

2. **Optimized Build (Recommended):**
   - Windows: Run `build-and-run.bat`
   - Linux/Mac: Run `./build-and-run.sh`
   
   This will:
   - Build the optimized base Docker image with all system dependencies
   - Build and start all services using the shared base image
   - Significantly reduce future build times (from ~20+ minutes to ~2-3 minutes)

3. **Alternative - Standard Docker Compose:**
```bash
docker-compose up --build -d
```

### Development Workflow

**For quick rebuilds during development:**
- Windows: Run `quick-rebuild.bat`  
- Linux/Mac: Run `./quick-rebuild.sh`

This rebuilds only the application services without rebuilding the base image.

### Services & Ports

Once running, access the services at:
- **Dashboard**: http://localhost:3000 (Main UI)
- **API**: http://localhost:8000 (Backend API)
- **Emulator**: http://localhost:5555 (Android Emulator Service)

### Docker Architecture

PAIME uses an optimized Docker architecture:
- **Base Image (`paime-base`)**: Contains all system dependencies (gcc, python3-dev, android-tools, tesseract-ocr, etc.)
- **Shared Cache**: 534MB of Python packages cached in `./shared_cache/pip_cache`
- **Runtime Installation**: Services install Python packages from cache at startup instead of build time

This reduces build times significantly and allows for faster iterations during development.

### Usage

1. Upload APK files through the dashboard
2. Games are automatically processed and unique versions are tracked
3. Create manual testing sessions using the "Create New Session" button on each game
4. Monitor AI testing progress in real-time
5. View bugs, analytics, and session details through the dashboard

### Session Management

- **Manual Control**: Sessions are created on-demand via button clicks
- **Multiple Sessions**: Each game version can have multiple concurrent sessions
- **AI Knowledge Sharing**: AI learns from previous sessions to improve testing efficiency
- **Unique Game IDs**: Games are identified by hash of (game_name, package_name, version)

### Troubleshooting

**Build Issues:**
- Ensure Docker Desktop has enough resources allocated
- If base image build fails, try building manually: `docker build -f Dockerfile.base -t paime-base .`

**Runtime Issues:**
- Check service logs: `docker-compose logs -f [service_name]`
- Restart services: `docker-compose restart [service_name]`
- Clean rebuild: `docker-compose down && docker system prune -f && ./build-and-run.bat`
