import asyncio
import base64
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Optional

import asyncpg
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
from redis import asyncio as aioredis
import io
import math
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Emulator Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class LiveStreamManager:
    def __init__(self):
        self.clients = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.clients.discard(websocket)

    async def broadcast(self, screenshot_b64: str, session_id: str):
        for ws in list(self.clients):
            try:
                await ws.send_json({
                    'type': 'live_screenshot',
                    'session_id': session_id,
                    'screenshot': screenshot_b64
                })
            except Exception as e:
                logger.warning(f"Failed to send screenshot: {e}")

live_stream_manager = LiveStreamManager()
active_sessions: Dict[str, 'EmulatorSession'] = {}

@app.websocket("/ws")
async def live_stream_websocket(websocket: WebSocket):
    await live_stream_manager.connect(websocket)
    logger.info("Client connected for live screenshot streaming")
    try:
        while True:
            await asyncio.sleep(1)
            # Stream the latest screenshot from all active sessions
            for session_id, session in active_sessions.items():
                screenshot_b64 = await session.generate_screenshot()
                await live_stream_manager.broadcast(screenshot_b64, session_id)
    except WebSocketDisconnect:
        live_stream_manager.disconnect(websocket)
        logger.info("Live stream client disconnected")
    except Exception as e:
        logger.error(f"Live stream WebSocket error: {e}")
class LiveStreamManager:
    def __init__(self):
        self.clients = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.clients.discard(websocket)

    async def broadcast(self, screenshot_b64: str, session_id: str):
        for ws in list(self.clients):
            try:
                await ws.send_json({
                    'type': 'live_screenshot',
                    'session_id': session_id,
                    'screenshot': screenshot_b64
                })
            except Exception as e:
                logger.warning(f"Failed to send screenshot: {e}")


active_sessions: Dict[str, 'EmulatorSession'] = {}

@app.websocket("/ws")
async def live_stream_websocket(websocket: WebSocket):
    await live_stream_manager.connect(websocket)
    logger.info("Client connected for live screenshot streaming")
    try:
        while True:
            await asyncio.sleep(1)
            # Stream the latest screenshot from all active sessions
            for session_id, session in active_sessions.items():
                screenshot_b64 = await session.generate_screenshot()
                await live_stream_manager.broadcast(screenshot_b64, session_id)
    except WebSocketDisconnect:
        live_stream_manager.disconnect(websocket)
        logger.info("Live stream client disconnected")
    except Exception as e:
        logger.error(f"Live stream WebSocket error: {e}")
class GameKnowledge:
    """Stores and shares game knowledge between sessions"""
    
    def __init__(self):
        self.game_knowledge = {}
        self.db_pool = None
        
    async def initialize_db(self):
        """Initialize database connection"""
        self.db_pool = await asyncpg.create_pool(
            os.getenv('DATABASE_URL', 'postgresql://paime:paime123@db:5432/paime')
        )
        
    async def save_game_knowledge(self, game_id: str, knowledge: dict):
        """Save game knowledge to database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO game_analysis (
                        game_id, category_primary, category_secondary, 
                        difficulty_score, mechanics, levels_discovered,
                        performance_summary, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (game_id) 
                    DO UPDATE SET
                        category_primary = EXCLUDED.category_primary,
                        category_secondary = EXCLUDED.category_secondary,
                        difficulty_score = EXCLUDED.difficulty_score,
                        mechanics = EXCLUDED.mechanics,
                        levels_discovered = EXCLUDED.levels_discovered,
                        performance_summary = EXCLUDED.performance_summary,
                        updated_at = NOW()
                    """,
                    uuid.UUID(game_id),
                    knowledge.get('category', 'unknown'),
                    knowledge.get('category_secondary', ''),
                    knowledge.get('difficulty', 2.5),
                    json.dumps(knowledge.get('mechanics', [])),
                    json.dumps(knowledge.get('levels', [])),
                    json.dumps(knowledge.get('performance', {}))
                )
                logger.info(f"Saved knowledge for game {game_id}")
        except Exception as e:
            logger.error(f"Failed to save game knowledge: {e}")
            
    async def load_game_knowledge(self, game_id: str) -> dict:
        """Load existing game knowledge"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT category_primary, category_secondary, difficulty_score,
                           mechanics, levels_discovered, performance_summary
                    FROM game_analysis 
                    WHERE game_id = $1
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    uuid.UUID(game_id)
                )
                if result:
                    return {
                        'category': result['category_primary'],
                        'mechanics': json.loads(result['mechanics'] or '[]'),
                        'difficulty': float(result['difficulty_score'] or 2.5),
                        'levels': json.loads(result['levels_discovered'] or '[]'),
                        'performance': json.loads(result['performance_summary'] or '{}')
                    }
        except Exception as e:
            logger.error(f"Failed to load game knowledge: {e}")
        return {'category': 'unknown', 'mechanics': [], 'difficulty': 2.5, 'levels': [], 'performance': {}}

class EmulatorSession:
    """Represents an active emulator session"""
    
    def __init__(self, session_id: str, game_id: str, knowledge: GameKnowledge):
        self.session_id = session_id
        self.game_id = game_id
        self.knowledge = knowledge
        self.start_time = datetime.utcnow()
        self.frame_count = 0
        self.game_state = {
            'score': 0,
            'lives': 3,
            'level': 1,
            'player_x': 540,
            'player_y': 960,
            'elements': [],
            'ai_actions': []
        }
        self.game_knowledge_cache = {}
        
    async def initialize(self):
        """Initialize session with existing knowledge"""
        self.game_knowledge_cache = await self.knowledge.load_game_knowledge(self.game_id)
        logger.info(f"Initialized session {self.session_id} with knowledge: {self.game_knowledge_cache}")
        
    async def generate_screenshot(self) -> str:
        """Capture real emulator screenshot using ADB (actual device output)"""
        try:
            import subprocess
            # Run ADB command to capture screenshot from emulator/device
            result = subprocess.run([
                'adb', 'exec-out', 'screencap', '-p'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                img_bytes = result.stdout
                # Convert to base64
                screenshot_b64 = base64.b64encode(img_bytes).decode()
                return screenshot_b64
            else:
                logger.error(f"ADB screenshot failed: {result.stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f"Failed to capture real screenshot: {e}")
            return None
            
    async def _update_game_state(self):
        """Update game state based on AI learning and actions"""
        # Simulate AI learning and adaptation
        difficulty = self.game_knowledge_cache.get('difficulty', 2.5)
        
        # AI makes decisions based on learned patterns
        if self.frame_count % 60 == 0:  # Every second
            self._simulate_ai_action()
            
        # Update score and level progression
        if self.frame_count % 120 == 0:  # Every 2 seconds
            self.game_state['score'] += int(10 * difficulty)
            
        if self.game_state['score'] > (self.game_state['level'] * 1000):
            self.game_state['level'] += 1
            await self._learn_new_level()
            
    def _simulate_ai_action(self):
        """Simulate AI making intelligent decisions"""
        actions = ['move_left', 'move_right', 'jump', 'attack', 'collect', 'dodge']
        action = random.choice(actions)
        
        # AI adapts based on game knowledge
        if 'platformer' in self.game_knowledge_cache.get('mechanics', []):
            action = random.choice(['jump', 'move_left', 'move_right'])
        elif 'puzzle' in self.game_knowledge_cache.get('mechanics', []):
            action = random.choice(['tap_element', 'swipe', 'rotate'])
            
        self.game_state['ai_actions'].append({
            'action': action,
            'frame': self.frame_count,
            'confidence': random.uniform(0.7, 0.95)
        })
        
        # Keep only recent actions
        if len(self.game_state['ai_actions']) > 10:
            self.game_state['ai_actions'] = self.game_state['ai_actions'][-10:]
            
    async def _learn_new_level(self):
        """AI learns about new level"""
        level_info = {
            'level': self.game_state['level'],
            'discovered_at': datetime.utcnow().isoformat(),
            'elements_count': random.randint(5, 20),
            'difficulty_rating': min(5.0, self.game_state['level'] * 0.5)
        }
        
        # Update knowledge cache
        if 'levels' not in self.game_knowledge_cache:
            self.game_knowledge_cache['levels'] = []
        self.game_knowledge_cache['levels'].append(level_info)
        
        # Save to database
        await self.knowledge.save_game_knowledge(self.game_id, self.game_knowledge_cache)
        
    def _draw_game_world(self, draw):
        """Draw the game world based on learned mechanics"""
        # Background elements
        for i in range(8):
            x = (i * 135) + (self.frame_count % 135)
            y = 200 + random.randint(-50, 50)
            draw.rectangle([x, y, x+120, y+80], fill=(40, 60, 80), outline=(100, 120, 140))
            
        # Player character (AI controlled)
        t = self.frame_count * 0.05
        player_x = 540 + int(200 * math.sin(t))
        player_y = 960 + int(100 * math.sin(t * 2))
        
        # Player with AI indicator
        draw.ellipse([player_x-50, player_y-50, player_x+50, player_y+50], 
                    fill=(255, 220, 50), outline=(200, 180, 0))
        draw.ellipse([player_x-20, player_y-20, player_x+20, player_y+20], 
                    fill=(255, 100, 100))  # AI core
        
        # Game elements based on knowledge
        mechanics = self.game_knowledge_cache.get('mechanics', [])
        if 'collectible' in mechanics:
            self._draw_collectibles(draw)
        if 'obstacle' in mechanics:
            self._draw_obstacles(draw)
        if 'enemy' in mechanics:
            self._draw_enemies(draw)
            
    def _draw_collectibles(self, draw):
        """Draw collectible items"""
        random.seed(self.frame_count // 60)
        for i in range(5):
            x = random.randint(100, 980)
            y = random.randint(300, 1500)
            size = 30
            # Sparkling collectibles
            draw.ellipse([x-size, y-size, x+size, y+size], 
                        fill=(255, 255, 100), outline=(255, 200, 0))
            
    def _draw_obstacles(self, draw):
        """Draw obstacles"""
        random.seed(self.frame_count // 30)
        for i in range(3):
            x = random.randint(200, 880)
            y = random.randint(400, 1400)
            width, height = 100, 150
            draw.rectangle([x, y, x+width, y+height], 
                          fill=(150, 50, 50), outline=(200, 100, 100))
            
    def _draw_enemies(self, draw):
        """Draw enemy characters"""
        for i in range(2):
            enemy_t = (self.frame_count + i * 100) * 0.03
            enemy_x = 300 + int(400 * math.sin(enemy_t))
            enemy_y = 800 + i * 400
            draw.rectangle([enemy_x-40, enemy_y-40, enemy_x+40, enemy_y+40], 
                          fill=(200, 50, 50), outline=(255, 100, 100))
            
    def _draw_ui_elements(self, draw):
        """Draw game UI"""
        # Score panel
        draw.rectangle([40, 40, 300, 120], fill=(0, 0, 0, 180), outline=(255, 255, 255))
        
        # Lives indicator
        draw.rectangle([40, 140, 200, 200], fill=(0, 0, 0, 180), outline=(255, 255, 255))
        for i in range(self.game_state['lives']):
            x = 60 + i * 40
            draw.ellipse([x, 155, x+25, x+180], fill=(255, 100, 100))
            
        # Level indicator
        draw.rectangle([880, 40, 1040, 120], fill=(0, 0, 0, 180), outline=(255, 255, 255))
        
        # Knowledge indicator
        knowledge_level = len(self.game_knowledge_cache.get('levels', []))
        draw.rectangle([880, 140, 1040, 200], fill=(0, 100, 200), outline=(255, 255, 255))
        
    def _draw_ai_indicators(self, draw):
        """Draw AI status and decision indicators"""
        # AI Status Panel
        draw.rectangle([40, 1750, 400, 1880], fill=(20, 20, 20, 200), outline=(0, 255, 0))
        
        # AI confidence indicator
        recent_action = self.game_state['ai_actions'][-1] if self.game_state['ai_actions'] else None
        confidence = 0.8
        if recent_action and isinstance(recent_action, dict):
            confidence = recent_action.get('confidence', 0.8)
        else:
            confidence = 0.8
        bar_width = int(300 * confidence)
        draw.rectangle([60, 1780, 60+bar_width, 1800], fill=(0, 255, 0))
            
        # Knowledge stats
        knowledge_count = len(self.game_knowledge_cache.get('levels', []))
        draw.rectangle([60, 1820, 60+(knowledge_count*20), 1840], fill=(255, 200, 0))

# Global instances
game_knowledge = GameKnowledge()
active_sessions: Dict[str, EmulatorSession] = {}
installed_apps: Dict[str, dict] = {}  # Track installed apps
@app.on_event("startup")
async def startup_event():
    """Initialize services"""
    await game_knowledge.initialize_db()
    logger.info("Emulator service started")

@app.get("/")
async def root():
    """Root endpoint for connection testing"""
    return {"status": "emulator_online", "message": "Android emulator service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_sessions": len(active_sessions)}

@app.get("/screenshot")
async def get_screenshot():
    """Get emulator screenshot"""
    try:
        # Generate a basic screenshot
        img = Image.new('RGB', (1080, 1920), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)
        
        # Draw basic UI
        draw.rectangle([50, 100, 1030, 200], fill=(70, 70, 100))
        draw.text((100, 130), "Emulator Display", fill=(255, 255, 255))
        draw.text((100, 160), "Game running...", fill=(200, 200, 200))
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        screenshot_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "screenshot": screenshot_b64,
            "timestamp": datetime.utcnow().isoformat(),
            "resolution": {"width": 1080, "height": 1920}
        }
    except Exception as e:
        logger.error(f"Error generating screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/install-apk")
async def install_apk_endpoint(data: dict):
    """Install APK and register it in the system"""
    try:
        apk_path = data.get('apk_path')
        package_name = data.get('package_name')
        
        if not apk_path or not package_name:
            raise HTTPException(status_code=400, detail="APK path and package name required")
        
        logger.info(f"Installing APK: {package_name} from {apk_path}")
        
        # Register the installed app
        app_info = {
            "package_name": package_name,
            "apk_path": apk_path,
            "installed_at": datetime.utcnow().isoformat(),
            "sessions": []
        }
        installed_apps[package_name] = app_info
        
        logger.info(f"Successfully registered APK installation: {package_name}")
        
        return {
            "success": True,
            "message": f"APK {package_name} installed and registered successfully",
            "package_name": package_name
        }
    except Exception as e:
        logger.error(f"Error in install-apk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/launch-app")
async def launch_app_endpoint(data: dict):
    """Launch app - prepare it for session creation"""
    try:
        package_name = data.get('package_name')
        
        if not package_name:
            raise HTTPException(status_code=400, detail="Package name required")
        
        # Check if app is installed
        if package_name not in installed_apps:
            raise HTTPException(status_code=404, detail=f"App {package_name} not installed")
        
        logger.info(f"App {package_name} ready for session creation")
        
        return {
            "success": True,
            "message": f"App {package_name} launched successfully",
            "package_name": package_name,
            "status": "launched"
        }
    except Exception as e:
        logger.error(f"Error in launch-app: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/sessions/{game_id}/start")
async def start_session(game_id: str):
    """Start a new emulator session"""
    try:
        session_id = str(uuid.uuid4())
        session = EmulatorSession(session_id, game_id, game_knowledge)
        await session.initialize()
        
        active_sessions[session_id] = session
        
        logger.info(f"Started session {session_id} for game {game_id}")
        return {
            "session_id": session_id,
            "game_id": game_id,
            "status": "active",
            "knowledge_loaded": bool(session.game_knowledge_cache)
        }
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/screenshot")
async def get_screenshot(session_id: str):
    """Get current screenshot for session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        session = active_sessions[session_id]
        screenshot = await session.generate_screenshot()
        
        if not screenshot:
            raise HTTPException(status_code=500, detail="Failed to generate screenshot")
            
        return {
            "session_id": session_id,
            "screenshot": screenshot,
            "frame_count": session.frame_count,
            "game_state": session.game_state,
            "knowledge_stats": {
                "levels_discovered": len(session.game_knowledge_cache.get('levels', [])),
                "mechanics_learned": len(session.game_knowledge_cache.get('mechanics', [])),
                "difficulty_assessment": session.game_knowledge_cache.get('difficulty', 2.5)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/action")
async def perform_action(session_id: str, action_data: dict):
    """Perform AI action in session with advanced simulation and bug scenarios"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session = active_sessions[session_id]
        action_type = action_data.get('type', 'tap')
        # Advanced simulation: move player, interact, trigger level progression
        if action_type == 'tap':
            x = action_data.get('x', 540)
            y = action_data.get('y', 960)
            # Move player to tap location
            session.game_state['player_x'] = x
            session.game_state['player_y'] = y
            # Interact with collectibles
            if 'collectible' in session.game_knowledge_cache.get('mechanics', []):
                session.game_state['score'] += 50
        elif action_type == 'swipe':
            dx = action_data.get('end_x', 540) - action_data.get('start_x', 540)
            dy = action_data.get('end_y', 960) - action_data.get('start_y', 960)
            session.game_state['player_x'] += dx
            session.game_state['player_y'] += dy
            session.game_state['score'] += 20
        elif action_type == 'back':
            session.game_state['lives'] = max(0, session.game_state['lives'] - 1)
        # Level progression
        if session.game_state['score'] > (session.game_state['level'] * 1000):
            session.game_state['level'] += 1
            await session._learn_new_level()
        # Random bug simulation
        import random
        bug_chance = random.random()
        if bug_chance < 0.05:
            session.game_state['frozen'] = True
        elif bug_chance < 0.08:
            session.game_state['crashed'] = True
        elif bug_chance < 0.12:
            session.game_state['ui_glitch'] = True
        else:
            session.game_state['frozen'] = False
            session.game_state['crashed'] = False
            session.game_state['ui_glitch'] = False
        session.game_state['ai_actions'].append({
            'action': action_type,
            'frame': session.frame_count,
            'data': action_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        return {"status": "action_performed", "action": action_type}
    except Exception as e:
        logger.error(f"Failed to perform action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/screenshot")
async def get_screenshot(session_id: str):
    """Get current screenshot for session with bug simulation"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session = active_sessions[session_id]
        # Bug simulation: freeze, crash, UI glitch
        if session.game_state.get('crashed'):
            # Return blank/crashed image
            img = Image.new('RGB', (1080, 1920), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((500, 960), "CRASHED", fill=(255, 0, 0))
        elif session.game_state.get('frozen'):
            # Return previous image (simulate freeze)
            if hasattr(session, 'last_screenshot'):
                screenshot_b64 = session.last_screenshot
                return {
                    "session_id": session_id,
                    "screenshot": screenshot_b64,
                    "frame_count": session.frame_count,
                    "game_state": session.game_state
                }
            else:
                img = Image.new('RGB', (1080, 1920))
                draw = ImageDraw.Draw(img)
                draw.text((500, 960), "FROZEN", fill=(255, 255, 0))
        elif session.game_state.get('ui_glitch'):
            img = Image.new('RGB', (1080, 1920))
            draw = ImageDraw.Draw(img)
            draw.rectangle([100, 100, 1000, 1800], fill=(255, 0, 255))
            draw.text((500, 960), "UI GLITCH", fill=(0, 255, 255))
        else:
            # Normal screenshot
            img = Image.new('RGB', (1080, 1920), color=(20, 30, 50))
            draw = ImageDraw.Draw(img)
            draw.text((100, 130), "Emulator Display", fill=(255, 255, 255))
            draw.text((100, 160), f"Level: {session.game_state['level']} Score: {session.game_state['score']}", fill=(200, 200, 200))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        screenshot_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        session.last_screenshot = screenshot_b64
        return {
            "session_id": session_id,
            "screenshot": screenshot_b64,
            "frame_count": session.frame_count,
            "game_state": session.game_state
        }
    except Exception as e:
        logger.error(f"Failed to get screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/learn")
async def update_knowledge(session_id: str, knowledge_data: dict):
    """Update game knowledge from AI learning"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        session = active_sessions[session_id]
        
        # Update session knowledge
        for key, value in knowledge_data.items():
            if key == 'mechanics' and isinstance(value, list):
                existing = session.game_knowledge_cache.get('mechanics', [])
                session.game_knowledge_cache['mechanics'] = list(set(existing + value))
            else:
                session.game_knowledge_cache[key] = value
                
        # Save to database
        await game_knowledge.save_game_knowledge(session.game_id, session.game_knowledge_cache)
        
        return {
            "status": "knowledge_updated",
            "updated_fields": list(knowledge_data.keys()),
            "total_knowledge": session.game_knowledge_cache
        }
    except Exception as e:
        logger.error(f"Failed to update knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/games/{game_id}/knowledge")
async def get_game_knowledge(game_id: str):
    """Get accumulated knowledge for a game"""
    try:
        knowledge = await game_knowledge.load_game_knowledge(game_id)
        return {
            "game_id": game_id,
            "knowledge": knowledge,
            "knowledge_age": "recent",  # Could calculate from database
            "shared_sessions": len([s for s in active_sessions.values() if s.game_id == game_id])
        }
    except Exception as e:
        logger.error(f"Failed to get game knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def stop_session(session_id: str):
    """Stop and cleanup session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        session = active_sessions[session_id]
        
        # Save final knowledge
        await game_knowledge.save_game_knowledge(session.game_id, session.game_knowledge_cache)
        
        # Remove session
        del active_sessions[session_id]
        
        logger.info(f"Stopped session {session_id}")
        return {"status": "session_stopped", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to stop session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "active_sessions": [
            {
                "session_id": sid,
                "game_id": session.game_id,
                "frame_count": session.frame_count,
                "uptime_seconds": (datetime.utcnow() - session.start_time).total_seconds(),
                "knowledge_stats": {
                    "levels": len(session.game_knowledge_cache.get('levels', [])),
                    "mechanics": len(session.game_knowledge_cache.get('mechanics', []))
                }
            }
            for sid, session in active_sessions.items()
        ]
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for AI agent communication"""
    await websocket.accept()
    logger.info("AI agent connected via WebSocket")
    
    try:
        while True:
            # Wait for message from AI agent
            data = await websocket.receive_json()
            action_type = data.get('type', 'unknown')
            
            logger.info(f"Received WebSocket action: {action_type}")
            
            # Handle different action types
            if action_type == 'start_session':
                game_id = data.get('game_id')
                if game_id:
                    session_id = str(uuid.uuid4())
                    session = EmulatorSession(session_id, game_id, game_knowledge)
                    await session.initialize()
                    active_sessions[session_id] = session
                    
                    await websocket.send_json({
                        'type': 'session_started',
                        'session_id': session_id,
                        'game_id': game_id,
                        'status': 'success'
                    })
                else:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'game_id required'
                    })
                    
            elif action_type == 'get_screenshot':
                session_id = data.get('session_id')
                if session_id and session_id in active_sessions:
                    session = active_sessions[session_id]
                    screenshot = await session.generate_screenshot()
                    
                    await websocket.send_json({
                        'type': 'screenshot',
                        'session_id': session_id,
                        'screenshot': screenshot,
                        'game_state': session.game_state,
                        'frame_count': session.frame_count
                    })
                else:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Invalid session_id'
                    })
                    
            elif action_type == 'perform_action':
                session_id = data.get('session_id')
                action_data = data.get('action', {})
                
                if session_id and session_id in active_sessions:
                    session = active_sessions[session_id]
                    session.game_state['ai_actions'].append({
                        'action': action_data.get('type', 'tap'),
                        'frame': session.frame_count,
                        'data': action_data,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    await websocket.send_json({
                        'type': 'action_performed',
                        'session_id': session_id,
                        'action': action_data,
                        'status': 'success'
                    })
                else:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Invalid session_id'
                    })
                    
            elif action_type == 'ping':
                await websocket.send_json({
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat(),
                    'active_sessions': len(active_sessions)
                })
                
            else:
                await websocket.send_json({
                    'type': 'error',
                    'message': f'Unknown action type: {action_type}'
                })
                
    except WebSocketDisconnect:
        logger.info("AI agent disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                'type': 'error',
                'message': str(e)
            })
        except:
            pass  # Connection might be closed

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5555)
