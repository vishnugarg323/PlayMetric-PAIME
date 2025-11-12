# PlayMetric - AI-Powered Mobile Game Testing Platform

**Automated Android game testing using hybrid intelligence: Computer Vision + Vision AI + Reinforcement Learning**

PlayMetric is an intelligent mobile game testing system that uses a **three-phase hybrid AI approach** to automatically play and analyze casual/puzzle mobile games. The system works generically across multiple game types including traffic jam, bottle sort, screw pull, color sort, and other simple puzzle games.

## ⚡ Quick Start (Physical Device - Recommended)

```powershell
# ONE COMMAND SETUP - Does everything automatically!
.\scripts\setup-playmetric.ps1

# This script will:
# 1. Connect your Android phone via USB (enable USB Debugging first)
# 2. Build Docker images with optimized parallel builds (5-7 min)
# 3. Start all services
# 4. Verify connections
# 5. Open dashboard at http://localhost:3000
```

**That's it!** One command does everything. ✨

**Subsequent runs** (images already built):
```powershell
# Skip build, just start services (< 1 min)
.\scripts\setup-playmetric.ps1 -SkipBuild

# Or use docker-compose directly
docker-compose up -d
```

### 🚀 Optimized Build System

PlayMetric uses a **3-tier base image system** for faster builds:

- **playmetric-base**: Common dependencies (FastAPI, httpx, asyncpg, numpy, curl)
- **playmetric-base-adb**: Base + Android ADB tools  
- **playmetric-base-ml**: Base + CV/ML libraries (OpenCV, PyTorch, scikit-learn, Tesseract)

**Benefits:**
- ✅ **5-7 minute builds** (vs 15-20 min traditional)
- ✅ **Parallel builds** - All 5 services build simultaneously  
- ✅ **Shared layers** - Download dependencies once, reuse everywhere
- ✅ **Incremental rebuilds** - Only changed services rebuild (~30 sec)

**Build Commands:**
```powershell
# Automatic build (included in setup-playmetric.ps1)
.\scripts\setup-playmetric.ps1  # Builds + starts everything

# Manual optimized build (parallel - if needed)
.\build-optimized.ps1

# Traditional build (slower - sequential)
docker-compose build

# Rebuild only changed service (fast - reuses base image)
docker-compose build agent  # ~30-60 seconds

# Rebuild only base images
.\build-optimized.ps1 -BaseOnly
```

**Why Physical Device?**
- ✅ Real hardware testing (more accurate)
- ✅ Auto-detects screen dimensions (works with any phone)
- ✅ No emulator setup needed
- ✅ Works immediately

See [PHYSICAL_DEVICE_SETUP.md](PHYSICAL_DEVICE_SETUP.md) for detailed instructions.

## 🧠 Three-Phase Hybrid Intelligence System

PlayMetric combines three complementary AI approaches:

### **Phase 1: Computer Vision (CV)** ✅ IMPLEMENTED
- **Speed**: < 100ms per decision
- **Purpose**: Fast pattern recognition and UI analysis
- **Capabilities**:
  - Universal pattern recognition (menu/gameplay/completion/failure)
  - Context-aware action decisions
  - Multi-strategy stuck detection & recovery
  - OCR text detection (buttons, labels, instructions)
  - UI element detection via OpenCV
  - Works across ANY casual/puzzle game without game-specific code

### **Phase 2: Vision AI** ✅ IMPLEMENTED
Three vision models supported (auto-detects best available):

**LLaVA (Local, Free, Unlimited)** - Recommended
- **Speed**: CPU: 5-10s | GPU: 1-2s per decision
- **Cost**: FREE - runs locally, no API costs
- **Setup**: Automatic via Docker, ~7GB model download on first use
- **Privacy**: Fully local, no data sent to cloud

**Gemini Vision (Google Cloud)**
- **Speed**: 1-2 seconds per decision  
- **Cost**: Free tier: 60 requests/min
- **Setup**: Set `GEMINI_API_KEY` in `.env`

**GPT-4V (OpenAI)**
- **Speed**: 1-2 seconds per decision
- **Cost**: ~$0.01 per image
- **Setup**: Set `OPENAI_API_KEY` in `.env`

**Capabilities (all models)**:
- Deep scene understanding (menu, gameplay, dialog, game over)
- Game object identification (buttons, items, obstacles)
- Smart action recommendations with reasoning
- Progress detection and outcome evaluation
- Used for user demonstration learning and AI decision making

### **Phase 3: Reinforcement Learning** ✅ IMPLEMENTED
- **Speed**: Instant (Q-table lookup)
- **Purpose**: Learn from experience and optimize over time
- **Capabilities**:
  - Q-Learning with experience replay
  - Learns which actions work in which situations
  - Explores new strategies (epsilon-greedy)
  - Saves knowledge across sessions
  - Improves with each game played

## 🔄 How They Work Together

```
┌─────────────────────────────────────────────────────┐
│  INPUT: Screenshot + OCR + UI Elements              │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  Phase 1 (CV): Fast Analysis                        │
│  - Pattern matching, screen classification          │
│  - Action recommendation with confidence score      │
│  - Time: ~50-100ms                                  │
└───────────────────┬─────────────────────────────────┘
                    ↓
          ┌─────────┴─────────┐
          │   Confidence?     │
          └─────────┬─────────┘
              High  │  Low / Stuck
    ┌──────────────┴──────────────┐
    ↓                              ↓
┌────────────┐          ┌───────────────────────┐
│ Use CV     │          │ Phase 2 (Vision AI):  │
│ Decision   │          │ Deep Understanding    │
└─────┬──────┘          │ - Visual analysis     │
      │                 │ - Game object ID      │
      │                 │ - Strategic reasoning │
      │                 │ Time: ~2-3 seconds    │
      │                 └──────────┬────────────┘
      │                            ↓
      └────────────┬───────────────┘
                   ↓
         ┌─────────────────────┐
         │ Phase 3 (RL):       │
         │ Choose Best Action  │
         │ - Q-table lookup    │
         │ - Exploration       │
         │ - Learn & improve   │
         └──────────┬──────────┘
                    ↓
         ┌──────────────────────┐
         │  EXECUTE ACTION      │
         │  - Tap / Swipe       │
         └──────────┬───────────┘
                    ↓
         ┌──────────────────────┐
         │  UPDATE RL           │
         │  - Calculate reward  │
         │  - Update Q-values   │
         │  - Store experience  │
         └──────────────────────┘
```

## 🎯 What It Does

PlayMetric automatically:

1. **Installs games** on Android emulators
2. **Plays them intelligently** using hybrid AI (CV + Vision AI + RL)
3. **Captures screenshots** at 3 FPS and streams live to dashboard
4. **Detects bugs** (crashes, ANRs, UI issues)
5. **Shares knowledge** across sessions (RL model learns over time)
6. **Generates analytics** (difficulty, retention, performance)
7. **Learns from user gameplay** with vision AI analysis
8. **Auto-trains continuously** in background

## 📊 Vision AI & Learning Visualization

### 🌐 Web Dashboard (Recommended)

Open **http://localhost:8004** in your browser to see real-time visualization:

- **Live Learning Statistics** - Total demonstrations, action types, success rates
- **Visual Demonstrations** - Before/after screenshots with action details
- **Interactive Cards** - Click to see coordinates, rewards, OCR text
- **Auto-Refresh** - Updates every 30 seconds automatically

### 🔌 API Endpoints

**Core Endpoints:**
- `GET /` - Visual dashboard (HTML interface)
- `GET /vision/llava/status` - Check if LLaVA is loaded (loading/loaded/error)
- `GET /vision/learned-data?game_id=X&limit=50` - View user demonstrations with screenshots
- `GET /vision/learning-progress?game_id=X` - See learning statistics over time
- `GET /training/stats` - Training pipeline stats + LLaVA status

**What You Can See:**
- ✅ User demonstration screenshots (before/after actions)
- ✅ Actions taken by user (tap coordinates, swipes)
- ✅ Rewards and success rates per action
- ✅ Learning progress timeline (demonstrations per hour)
- ✅ Action distribution (most common user actions)
- ✅ LLaVA model status (loading/ready/device)
- ✅ OCR-detected text from gameplay
- ✅ Vision AI scene analysis

**Example Usage:**
```bash
# Open web dashboard
open http://localhost:8004

# OR use curl for API access
curl http://localhost:8004/vision/llava/status
curl http://localhost:8004/vision/learned-data?limit=50
curl http://localhost:8004/vision/learning-progress
```

## 🏗️ Architecture

│  - Multi-strategy stuck detection & recovery            │5. **Shares knowledge** across game versions (same game learns collectively)

```

Dashboard (React)          Port 3000 - Web UI│  - Works across ANY casual/puzzle game                  │6. **Generates analytics** (difficulty, retention, performance)

      ↓

Orchestrator (FastAPI)     Port 8000 - Main API└─────────────────────────────────────────────────────────┘

      ↓

      ├─→ Emulator Manager      Port 8005                        ↓ (if confidence < 0.5)---

      ├─→ Observation Service   Port 8001

      ├─→ AI Agent              Port 8004┌─────────────────────────────────────────────────────────┐

      └─→ Analytics Engine      Port 8003

            ↓│  TIER 2: Basic OCR + Computer Vision                    │## ⚡ Quick Start

      PostgreSQL + Redis

```│  - Text detection (buttons, labels)                     │



### Services│  - UI element detection                                 │```powershell



- **Emulator Manager**: APK installation, app launching│  - Simple heuristic decision making                     │# Windows: Use startup script

- **Observation**: Screenshot capture (3 FPS), OCR, UI detection

- **AI Agent**: 3-tier intelligent gameplay system└─────────────────────────────────────────────────────────┘.\start.bat

- **Analytics**: Difficulty analysis, level tracking, metrics

- **Orchestrator**: API gateway, session management                        ↓ (if no text/UI found)

- **Dashboard**: Real-time monitoring UI

┌─────────────────────────────────────────────────────────┐# Or manual start

## 🚀 Quick Start

│  TIER 3: Reinforcement Learning Agent                   │docker-compose up -d

### Prerequisites

│  - Random exploration when stuck                        │

- Windows with Docker Desktop

- Android Studio emulator│  - Learning from successful actions                     │# Wait for emulator boot (1-2 min)

- ADB configured

└─────────────────────────────────────────────────────────┘# Check status

### 1. Start Emulator

```docker logs playmetric-emulator --follow

```powershell

emulator -avd Pixel_5_API_30 -no-window

adb tcpip 5555

adb connect localhost:5555## 🏗️ Architecture# Access dashboard

```

Start-Process http://localhost:3000

### 2. Start PlayMetric

``````

```powershell

# Copy config┌──────────────┐

cp .env.example .env

│  Dashboard   │  React Frontend (Port 3000)**Dashboard**: http://localhost:3000  

# Start services

docker-compose up --build -d│  (React)     │  - Real-time game monitoring**API Docs**: http://localhost:8000/docs  



# Check status└──────┬───────┘  - Session management**Emulator Stream**: http://localhost:8006 ⭐ NEW!

docker-compose ps

```       │          - Live screenshot stream



### 3. Access Dashboard       ↓---



Open: http://localhost:3000┌──────────────┐



## 🎮 Usage│ Orchestrator │  FastAPI (Port 8000)## 🏗️ Architecture



1. Upload APK via Dashboard│   (FastAPI)  │  - Session lifecycle management

2. Create new session

3. Watch AI play automatically└──┬───────────┘  - APK installation coordination```

4. View analytics and metrics

   │              - Service orchestration┌─────────────────────────────────────────────────────────┐

## 🧠 Advanced Game Intelligence (Phase 1)

   ├─────────────────┬─────────────────┬──────────────────┐│  📱 Android Emulator (Headless)                         │

### Universal Patterns

   ↓                 ↓                 ↓                  ↓│     └─ Boots automatically                              │

Works across all casual/puzzle games:

┌─────────┐   ┌────────────┐   ┌──────────┐   ┌──────────────┐│     └─ Screenshots streamed at 3 FPS                    │

- **Menu**: "tap", "start", "play", "begin", "go", "level"

- **Gameplay**: "tap", "drag", "swipe", "sort", "match", "pull"│ Emulator│   │ Observation│   │   Agent  │   │  Analytics   ││     └─ Always-on (no session required)                  │

- **Completion**: "complete", "next", "win", "victory", "perfect"

- **Failure**: "retry", "try again", "restart", "game over"│ Manager │   │  Service   │   │  (AI)    │   │   Engine     │├─────────────────────────────────────────────────────────┤



### Interactive Zones│         │   │            │   │          │   │              ││  🤖 AI Agent (RL + Heuristic)                           │



- **Center**: Primary gameplay (0.2-0.8 x, 0.3-0.7 y)│ Port    │   │ Port 8001  │   │ Port 8004│   │ Port 8003    ││     └─ Observes screen state                            │

- **Bottom**: Action buttons (0.1-0.9 x, 0.75-0.95 y)

- **Top**: Info/back buttons (0.1-0.9 x, 0.05-0.25 y)│ 8005    │   │            │   │          │   │              ││     └─ Decides actions (tap, swipe, longpress, etc.)    │

- **Left/Right**: Side panels

└─────────┘   └────────────┘   └──────────┘   └──────────────┘│     └─ Learns from experience                           │

### Stuck Recovery

    │              │                 │                ││     └─ Shares knowledge across game versions            │

3-tier recovery when stuck:

1. Try back button (after 10 actions)    │              │                 │                │├─────────────────────────────────────────────────────────┤

2. Explore different zones (after 5 actions)

3. Try alternative UI elements (immediate)    └──────────────┴─────────────────┴────────────────┘│  💾 Knowledge Database (PostgreSQL)                     │



## 📊 Monitoring                           ││     └─ RL models per GAME (not per version)            │



### Health Checks                    ┌──────┴──────┐│     └─ Experience replay buffer                         │



```powershell                    │  PostgreSQL │  TimescaleDB (Port 5432)│     └─ Shared across versions of same game              │

curl http://localhost:8000/health  # Orchestrator

curl http://localhost:8001/health  # Observation                    │    Redis    │  Cache (Port 6379)├─────────────────────────────────────────────────────────┤

curl http://localhost:8003/health  # Analytics

curl http://localhost:8004/health  # Agent                    └─────────────┘│  📊 Dashboard (React)                                    │

curl http://localhost:8005/health  # Emulator Manager

``````│     └─ Live emulator view                               │



### Logs│     └─ Screenshot stream (3 FPS)                        │



```powershell### Core Services│     └─ Session monitoring                               │

docker-compose logs -f agent

docker-compose logs -f observation│     └─ UI/UX validation (optional)                      │

```

#### 1. **Emulator Manager** (Port 8005)└─────────────────────────────────────────────────────────┘

## 🔧 Configuration

- Connects to Android emulator running on host machine```

Key `.env` settings:

- APK installation and app launching

```bash

SCREEN_WIDTH=1080- Device control via ADB---

SCREEN_HEIGHT=1920

AGENT_MODE=heuristic

ACTION_INTERVAL=1.5

SCREENSHOT_FPS=3#### 2. **Observation Service** (Port 8001)## 🎮 Core Features

ENABLE_OCR=true

LOG_LEVEL=INFO- Captures screenshots (3 FPS)

```

- Performs OCR on screen text### 1. Device Setup ⭐ 

## 🔮 Phase 2: Vision AI (NOT IMPLEMENTED)

- Detects UI elements (buttons, clickable areas)**⚠️ IMPORTANT: Emulators don't work on Windows Docker**

**⚠️ IMPORTANT**: Phase 2 is a placeholder only - not functional!

- Provides real-time game state- x86_64 requires KVM (Linux kernel only)

The file `agent/src/vision_ai_agent.py` contains structure for future Vision-Language Model integration (Gemini, LLaVA) but is NOT implemented.

- ARM requires ARM host CPU

**Current system works great without Phase 2!** The 3-tier intelligence (Phase 1) is fully functional.

#### 3. **AI Agent** (Port 8004)

## 🐛 Troubleshooting

- **Advanced Game Intelligence**: Generic smart AI system**✅ Solution: Use Physical Android Device**

### Emulator Issues

  - Universal pattern recognition for menus, gameplay, completion screens1. Enable USB Debugging on your Android phone

```powershell

adb devices  - Context-aware decisions based on screen state2. Connect via USB to Windows PC

adb kill-server && adb start-server

adb connect localhost:5555  - Multi-strategy stuck detection (back button, zone exploration, UI alternatives)3. System automatically detects and uses your device

```

  - Works across multiple game types without game-specific code4. See [PHYSICAL_DEVICE_GUIDE.md](PHYSICAL_DEVICE_GUIDE.md) for full setup

### Service Issues

- **Basic OCR Intelligence**: Fallback when advanced AI has low confidence

```powershell

docker-compose restart agent- **RL Agent**: Last resort for exploration**Benefits:**

docker-compose build --no-cache agent

docker-compose logs -f agent- ✅ Real hardware testing (more accurate)

```

#### 4. **Analytics Engine** (Port 8003)- ✅ Works immediately (no emulator setup)

## 📁 Structure

- Difficulty analysis- ✅ Screenshots captured at **3 FPS** and streamed

```

PlayMetric/- Level progression tracking- ✅ Can test on multiple devices simultaneously

├── agent/                 # AI Agent (Phase 1 working)

│   ├── advanced_game_intelligence.py  ✅- Retention simulation

│   ├── game_intelligence.py           ✅

│   ├── vision_ai_agent.py             ❌ Placeholder only- Performance metrics### 2. Smart AI Agents

│   └── main_v2.py                     ✅

├── observation/           # Screenshots, OCR**Two modes:**

├── analytics/             # Metrics, analysis

├── orchestrator/          # API gateway#### 5. **Orchestrator** (Port 8000)- **Heuristic Agent** (recommended): Rule-based intelligent exploration

├── emulator_manager/      # Device control

├── dashboard/             # React UI- Central API gateway- **RL Agent** (advanced): Deep Q-Network that learns from gameplay

├── database/              # PostgreSQL migrations

├── shared/                # Common utilities- Session management

└── docker-compose.yml

```- Service coordination**Actions available:**



## 📄 License- WebSocket for real-time updates- Tap, Swipe (up/down/left/right), Long press, Multi-tap, Back, Home



See LICENSE file.



---#### 6. **Dashboard** (Port 3000)### 3. Knowledge Persistence & Sharing



**Built with ❤️ for intelligent game testing**- React-based web UI- RL model stored per **game** (identified by `package_name`)



**Current Status**: Phase 1 fully functional | Phase 2 not implemented (placeholder only)- Live game monitoring- Experience replay buffer shared across all versions of same game


- Session controls- New sessions automatically load existing knowledge

- Analytics visualization- Continuous learning across sessions



## 🚀 Quick StartExample:

```

### PrerequisitesGame: "com.example.puzzle" v1.0 → Trains for 1 hour → Saves model

Game: "com.example.puzzle" v1.1 → Loads existing model → Continues learning

- **Windows** with Docker DesktopGame: "com.example.puzzle" v2.0 → Loads same model → Keeps improving

- **Android Studio** with emulator installed```

- **ADB** configured and accessible

- **Docker & Docker Compose**### 4. UI/UX Validation (Optional)

- Upload design specs (images/PDFs) when creating session

### 1. Start Android Emulator- AI compares screenshots against specs during gameplay

- Detects mismatches (wrong colors, missing elements, layout issues)

```powershell- Reports as bugs with visual diff

# Start emulator (headless)

emulator -avd Pixel_5_API_30 -no-window### 5. Real-Time Dashboard

- **Emulator view**: Always visible, even without session

# Enable ADB over TCP- **Screenshot stream**: Live gameplay at 3 FPS

adb tcpip 5555- **Session stats**: Actions, bugs, crashes, progress

- **AI thinking**: See what agent is deciding and why

# Verify connection- **Bug reports**: Real-time crash/ANR detection

adb connect localhost:5555

adb devices---

```

## 📋 System Requirements

### 2. Configure Environment

**Minimum:**

```powershell- 8GB RAM

# Copy example config- 4 CPU cores

cp .env.example .env- 30GB disk space

- Docker Desktop

# Edit .env if needed (defaults work for most setups)

```**Recommended:**

- 16GB+ RAM

### 3. Start PlayMetric- 6+ CPU cores

- 50GB SSD

```powershell- Windows 10/11 with WSL2 or Linux

# Build and start all services

docker-compose up --build -d---



# View logs## 🚀 Installation

docker-compose logs -f

### Step 1: Clone and Configure

# Check service health

docker-compose ps```powershell

```cd C:\Users\vishn\PlayMetric



### 4. Access Dashboard# Create .env file with your settings

```

Open browser: http://localhost:3000

**Key `.env` settings:**

## 🎮 Using PlayMetric```env

# Screenshot rate (frames per second)

### Upload and Play a GameSCREENSHOT_FPS=3



1. **Upload APK**:# Agent settings

   - Go to DashboardAGENT_MODE=heuristic

   - Click "Upload Game"ACTION_INTERVAL=1.5

   - Select your game APK file

# Emulator

2. **Create Session**:EMULATOR_DEVICE=pixel_5

   - Click "Start New Session"EMULATOR_MEMORY=2048

   - Enter session nameBOOT_TIMEOUT=120

   - Select game package

# Database

3. **Watch AI Play**:DB_USER=playmetric

   - Live screenshot updates every 333msDB_PASSWORD=playmetric123

   - See AI decisions in real-time```

   - Monitor progress and metrics

### Step 2: Build and Start

### API Usage

```powershell

```bash# Build images (first time only, ~10-15 min)

# Start sessiondocker-compose build

curl -X POST http://localhost:8000/session/start \

  -H "Content-Type: application/json" \# Start all services

  -d '{"package_name": "com.game.example", "session_name": "test-run"}'docker-compose up -d



# Stop session# Check status

curl -X POST http://localhost:8000/session/stop/SESSION_IDdocker-compose ps

```

# Wait for all services to be healthy

## 🧠 Advanced Game Intelligence```



The **Advanced Game Intelligence** system is the heart of PlayMetric's smart gameplay. It works generically across multiple casual/puzzle games without game-specific code.### Step 3: Access Dashboard



### Universal Pattern RecognitionOpen http://localhost:3000



```pythonYou should see:

# Example patterns detected across ALL games- Emulator view (even before creating session)

Menu Keywords: "tap", "start", "play", "begin", "go", "level", "continue"- Games list

Gameplay Keywords: "tap", "drag", "swipe", "sort", "match", "pull", "push", "rotate"- Sessions tab

Completion Keywords: "complete", "next", "win", "victory", "perfect", "excellent"- Analytics

Failure Keywords: "retry", "try again", "restart", "game over"

```---



### Interactive Zones## 🎯 Usage



The system divides the screen into 5 universal zones:### Upload Game

- **Center**: Primary gameplay area (0.2-0.8 x, 0.3-0.7 y)

- **Bottom**: Common action buttons (0.1-0.9 x, 0.75-0.95 y)1. Go to **Games** tab

- **Top**: Info/back buttons (0.1-0.9 x, 0.05-0.25 y)2. Click **"Add Game"**

- **Left Panel**: Side menu (0.0-0.2 x, 0.2-0.8 y)3. Upload APK file

- **Right Panel**: Side menu (0.8-1.0 x, 0.2-0.8 y)4. System parses metadata (version, package name, etc.)



### Stuck Detection & Recovery### Create Test Session



When the AI gets stuck (same state for 3+ actions), it uses a 3-tier recovery strategy:1. Go to **Sessions** tab

2. Click **"New Session"**

1. **Try Back Button** (after 10 stuck actions)3. Select game

2. **Explore Different Zones** (after 5 actions)4. Choose agent mode:

3. **Try Alternative UI Elements** (immediate)   - **Heuristic** (recommended for most games)

   - **RL** (experimental, learns over time)

### Screen Classification5. **Optional**: Enable "UI/UX Validation" and upload design specs

6. Click **"Start Session"**

The AI classifies every screen as:

- **Menu**: Start screens, level selection### Monitor Live

- **Gameplay**: Active game interaction

- **Completion**: Level finished, victory- **Emulator view**: See what's happening on device

- **Game Over**: Failure, retry screens- **Screenshot stream**: Auto-updates every ~333ms (3 FPS)

- **AI decisions**: Watch agent's thinking process

## 📊 Monitoring & Analytics- **Bugs**: Real-time crash/ANR alerts



### Service Health### Review Results



```powershellAfter session ends:

# Check all services- Download report (JSON/PDF)

docker-compose ps- View analytics (difficulty, retention, performance)

- Check bug list with screenshots

# View specific service logs- Compare with previous versions

docker-compose logs -f agent

docker-compose logs -f observation---



# Health check endpoints## 🤖 AI Agent Details

curl http://localhost:8000/health  # Orchestrator

curl http://localhost:8001/health  # Observation### Knowledge Persistence

curl http://localhost:8003/health  # Analytics

curl http://localhost:8004/health  # Agent**Database schema:**

curl http://localhost:8005/health  # Emulator Manager```sql

```-- RL models stored per GAME (not version)

CREATE TABLE rl_models (

### Database Access    id UUID PRIMARY KEY,

    game_id UUID REFERENCES games(id),  -- Links to GAME, not version

```powershell    package_name VARCHAR(255),           -- Identifies game uniquely

# Connect to PostgreSQL    model_data BYTEA,                    -- Neural network weights

docker exec -it playmetric-postgres psql -U playmetric -d playmetric    training_steps INT,

    average_reward FLOAT,

# Useful queries    created_at TIMESTAMP

SELECT * FROM sessions ORDER BY created_at DESC LIMIT 10;);

SELECT * FROM game_events WHERE session_id = 'SESSION_ID';

SELECT * FROM analytics_summary;-- Experience replay buffer

```CREATE TABLE rl_experiences (

    id UUID PRIMARY KEY,

### Redis Cache    game_id UUID,                        -- Same game shares experiences

    state BYTEA,                         -- Screenshot/features

```powershell    action INT,

# Connect to Redis    reward FLOAT,

docker exec -it playmetric-redis redis-cli    next_state BYTEA,

    done BOOLEAN,

# Useful commands    priority FLOAT,

KEYS *    timestamp TIMESTAMP

GET session:SESSION_ID);

``````



## 🔧 Configuration### How Knowledge Sharing Works



### Environment Variables```python

# When session starts

Key settings in `.env`:def start_session(game_id, version_id):

    # Find game's package name

```bash    game = db.get_game(game_id)

# Screen dimensions (must match emulator)    package_name = game.package_name

SCREEN_WIDTH=1080    

SCREEN_HEIGHT=1920    # Load existing model for this GAME (any version)

    existing_model = db.get_latest_model(package_name=package_name)

# AI behavior    

AGENT_MODE=heuristic        # random | heuristic | rl | hybrid    if existing_model:

ACTION_INTERVAL=1.5         # Seconds between actions        # Load weights and continue learning

        agent.load_model(existing_model.model_data)

# Screenshot capture        print(f"Loaded existing model with {existing_model.training_steps} steps")

SCREENSHOT_FPS=3            # Screenshots per second    else:

ENABLE_OCR=true             # Enable text detection        # First time playing this game

        agent.initialize_new_model()

# Logging        print("Starting fresh learning")

LOG_LEVEL=INFO              # DEBUG | INFO | WARNING | ERROR    

```    # Play game...

    

## 🔮 Phase 2: Vision AI (Coming Soon)    # Save model (updates existing or creates new)

    db.save_model(package_name=package_name, model_data=agent.get_weights())

Phase 2 will add **Vision-Language Model** integration for even smarter gameplay:```



### Planned Features### Training Process

- **Google Gemini Flash** integration (1500 free API calls/day)

- **LLaVA** local model support (unlimited, no API costs)1. Agent observes screen (84x84x3 RGB)

- **Hybrid approach**: Fast CV for quick decisions, Vision AI for complex situations2. Passes through CNN to extract features

- **Result caching**: Save API calls by caching similar screens3. Outputs Q-values for each action

4. Selects action (epsilon-greedy)

### Example Usage (Future)5. Executes action via ADB

6. Observes result (reward + next state)

```python7. Stores experience in replay buffer

# Configure Vision AI8. Periodically trains on random batch

GEMINI_API_KEY=your_api_key_here9. Updates model weights

VISION_AI_ENABLED=true10. Saves to database every N steps

VISION_AI_MODEL=gemini-1.5-flash

---

# System will automatically use Vision AI when:

# - CV confidence < 50%## 🖼️ Screenshot Streaming

# - Stuck for 3+ actions

# - New screen type detected### Configuration

```

```yaml

## 🐛 Troubleshooting# docker-compose.yml

observation:

### Emulator Not Connecting  environment:

    - SCREENSHOT_FPS=3              # Frames per second

```powershell    - SCREENSHOT_QUALITY=85         # JPEG quality (0-100)

# Check ADB connection    - SCREENSHOT_RESIZE=true        # Resize to 720p for bandwidth

adb devices```



# Restart ADB server### How It Works

adb kill-server

adb start-server```

Emulator → ADB screencap (raw PNG)

# Reconnect to emulator    ↓

adb connect localhost:5555Observation Service → Process/compress

```    ↓

WebSocket → Broadcast to dashboard

### Service Shows Unhealthy    ↓

Dashboard → Display in real-time

```powershell```

# Restart specific service

docker-compose restart agent**Bandwidth usage:** ~50-100 KB/frame @ 3 FPS = ~150-300 KB/s



# Rebuild service### Access Screenshots

docker-compose build --no-cache agent

docker-compose up -d agent- **Live view**: Dashboard emulator panel

```- **Stored**: `/data/screenshots/{session_id}/`

- **API**: `GET /api/sessions/{id}/screenshots`

### Screenshots Not Capturing

---

```powershell

# Check observation service logs## 🎨 UI/UX Validation

docker-compose logs observation

### Setup

# Verify ADB from container

docker exec playmetric-observation adb devices1. Create session with "UI/UX Validation" enabled

2. Upload reference images or PDF:

# Test screenshot manually   - Login screen mockup

docker exec playmetric-observation adb shell screencap -p /sdcard/test.png   - Main menu design

```   - Settings layout

   - etc.

### Agent Not Taking Actions

### What Gets Validated

```powershell

# Check agent logs- **Color matching**: RGB values within threshold

docker-compose logs -f agent- **Layout**: Element positions and sizes

- **Text**: OCR comparison

# Verify agent can reach observation service- **Assets**: Image similarity

docker exec playmetric-agent curl http://observation:8001/health- **Spacing**: Margins and padding



# Check if session is active### Results

curl http://localhost:8000/session/status

```Mismatch reports show:

- Screenshot vs Reference side-by-side

## 📁 Project Structure- Highlighted differences

- Severity score

```- Recommendations

PlayMetric/

├── agent/                 # AI Agent serviceExample bug:

│   ├── src/```

│   │   ├── main_v2.py                    # Main agent logicType: UI_MISMATCH

│   │   ├── advanced_game_intelligence.py # Smart AI systemTitle: "Button color doesn't match design"

│   │   ├── game_intelligence.py          # Basic OCR intelligenceScreenshot: session_123/screenshot_045.png

│   │   ├── vision_ai_agent.py            # Phase 2 placeholderReference: design_specs/button_spec.png

│   │   └── rl_agent.py                   # RL fallbackDifference: Color off by 15% (expected #FF5733, got #E84829)

│   └── DockerfileSeverity: Medium

├── observation/           # Screenshot & OCR service```

│   ├── src/

│   │   └── main.py---

│   └── Dockerfile

├── analytics/             # Analytics engine## 📊 Database Schema

│   ├── src/

│   │   └── main.py**Core tables:**

│   └── Dockerfile```sql

├── orchestrator/          # Main API gatewaygames                   -- Game metadata

│   ├── src/game_versions          -- APK versions

│   │   └── main_v2.pysessions               -- Test sessions

│   └── Dockerfilebugs                   -- Detected issues

├── emulator_manager/      # Emulator controlscreenshots            -- Captured images

│   ├── src/rl_models              -- AI models (per game)

│   │   └── main.pyrl_experiences         -- Training data

│   └── Dockerfilesession_metrics        -- Performance data

├── dashboard/             # React frontendui_validations         -- UI/UX check results

│   ├── src/```

│   └── Dockerfile

├── database/              # PostgreSQL migrations**Key relationships:**

│   └── migrations/- `rl_models.game_id` → `games.id` (not version-specific)

├── shared/                # Shared utilities- `rl_experiences.game_id` → `games.id` (shared)

│   └── database.py        # DB connection helper- `sessions.game_version_id` → `game_versions.id` (session-specific)

├── docker-compose.yml     # Service orchestration

├── .env                   # Configuration---

└── README.md             # This file

```## 🐛 Troubleshooting



## 🤝 Contributing### Dashboard Won't Load



PlayMetric is designed to be extensible:```powershell

# Check status

### Adding New Game Supportdocker-compose ps dashboard



The generic intelligence system should work automatically, but you can enhance it:# View logs

docker logs playmetric-dashboard --tail 50

1. Add game-specific patterns to `GameKnowledgeBase` (optional)

2. Tune confidence thresholds in `.env`# Restart

3. Test and iteratedocker-compose restart dashboard



### Adding Vision AI Models# Access at http://localhost:3000

```

To add a new Vision-Language Model:

### Emulator Not Booting

1. Edit `agent/src/vision_ai_agent.py`

2. Add new model method (e.g., `_call_claude_api`)```powershell

3. Update model type enum# Check boot status

4. Configure API keys in `.env`docker exec playmetric-emulator getprop sys.boot_completed



## 📄 License# Should output: 1 (means booted)



See LICENSE file for details.# Check logs if not booting

docker logs playmetric-emulator --tail 100

## 🙋 Support

# Verify Redroid container is running

For issues, questions, or contributions:docker ps | findstr emulator

- Create an issue on GitHub

- Check troubleshooting section above# Restart emulator

- Review service logs with `docker-compose logs`docker-compose restart emulator



---# Check live stream status

curl http://localhost:8006/status

**Built with ❤️ for intelligent game testing**```


### Agent Not Learning

```powershell
# Verify database connection
docker logs playmetric-agent | grep "Database"

# Check experiences stored
docker exec playmetric-postgres psql -U playmetric -d playmetric -c \
  "SELECT COUNT(*) FROM rl_experiences;"

# View model info
docker exec playmetric-postgres psql -U playmetric -d playmetric -c \
  "SELECT * FROM rl_models ORDER BY created_at DESC LIMIT 5;"
```

### Screenshots Not Streaming

```powershell
# Check observation service
docker logs playmetric-observation --tail 50

# Test ADB connection
docker exec playmetric-observation adb devices

# Verify WebSocket
# Dashboard console should show: "WebSocket connected"
```

---

## 🔧 Configuration Reference

### Agent Settings

```env
# Agent type
AGENT_MODE=heuristic          # heuristic | rl

# Action timing
ACTION_INTERVAL=1.5           # Seconds between actions
ACTION_RANDOMNESS=0.1         # Random exploration (0-1)

# RL specific
RL_LEARNING_RATE=0.001
RL_BATCH_SIZE=64
RL_GAMMA=0.99                 # Discount factor
RL_EPSILON_START=1.0
RL_EPSILON_MIN=0.01
RL_EPSILON_DECAY=0.995
RL_MEMORY_SIZE=50000
```

### Screenshot Settings

```env
SCREENSHOT_FPS=3              # Frames per second (1-10)
SCREENSHOT_QUALITY=85         # JPEG quality (50-100)
SCREENSHOT_RESIZE=true        # Resize to 720p
SCREENSHOT_STORAGE_DAYS=30    # Keep for N days
```

### Emulator Settings

```env
EMULATOR_DEVICE=pixel_5       # Device profile
EMULATOR_MEMORY=2048          # RAM in MB
EMULATOR_CORES=4              # CPU cores
BOOT_TIMEOUT=120              # Max boot wait (seconds)
HEADLESS=true                 # No GUI
```

---

## 📈 Performance Optimization

### For Faster Training

```env
# Increase screenshot processing
SCREENSHOT_FPS=5

# Faster actions
ACTION_INTERVAL=1.0

# Larger batches
RL_BATCH_SIZE=128

# More memory
EMULATOR_MEMORY=4096
```

### For Lower Resource Usage

```env
# Reduce screenshot rate
SCREENSHOT_FPS=1

# Slower actions
ACTION_INTERVAL=2.0

# Smaller batches
RL_BATCH_SIZE=32

# Less memory
EMULATOR_MEMORY=1024
```

---

## 🚀 Advanced Features

### Custom Reward Functions

Edit `agent/src/rl_agent.py`:

```python
def calculate_reward(self, prev_state, action, new_state):
    reward = 0.0
    
    # Reward for progress (e.g., score increase)
    if self.detect_score_increase(prev_state, new_state):
        reward += 10.0
    
    # Penalty for crash
    if self.detect_crash(new_state):
        reward -= 100.0
    
    # Reward for reaching new screen
    if self.detect_new_screen(prev_state, new_state):
        reward += 5.0
    
    return reward
```

### Multi-Game Training

```python
# Train on similar games to share knowledge
games = [
    "com.example.puzzle1",
    "com.example.puzzle2",
    "com.example.puzzle3"
]

for game in games:
    train_session(game, load_model_from="puzzle_genre")
    # Model improves across all puzzle games
```

---

## 📝 API Reference

### Upload Game

```http
POST /api/games
Content-Type: multipart/form-data

{
  "apk": <file>
}
```

### Create Session

```http
POST /api/sessions
Content-Type: application/json

{
  "game_id": "uuid",
  "version_id": "uuid",
  "agent_mode": "heuristic",
  "duration_minutes": 30,
  "enable_ui_validation": false,
  "ui_specs": null
}
```

### Get Live Screenshots

```http
GET /api/sessions/{session_id}/screenshots/live
```

WebSocket endpoint:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/screenshots');
ws.onmessage = (event) => {
    const screenshot = JSON.parse(event.data);
    displayImage(screenshot.data);
};
```

### Get Session Results

```http
GET /api/sessions/{session_id}/results
```

---

## 🔐 Security Notes

- Database credentials in `.env` (don't commit!)
- API has no auth by default (add JWT if needed)
- Screenshots stored locally (not encrypted)
- Emulator runs privileged (Docker requirement)

---

## 📦 Project Structure

```
PlayMetric/
├── .env                        # Configuration (GITIGNORED)
├── docker-compose.yml          # Service definitions
├── README.md                   # This file
│
├── dashboard/                  # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Games.tsx
│   │   │   ├── Sessions.tsx
│   │   │   └── CreateSession.tsx
│   │   └── components/
│   └── Dockerfile
│
├── orchestrator/               # Main backend
│   ├── src/
│   │   ├── main_v2.py
│   │   └── multi_session.py
│   └── requirements.txt
│
├── agent/                      # AI agent
│   ├── src/
│   │   ├── rl_agent.py
│   │   └── heuristic_agent.py
│   └── requirements.txt
│
├── observation/                # Screenshot capture
│   ├── src/
│   │   └── capture.py
│   └── requirements.txt
│
├── emulator/                   # Android emulator
│   └── Dockerfile
│
└── database/                   # Schema
    └── init.sql
```

---

## 🎓 How It All Works

### Session Lifecycle

```
1. User uploads APK
   ↓
2. System parses metadata (version, package, etc.)
   ↓
3. User creates session
   ↓
4. Orchestrator installs APK on emulator
   ↓
5. Agent loads knowledge for this GAME (if exists)
   ↓
6. Agent launches app
   ↓
7. Screenshot capture starts (3 FPS)
   ↓
8. Agent observes → decides → acts → learns
   ↓
9. Crash detector monitors logcat
   ↓
10. UI validator compares screenshots (if enabled)
    ↓
11. All data saved to database
    ↓
12. Session ends → Model saved → Report generated
```

### Knowledge Sharing Example

```
Day 1: Test "Puzzle Game v1.0" for 2 hours
       → Agent learns basic mechanics
       → Model saved to DB

Day 2: Test "Puzzle Game v1.1" for 1 hour
       → Agent loads v1.0 knowledge
       → Continues learning
       → Model updated

Day 3: Test "Puzzle Game v2.0" for 30 min
       → Agent loads improved model
       → Already knows game mechanics
       → Focuses on new features
```

---

## 🛠️ Development

### Run Locally

```powershell
# Start dependencies
docker-compose up -d postgres redis emulator

# Run orchestrator locally
cd orchestrator
pip install -r requirements.txt
python src/main_v2.py

# Run dashboard locally
cd dashboard
npm install
npm run dev
```

### Add New Agent

```python
# agent/src/agents/my_agent.py
from .base import BaseAgent

class MyAgent(BaseAgent):
    def select_action(self, state):
        # Your logic
        return action
```

Register in `agent/src/main.py`:
```python
from agents.my_agent import MyAgent

agents = {
    'heuristic': HeuristicAgent,
    'rl': RLAgent,
    'my_agent': MyAgent  # Add here
}
```

---

## 📞 Support

**Common commands:**
```powershell
# View all logs
docker-compose logs -f

# Restart everything
docker-compose restart

# Stop and remove
docker-compose down

# Reset database
docker-compose down -v
docker-compose up -d
```

**Check services:**
- Dashboard: http://localhost:3000
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Emulator: http://localhost:6080

---

## 📄 License

MIT License - See LICENSE file

---

## 🎉 Summary

✅ **Headless emulator** with 3 FPS screenshot streaming  
✅ **Smart AI agents** that learn and improve  
✅ **Knowledge sharing** across game versions  
✅ **UI/UX validation** (optional)  
✅ **Real-time dashboard** with live monitoring  
✅ **Complete automation** from APK → Results  
✅ **Production-ready** Docker setup  

**Ready to use! Start with:**
```powershell
docker-compose up -d
```

---

*Built for game developers and QA engineers* 🎮
