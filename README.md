# PlayMetric - AI-Powered Game Testing System

**Automated Android game testing using reinforcement learning agents with real-time monitoring**

---

## 🎯 What It Does

PlayMetric automatically:
1. **Installs games** on Android emulators
2. **Plays them intelligently** using AI agents that learn
3. **Captures screenshots** at 3 FPS and streams live to dashboard
4. **Detects bugs** (crashes, ANRs, UI issues)
5. **Shares knowledge** across game versions (same game learns collectively)
6. **Generates analytics** (difficulty, retention, performance)

---

## ⚡ Quick Start

```powershell
# Windows: Use startup script
.\start.bat

# Or manual start
docker-compose up -d

# Wait for emulator boot (1-2 min)
# Check status
docker logs playmetric-emulator --follow

# Access dashboard
Start-Process http://localhost:3000
```

**Dashboard**: http://localhost:3000  
**API Docs**: http://localhost:8000/docs  
**Emulator Stream**: http://localhost:8006 ⭐ NEW!

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  📱 Android Emulator (Headless)                         │
│     └─ Boots automatically                              │
│     └─ Screenshots streamed at 3 FPS                    │
│     └─ Always-on (no session required)                  │
├─────────────────────────────────────────────────────────┤
│  🤖 AI Agent (RL + Heuristic)                           │
│     └─ Observes screen state                            │
│     └─ Decides actions (tap, swipe, longpress, etc.)    │
│     └─ Learns from experience                           │
│     └─ Shares knowledge across game versions            │
├─────────────────────────────────────────────────────────┤
│  💾 Knowledge Database (PostgreSQL)                     │
│     └─ RL models per GAME (not per version)            │
│     └─ Experience replay buffer                         │
│     └─ Shared across versions of same game              │
├─────────────────────────────────────────────────────────┤
│  📊 Dashboard (React)                                    │
│     └─ Live emulator view                               │
│     └─ Screenshot stream (3 FPS)                        │
│     └─ Session monitoring                               │
│     └─ UI/UX validation (optional)                      │
└─────────────────────────────────────────────────────────┘
```

---

## 🎮 Core Features

### 1. Device Setup ⭐ 
**⚠️ IMPORTANT: Emulators don't work on Windows Docker**
- x86_64 requires KVM (Linux kernel only)
- ARM requires ARM host CPU

**✅ Solution: Use Physical Android Device**
1. Enable USB Debugging on your Android phone
2. Connect via USB to Windows PC
3. System automatically detects and uses your device
4. See [PHYSICAL_DEVICE_GUIDE.md](PHYSICAL_DEVICE_GUIDE.md) for full setup

**Benefits:**
- ✅ Real hardware testing (more accurate)
- ✅ Works immediately (no emulator setup)
- ✅ Screenshots captured at **3 FPS** and streamed
- ✅ Can test on multiple devices simultaneously

### 2. Smart AI Agents
**Two modes:**
- **Heuristic Agent** (recommended): Rule-based intelligent exploration
- **RL Agent** (advanced): Deep Q-Network that learns from gameplay

**Actions available:**
- Tap, Swipe (up/down/left/right), Long press, Multi-tap, Back, Home

### 3. Knowledge Persistence & Sharing
- RL model stored per **game** (identified by `package_name`)
- Experience replay buffer shared across all versions of same game
- New sessions automatically load existing knowledge
- Continuous learning across sessions

Example:
```
Game: "com.example.puzzle" v1.0 → Trains for 1 hour → Saves model
Game: "com.example.puzzle" v1.1 → Loads existing model → Continues learning
Game: "com.example.puzzle" v2.0 → Loads same model → Keeps improving
```

### 4. UI/UX Validation (Optional)
- Upload design specs (images/PDFs) when creating session
- AI compares screenshots against specs during gameplay
- Detects mismatches (wrong colors, missing elements, layout issues)
- Reports as bugs with visual diff

### 5. Real-Time Dashboard
- **Emulator view**: Always visible, even without session
- **Screenshot stream**: Live gameplay at 3 FPS
- **Session stats**: Actions, bugs, crashes, progress
- **AI thinking**: See what agent is deciding and why
- **Bug reports**: Real-time crash/ANR detection

---

## 📋 System Requirements

**Minimum:**
- 8GB RAM
- 4 CPU cores
- 30GB disk space
- Docker Desktop

**Recommended:**
- 16GB+ RAM
- 6+ CPU cores
- 50GB SSD
- Windows 10/11 with WSL2 or Linux

---

## 🚀 Installation

### Step 1: Clone and Configure

```powershell
cd C:\Users\vishn\PlayMetric

# Create .env file with your settings
```

**Key `.env` settings:**
```env
# Screenshot rate (frames per second)
SCREENSHOT_FPS=3

# Agent settings
AGENT_MODE=heuristic
ACTION_INTERVAL=1.5

# Emulator
EMULATOR_DEVICE=pixel_5
EMULATOR_MEMORY=2048
BOOT_TIMEOUT=120

# Database
DB_USER=playmetric
DB_PASSWORD=playmetric123
```

### Step 2: Build and Start

```powershell
# Build images (first time only, ~10-15 min)
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Wait for all services to be healthy
```

### Step 3: Access Dashboard

Open http://localhost:3000

You should see:
- Emulator view (even before creating session)
- Games list
- Sessions tab
- Analytics

---

## 🎯 Usage

### Upload Game

1. Go to **Games** tab
2. Click **"Add Game"**
3. Upload APK file
4. System parses metadata (version, package name, etc.)

### Create Test Session

1. Go to **Sessions** tab
2. Click **"New Session"**
3. Select game
4. Choose agent mode:
   - **Heuristic** (recommended for most games)
   - **RL** (experimental, learns over time)
5. **Optional**: Enable "UI/UX Validation" and upload design specs
6. Click **"Start Session"**

### Monitor Live

- **Emulator view**: See what's happening on device
- **Screenshot stream**: Auto-updates every ~333ms (3 FPS)
- **AI decisions**: Watch agent's thinking process
- **Bugs**: Real-time crash/ANR alerts

### Review Results

After session ends:
- Download report (JSON/PDF)
- View analytics (difficulty, retention, performance)
- Check bug list with screenshots
- Compare with previous versions

---

## 🤖 AI Agent Details

### Knowledge Persistence

**Database schema:**
```sql
-- RL models stored per GAME (not version)
CREATE TABLE rl_models (
    id UUID PRIMARY KEY,
    game_id UUID REFERENCES games(id),  -- Links to GAME, not version
    package_name VARCHAR(255),           -- Identifies game uniquely
    model_data BYTEA,                    -- Neural network weights
    training_steps INT,
    average_reward FLOAT,
    created_at TIMESTAMP
);

-- Experience replay buffer
CREATE TABLE rl_experiences (
    id UUID PRIMARY KEY,
    game_id UUID,                        -- Same game shares experiences
    state BYTEA,                         -- Screenshot/features
    action INT,
    reward FLOAT,
    next_state BYTEA,
    done BOOLEAN,
    priority FLOAT,
    timestamp TIMESTAMP
);
```

### How Knowledge Sharing Works

```python
# When session starts
def start_session(game_id, version_id):
    # Find game's package name
    game = db.get_game(game_id)
    package_name = game.package_name
    
    # Load existing model for this GAME (any version)
    existing_model = db.get_latest_model(package_name=package_name)
    
    if existing_model:
        # Load weights and continue learning
        agent.load_model(existing_model.model_data)
        print(f"Loaded existing model with {existing_model.training_steps} steps")
    else:
        # First time playing this game
        agent.initialize_new_model()
        print("Starting fresh learning")
    
    # Play game...
    
    # Save model (updates existing or creates new)
    db.save_model(package_name=package_name, model_data=agent.get_weights())
```

### Training Process

1. Agent observes screen (84x84x3 RGB)
2. Passes through CNN to extract features
3. Outputs Q-values for each action
4. Selects action (epsilon-greedy)
5. Executes action via ADB
6. Observes result (reward + next state)
7. Stores experience in replay buffer
8. Periodically trains on random batch
9. Updates model weights
10. Saves to database every N steps

---

## 🖼️ Screenshot Streaming

### Configuration

```yaml
# docker-compose.yml
observation:
  environment:
    - SCREENSHOT_FPS=3              # Frames per second
    - SCREENSHOT_QUALITY=85         # JPEG quality (0-100)
    - SCREENSHOT_RESIZE=true        # Resize to 720p for bandwidth
```

### How It Works

```
Emulator → ADB screencap (raw PNG)
    ↓
Observation Service → Process/compress
    ↓
WebSocket → Broadcast to dashboard
    ↓
Dashboard → Display in real-time
```

**Bandwidth usage:** ~50-100 KB/frame @ 3 FPS = ~150-300 KB/s

### Access Screenshots

- **Live view**: Dashboard emulator panel
- **Stored**: `/data/screenshots/{session_id}/`
- **API**: `GET /api/sessions/{id}/screenshots`

---

## 🎨 UI/UX Validation

### Setup

1. Create session with "UI/UX Validation" enabled
2. Upload reference images or PDF:
   - Login screen mockup
   - Main menu design
   - Settings layout
   - etc.

### What Gets Validated

- **Color matching**: RGB values within threshold
- **Layout**: Element positions and sizes
- **Text**: OCR comparison
- **Assets**: Image similarity
- **Spacing**: Margins and padding

### Results

Mismatch reports show:
- Screenshot vs Reference side-by-side
- Highlighted differences
- Severity score
- Recommendations

Example bug:
```
Type: UI_MISMATCH
Title: "Button color doesn't match design"
Screenshot: session_123/screenshot_045.png
Reference: design_specs/button_spec.png
Difference: Color off by 15% (expected #FF5733, got #E84829)
Severity: Medium
```

---

## 📊 Database Schema

**Core tables:**
```sql
games                   -- Game metadata
game_versions          -- APK versions
sessions               -- Test sessions
bugs                   -- Detected issues
screenshots            -- Captured images
rl_models              -- AI models (per game)
rl_experiences         -- Training data
session_metrics        -- Performance data
ui_validations         -- UI/UX check results
```

**Key relationships:**
- `rl_models.game_id` → `games.id` (not version-specific)
- `rl_experiences.game_id` → `games.id` (shared)
- `sessions.game_version_id` → `game_versions.id` (session-specific)

---

## 🐛 Troubleshooting

### Dashboard Won't Load

```powershell
# Check status
docker-compose ps dashboard

# View logs
docker logs playmetric-dashboard --tail 50

# Restart
docker-compose restart dashboard

# Access at http://localhost:3000
```

### Emulator Not Booting

```powershell
# Check boot status
docker exec playmetric-emulator getprop sys.boot_completed

# Should output: 1 (means booted)

# Check logs if not booting
docker logs playmetric-emulator --tail 100

# Verify Redroid container is running
docker ps | findstr emulator

# Restart emulator
docker-compose restart emulator

# Check live stream status
curl http://localhost:8006/status
```

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
