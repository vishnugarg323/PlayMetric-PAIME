"""
Agent Service V2 - Advanced RL with Database Integration
"""
import os
import sys
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import httpx
import uvicorn
import numpy as np
import cv2

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
sys.path.insert(0, '/app/shared')

try:
    from database import DatabaseManager
except ModuleNotFoundError:
    # Fallback: no database support
    DatabaseManager = None
from .actions import ActionSpace, ActionType
from .agents.random_agent import RandomAgent
from .agents.heuristic_agent import HeuristicAgent
from .agents.advanced_rl_agent import AdvancedRLAgent
from .game_intelligence import GameIntelligence

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
agent = None
action_space = None
game_intelligence = None  # Smart game analysis engine
play_task: Optional[asyncio.Task] = None
is_playing = False
ai_active = False  # NEW: Controls when AI actually starts making actions
observation_url = None
observation_service_url = None
emulator_manager_url = None
orchestrator_url = None
http_client: Optional[httpx.AsyncClient] = None
db_manager = None

# Session context
current_session_id = None
current_game_id = None
current_package_name = None

# Training control
training_enabled = True
training_interval = 10  # Train every N steps
steps_since_training = 0

# Current screenshot tracking for dashboard
current_screenshot_path = None
current_screenshot_count = 0


# Pydantic models
class StartPlayingRequest(BaseModel):
    agent_mode: str = "heuristic"  # random, heuristic, advanced_rl
    session_id: str
    game_id: str
    package_name: str
    enable_training: bool = True
    training_interval: int = 10


class TrainingConfig(BaseModel):
    enabled: bool = True
    interval: int = 10


class SaveModelRequest(BaseModel):
    version: int = 1


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global action_space, observation_url, observation_service_url, emulator_manager_url, orchestrator_url, http_client, db_manager
    
    # Startup
    logger.info("Starting AI Agent Service V2...")
    
    # Initialize database (if available)
    if DatabaseManager is not None:
        try:
            db_manager = DatabaseManager()
            await db_manager.connect()
            logger.info("Database connected")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Running without database support.")
            db_manager = None
    else:
        logger.warning("DatabaseManager not available. Running without database support.")
    
    # Initialize action space
    screen_width = int(os.getenv("SCREEN_WIDTH", "1080"))
    screen_height = int(os.getenv("SCREEN_HEIGHT", "1920"))
    action_space = ActionSpace(screen_width=screen_width, screen_height=screen_height)
    
    # Get service URLs
    observation_url = os.getenv("OBSERVATION_URL", "http://observation:8001")
    observation_service_url = observation_url  # Alias for clarity
    emulator_manager_url = os.getenv("EMULATOR_MANAGER_URL", "http://emulator-manager:8005")
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    
    # Create HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    logger.info("AI Agent Service V2 ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Service V2...")
    await stop_playing()
    if http_client:
        await http_client.aclose()
    if db_manager:
        await db_manager.disconnect()


app = FastAPI(
    title="PlayMetric AI Agent V2",
    description="Advanced RL agent with database-backed learning",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)


async def play_loop():
    """Main gameplay loop with RL training"""
    global is_playing, agent, steps_since_training, training_enabled, training_interval
    global current_session_id, ai_active, current_screenshot_path, current_screenshot_count
    
    action_interval = 2.0  # 2 seconds between actions for better visibility
    logger.info(f"Starting gameplay loop (interval: {action_interval}s - Balanced mode for analysis and testing)")
    
    # Wait for AI to be manually activated
    logger.info("⏸️  Waiting for manual AI activation...")
    while not ai_active and is_playing:
        await asyncio.sleep(1)
    
    if not is_playing:
        logger.info("Session stopped before AI activation")
        return
    
    logger.info("▶️  AI ACTIVATED - Starting gameplay immediately!")
    
    # User manually starts AI after game is already launched - no need to wait
    logger.info("✅ Game is ready, starting AI gameplay now...")
    
    last_state = None
    last_action = None
    last_action_params = None
    episode_reward = 0
    
    # Action counters for tracking
    action_counts = {
        'tap': 0,
        'swipe_up': 0,
        'swipe_down': 0,
        'swipe_left': 0,
        'swipe_right': 0,
        'back': 0,
        'wait': 0
    }
    
    while is_playing:
        try:
            # ===  CAPTURE FRESH SCREENSHOT FOR ANALYSIS ===
            # Get fresh screenshot directly from emulator-manager (not cached)
            fresh_screenshot = None
            try:
                logger.info("📸 Capturing fresh screenshot for AI analysis...")
                screenshot_response = await http_client.get(f"{emulator_manager_url}/screenshot/info")
                if screenshot_response.status_code == 200:
                    screenshot_info = screenshot_response.json()
                    fresh_screenshot = screenshot_info.get('path')
                    
                    # Store globally for dashboard access
                    current_screenshot_path = fresh_screenshot
                    current_screenshot_count += 1
                    
                    logger.info(f"✅ Screenshot captured (#{current_screenshot_count}): {fresh_screenshot}")
            except Exception as e:
                logger.warning(f"Failed to capture fresh screenshot: {e}")
            
            # Get current observation (for other data like UI elements)
            observation = await get_observation()
            
            # Use fresh screenshot if available, otherwise fall back to observation's cached screenshot
            screenshot = fresh_screenshot if fresh_screenshot else observation.get('screenshot')
            
            # === SMART GAME ANALYSIS ===
            ocr_data = {}
            ui_elements = []
            screenshot_comparison = {}
            
            if screenshot and game_intelligence:
                # Extract text using OCR
                ocr_data = game_intelligence.extract_text_from_screenshot(screenshot)
                if ocr_data.get('text'):
                    logger.info(f"📝 OCR detected text: {ocr_data['text'][:100]}...")
                if ocr_data.get('buttons_detected'):
                    logger.info(f"🎯 Found {len(ocr_data['buttons_detected'])} clickable buttons")
                
                # Detect UI elements
                ui_elements = game_intelligence.detect_ui_elements(screenshot)
                if ui_elements:
                    logger.info(f"🎮 Detected {len(ui_elements)} UI elements")
                
                # Compare with previous screenshot
                screenshot_comparison = game_intelligence.compare_screenshots(screenshot)
                if screenshot_comparison.get('changed_significantly'):
                    logger.info(f"✅ Screen changed significantly! Similarity: {screenshot_comparison['similarity_score']:.2%}")
            
            # Load screenshot for RL agent
            if isinstance(agent, AdvancedRLAgent) and screenshot:
                screenshot_array = load_screenshot(screenshot)
                current_state = agent.preprocess_observation(screenshot_array)
            else:
                current_state = None
            
            # Calculate smart reward with game understanding
            if game_intelligence:
                screen_changed = screenshot_comparison.get('changed_significantly', False)
                reward = game_intelligence.calculate_smart_reward(
                    observation, screen_changed, ocr_data
                )
            else:
                reward = calculate_reward(observation)
            episode_reward += reward
            
            # Store transition if we have previous state
            if isinstance(agent, AdvancedRLAgent) and last_state is not None:
                await agent.store_transition(
                    state=last_state,
                    action=last_action,
                    action_params=last_action_params,
                    reward=reward,
                    next_state=current_state,
                    done=False,  # Game doesn't end
                    level_identifier=observation.get('level', 'unknown')
                )
                
                # Train periodically
                if training_enabled:
                    steps_since_training += 1
                    if steps_since_training >= training_interval:
                        loss = agent.train_step()
                        if loss is not None:
                            logger.info(f"Training loss: {loss:.4f}, Epsilon: {agent.epsilon:.4f}")
                        steps_since_training = 0
            
            # === SMART ACTION DECISION ===
            smart_recommendation = None
            if game_intelligence:
                screen_changed = screenshot_comparison.get('changed_significantly', False)
                smart_recommendation = game_intelligence.get_smart_action_recommendation(
                    ocr_data, ui_elements, screen_changed
                )
            
            # Decide action: Smart recommendation overrides RL agent
            if smart_recommendation:
                # Use smart recommendation (OCR-detected buttons, UI elements, or stuck recovery)
                action_name = smart_recommendation['action']
                
                if action_name == 'tap' and smart_recommendation['coordinates']:
                    action = action_space.get_tap_at(
                        smart_recommendation['coordinates'][0],
                        smart_recommendation['coordinates'][1]
                    )
                elif action_name == 'swipe_up':
                    action = action_space.get_swipe_up()
                elif action_name == 'swipe_down':
                    action = action_space.get_swipe_down()
                elif action_name == 'back':
                    action = action_space.get_back_action()
                else:
                    # Fallback to random action
                    action = action_space.get_random_tap()
                
                reasoning = smart_recommendation['reasoning']
                
                # Add OCR text to reasoning if available
                ocr_text = ocr_data.get('text', '')
                if ocr_text:
                    reasoning = f"{reasoning}\n\n📝 OCR detected text: {ocr_text[:200]}"
                
                await broadcast_ai_thinking({
                    "type": "smart_decision",
                    "action": action.action_type.value,
                    "position": {"x": action.x, "y": action.y},
                    "reasoning": reasoning,
                    "ocr_text": ocr_text[:500] if ocr_text else None,  # Include raw OCR text
                    "ocr_detected": bool(ocr_data.get('buttons_detected')),
                    "ui_elements_detected": len(ui_elements),
                    "screen_changed": screenshot_comparison.get('changed_significantly', False),
                    "stuck": game_intelligence.is_stuck() if game_intelligence else False,
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
                
            elif isinstance(agent, AdvancedRLAgent) and current_state is not None:
                # Use RL agent if no smart recommendation
                action_index = agent.select_action(current_state, training=training_enabled)
                action = action_space.get_action_by_index(action_index)
                
                # Determine reasoning with more context
                is_exploring = (action_index == agent.last_exploration_action if hasattr(agent, 'last_exploration_action') else False)
                q_vals = agent.last_q_values if hasattr(agent, 'last_q_values') and agent.last_q_values is not None else None
                
                # Build meaningful reasoning based on context
                action_name = action.action_type.value.upper()
                if is_exploring:
                    reasoning = f"🎲 EXPLORING: Trying random {action_name} to discover new strategies (exploration rate: {agent.epsilon:.1%})"
                elif q_vals is not None:
                    max_q = float(q_vals.max())
                    avg_q = float(q_vals.mean())
                    confidence = "HIGH" if max_q > avg_q + 0.5 else "MEDIUM" if max_q > avg_q else "LOW"
                    reasoning = f"🧠 EXPLOITING ({confidence} confidence): {action_name} predicted best outcome (Q-value: {max_q:.2f}, avg: {avg_q:.2f}). Learning from {len(agent.memory) if hasattr(agent, 'memory') else 0} past experiences."
                else:
                    reasoning = f"🤖 ANALYZING: Choosing {action_name} based on screen analysis ({len(ui_elements)} UI elements detected)"
                
                # Broadcast AI thinking with detailed info
                await broadcast_ai_thinking({
                    "type": "rl_decision",
                    "action": action.action_type.value,
                    "action_index": action_index,
                    "position": {"x": action.x, "y": action.y},
                    "epsilon": round(agent.epsilon, 4),
                    "q_values": q_vals.tolist() if q_vals is not None else None,
                    "exploration": is_exploring,
                    "reasoning": reasoning,
                    "step": agent.steps if hasattr(agent, 'steps') else 0,
                    "memory_size": len(agent.memory) if hasattr(agent, 'memory') else 0,
                    "episode_reward": round(episode_reward, 2),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
            else:
                # Fallback to rule-based agent
                action = agent.decide_action(observation)
                
                await broadcast_ai_thinking({
                    "type": "rule_based_decision",
                    "action": action.action_type.value,
                    "position": {"x": action.x, "y": action.y},
                    "reasoning": f"📋 Heuristic: {action.action_type.value} at ({action.x}, {action.y}) - Found {len(ui_elements)} UI elements",
                    "ui_elements_count": len(ui_elements),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
            
            # Execute action
            logger.info(f"🎯 Executing action: {action.action_type.value} at ({action.x}, {action.y})")
            await execute_action(action)
            logger.info(f"⏳ Waiting {action_interval} seconds before next action...")
            
            # Cleanup temporary fresh screenshot
            if fresh_screenshot and os.path.exists(fresh_screenshot):
                try:
                    os.remove(fresh_screenshot)
                except Exception as e:
                    logger.debug(f"Could not remove temp screenshot: {e}")
            
            # Record action result in game intelligence
            if game_intelligence:
                screen_changed = screenshot_comparison.get('changed_significantly', False)
                game_intelligence.record_action_result(
                    action=action.action_type.value,
                    coordinates=(action.x, action.y),
                    screen_changed=screen_changed,
                    reward=reward
                )
            
            # Track action counts
            action_key = action.action_type.value.lower().replace(' ', '_')
            if action_key in action_counts:
                action_counts[action_key] += 1
            
            # Update session metrics in database
            total_actions = sum(action_counts.values())
            logger.info(f"🔍 PRE-CHECK: total_actions={total_actions}, db_manager={'EXISTS' if db_manager else 'NONE'}, current_session_id={current_session_id if current_session_id else 'NONE'}")
            
            if not db_manager:
                logger.warning("⚠️ db_manager is None - cannot update session metrics")
            if not current_session_id:
                logger.warning(f"⚠️ current_session_id is None - cannot update session metrics")
            
            if db_manager and current_session_id:
                try:
                    total_actions = sum(action_counts.values())
                    query = """
                    UPDATE sessions 
                    SET total_actions = $1
                    WHERE id = $2
                    """
                    await db_manager.execute_write(query, total_actions, current_session_id)
                    if total_actions % 10 == 0:  # Log every 10 actions to reduce noise
                        logger.info(f"📊 Session metrics updated: {total_actions} total actions")
                except Exception as e:
                    logger.error(f"❌ Failed to update session metrics: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Log detailed action info
            logger.info(f"Action #{sum(action_counts.values())}: {action.action_type.value} at ({action.x}, {action.y}) | "
                       f"Taps: {action_counts['tap']}, Swipes: {sum([action_counts[k] for k in action_counts if 'swipe' in k])}")
            
            # Store for next iteration
            last_state = current_state
            last_action = action_space.action_to_index(action.action_type) if current_state is not None else None
            last_action_params = {
                'x': action.x,
                'y': action.y,
                'x2': getattr(action, 'x2', None),
                'y2': getattr(action, 'y2', None),
                'duration': getattr(action, 'duration', None)
            }
            
            # Wait before next action
            await asyncio.sleep(action_interval)
            
        except Exception as e:
            logger.error(f"Error in play loop: {e}", exc_info=True)
            await asyncio.sleep(5)


def load_screenshot(screenshot_path: str) -> Optional[np.ndarray]:
    """Load screenshot from path"""
    try:
        if screenshot_path and os.path.exists(screenshot_path):
            img = cv2.imread(screenshot_path)
            return img
    except Exception as e:
        logger.error(f"Error loading screenshot: {e}")
    return None


def calculate_reward(observation: dict) -> float:
    """
    Calculate reward based on observation
    Optimized for puzzle games
    """
    reward = 0.0
    
    # Base reward for taking action (encourages exploration)
    reward += 0.01
    
    # Penalty for crashes
    if observation.get('crashed', False):
        reward -= 10.0
    
    # Reward for level completion (if detected)
    if observation.get('level_complete', False):
        reward += 5.0
    
    # Reward for progress (score increase, level change)
    score_change = observation.get('score_change', 0)
    if score_change > 0:
        reward += min(score_change * 0.1, 2.0)  # Cap at 2.0
    
    # Small penalty for inactivity
    if observation.get('no_change', False):
        reward -= 0.05
    
    return reward


async def get_observation():
    """Get current game state observation"""
    try:
        # Get latest screenshot
        response = await http_client.get(f"{observation_url}/capture/status")
        data = response.json()
        
        screenshot_path = data.get('last_screenshot')
        
        # Get UI elements
        ui_elements = []
        try:
            ui_response = await http_client.get(f"{observation_url}/analysis/ui-elements")
            ui_data = ui_response.json()
            ui_elements = ui_data.get('ui_elements', [])
        except Exception as e:
            logger.debug(f"Could not get UI elements: {e}")
        
        return {
            'screenshot': screenshot_path,
            'ui_elements': ui_elements,
            'action_count': agent.action_count if hasattr(agent, 'action_count') else 0,
            'level': 'unknown',  # TODO: Extract from OCR
            'score_change': 0,  # TODO: Track score
            'level_complete': False,  # TODO: Detect completion
            'crashed': False,  # TODO: Check crash detector
            'no_change': False  # TODO: Compare screenshots
        }
        
    except Exception as e:
        logger.error(f"Error getting observation: {e}")
        return {
            'screenshot': None,
            'ui_elements': [],
            'crashed': True  # Penalize observation errors
        }


async def execute_action(action):
    """Execute action via emulator-manager service"""
    try:
        if action.action_type == ActionType.TAP:
            logger.info(f"📱 ADB COMMAND: adb shell input tap {action.x} {action.y}")
            await http_client.post(
                f"{emulator_manager_url}/input/tap",
                json={"x": action.x, "y": action.y}
            )
            
        elif action.action_type in [ActionType.SWIPE_UP, ActionType.SWIPE_DOWN, 
                                     ActionType.SWIPE_LEFT, ActionType.SWIPE_RIGHT]:
            logger.info(f"📱 ADB COMMAND: adb shell input swipe {action.x} {action.y} {action.x2} {action.y2} {action.duration}")
            await http_client.post(
                f"{emulator_manager_url}/input/swipe",
                json={
                    "x1": action.x,
                    "y1": action.y,
                    "x2": action.x2,
                    "y2": action.y2,
                    "duration": action.duration
                }
            )
            
        elif action.action_type == ActionType.BACK:
            logger.info(f"📱 ADB COMMAND: adb shell input keyevent KEYCODE_BACK")
            await http_client.post(
                f"{emulator_manager_url}/input/back"
            )
            
        elif action.action_type == ActionType.WAIT:
            # Just wait, no action needed
            logger.info(f"⏸️  ACTION: Wait (no ADB command)")
            pass
            
        logger.info(f"✅ Executed action: {action.action_type.value}")
        
        # Capture and broadcast screenshot after action
        if current_session_id:
            await capture_and_broadcast_screenshot()
        
    except Exception as e:
        logger.error(f"Error executing action: {e}")


async def broadcast_ai_thinking(thinking_data: dict):
    """Broadcast AI thinking/decisions to orchestrator and save to database"""
    try:
        if current_session_id and db_manager:
            # Save to database for persistence
            try:
                await db_manager.execute(
                    """
                    INSERT INTO ai_thinking_logs 
                    (session_id, action_type, reasoning, q_values, epsilon, position, ui_context)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    current_session_id,
                    thinking_data.get('action'),
                    thinking_data.get('reasoning'),
                    thinking_data.get('q_values'),  # JSONB
                    thinking_data.get('epsilon'),
                    thinking_data.get('position'),  # JSONB
                    f"UI elements: {thinking_data.get('ui_elements_count', 0)}, Memory: {thinking_data.get('memory_size', 0)}"
                )
            except Exception as db_err:
                logger.debug(f"Could not save AI thinking to DB: {db_err}")
            
            # Broadcast via WebSocket
            await http_client.post(
                f"{orchestrator_url}/internal/broadcast_ai_thinking",
                json={
                    "session_id": current_session_id,
                    "thinking": thinking_data,
                    "timestamp": thinking_data.get('timestamp')
                },
                timeout=2.0
            )
    except Exception as e:
        logger.debug(f"Could not broadcast AI thinking: {e}")


async def capture_and_broadcast_screenshot():
    """Capture screenshot and broadcast via WebSocket - with fallback to observation service"""
    try:
        # Try emulator-manager first
        try:
            response = await http_client.get(f"{emulator_manager_url}/screenshot", timeout=3.0)
            if response.status_code == 200:
                screenshot_data = response.json()
                screenshot_path = screenshot_data.get('path')
                
                # Save to database and increment counter
                if screenshot_path and current_session_id:
                    try:
                        await db_manager.execute(
                            """INSERT INTO screenshots (session_id, file_path, timestamp)
                               VALUES ($1, $2, NOW())""",
                            current_session_id, screenshot_path
                        )
                        
                        # Increment total_screenshots counter
                        await db_manager.execute_write(
                            """UPDATE sessions 
                               SET total_screenshots = total_screenshots + 1 
                               WHERE id = $1""",
                            current_session_id
                        )
                        logger.debug(f"📸 Screenshot saved and counter incremented")
                    except Exception as db_err:
                        logger.error(f"Failed to save screenshot to database: {db_err}")
                    
                    # Broadcast to orchestrator for WebSocket streaming
                    await http_client.post(
                        f"{orchestrator_url}/internal/broadcast_screenshot",
                        json={
                            "session_id": current_session_id,
                            "screenshot_path": screenshot_path,
                            "timestamp": screenshot_data.get('timestamp')
                        },
                        timeout=2.0
                    )
                return
        except Exception as emulator_err:
            logger.debug(f"Emulator-manager unavailable, using observation service: {emulator_err}")
        
        # Fallback: Use observation service
        response = await http_client.get(
            f"{observation_service_url}/observation/capture",
            params={"session_id": current_session_id},
            timeout=5.0
        )
        if response.status_code == 200:
            obs_data = response.json()
            screenshot_path = obs_data.get('screenshot_path')
            
            if screenshot_path and current_session_id:
                # Broadcast via orchestrator
                await http_client.post(
                    f"{orchestrator_url}/internal/broadcast_screenshot",
                    json={
                        "session_id": current_session_id,
                        "screenshot_path": screenshot_path,
                        "timestamp": obs_data.get('timestamp')
                    },
                    timeout=2.0
                )
                
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")


async def stop_playing():
    """Stop the gameplay loop"""
    global is_playing, play_task, agent, current_game_id, current_session_id
    
    if is_playing:
        is_playing = False
        if play_task:
            play_task.cancel()
            try:
                await play_task
            except asyncio.CancelledError:
                pass
        
        # Update session end time and calculate duration
        if current_session_id:
            try:
                await db_manager.execute_write(
                    """UPDATE sessions 
                       SET completed_at = NOW(),
                           duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER,
                           status = 'completed'
                       WHERE id = $1""",
                    current_session_id
                )
                logger.info(f"Session {current_session_id} completed and duration calculated")
            except Exception as e:
                logger.error(f"Failed to update session end time: {e}")
        
        # Save RL model if applicable
        if isinstance(agent, AdvancedRLAgent) and current_game_id:
            try:
                await agent.save_model(current_game_id)
                logger.info("Saved RL model")
            except Exception as e:
                logger.error(f"Error saving model: {e}")
        
        logger.info("Gameplay stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "playing": is_playing,
        "agent_type": agent.__class__.__name__ if agent else None,
        "training_enabled": training_enabled,
        "db_connected": db_manager is not None
    }


@app.post("/play/start")
async def start_playing(request: StartPlayingRequest):
    """Start automated gameplay with advanced RL"""
    global agent, is_playing, play_task, current_session_id, current_game_id
    global current_package_name, training_enabled, training_interval, game_intelligence, ai_active
    
    if is_playing:
        return {"message": "Already playing", "agent": agent.__class__.__name__}
    
    # Reset AI activation state (must be manually activated)
    ai_active = False
    logger.info("⏸️  Session started - AI waiting for manual activation")
    
    # Initialize game intelligence engine
    game_intelligence = GameIntelligence()
    logger.info("🧠 Initialized smart game intelligence engine with OCR and screenshot analysis")
    
    # Store session context
    current_session_id = request.session_id
    current_game_id = request.game_id
    current_package_name = request.package_name
    training_enabled = request.enable_training
    training_interval = request.training_interval
    
    # Update session started_at in database
    if db_manager and current_session_id:
        try:
            await db_manager.execute_write(
                "UPDATE sessions SET started_at = NOW(), status = 'running' WHERE id = $1",
                current_session_id
            )
            logger.info(f"✅ Session {current_session_id} started at {__import__('datetime').datetime.now()}")
        except Exception as e:
            logger.error(f"Failed to update session started_at: {e}")
    
    # Create agent based on mode
    if request.agent_mode == "random":
        config = {}
        agent = RandomAgent(action_space, config)
        
    elif request.agent_mode == "advanced_rl":
        # Create advanced RL agent with database backing
        agent = AdvancedRLAgent(
            state_dim=128,
            action_dim=action_space.get_action_count(),
            learning_rate=0.001,
            gamma=0.99,
            epsilon_start=1.0 if training_enabled else 0.01,
            epsilon_end=0.01,
            epsilon_decay=0.995,
            batch_size=64,
            target_update_freq=1000
        )
        
        # Initialize with database
        await agent.initialize_from_db(db_manager, current_game_id, current_session_id)
        logger.info(f"Initialized RL agent with {len(agent.memory)} experiences")
        
    else:  # heuristic (default)
        config = {}
        agent = HeuristicAgent(action_space, config)
    
    logger.info(f"Starting gameplay with {agent.__class__.__name__}")
    
    # Start observation capture
    try:
        await http_client.post(
            f"{observation_url}/capture/start",
            json={"session_id": request.session_id}
        )
    except Exception as e:
        logger.warning(f"Could not start capture: {e}")
    
    # Start gameplay
    is_playing = True
    play_task = asyncio.create_task(play_loop())
    
    return {
        "message": "Gameplay started",
        "agent": agent.__class__.__name__,
        "session_id": request.session_id,
        "game_id": request.game_id,
        "training_enabled": training_enabled
    }


@app.options("/play/activate")
async def activate_ai_options():
    """Handle OPTIONS request for CORS preflight"""
    return {"message": "OK"}

@app.post("/play/activate")
async def activate_ai():
    """Activate AI to start playing (after game is launched)"""
    global ai_active
    
    if not is_playing:
        raise HTTPException(status_code=400, detail="No active session. Start a session first.")
    
    ai_active = True
    logger.info("▶️  AI ACTIVATED by user")
    
    return {
        "message": "AI activated - gameplay will begin",
        "ai_active": True,
        "session_id": current_session_id
    }


@app.options("/play/pause")
async def pause_ai_options():
    """Handle OPTIONS request for CORS preflight"""
    return {"message": "OK"}

@app.post("/play/pause")
async def pause_ai():
    """Pause AI gameplay"""
    global ai_active
    
    ai_active = False
    logger.info("⏸️  AI PAUSED by user")
    
    return {
        "message": "AI paused",
        "ai_active": False,
        "session_id": current_session_id
    }


@app.post("/play/stop")
async def stop_playing_endpoint():
    """Stop automated gameplay"""
    global ai_active
    ai_active = False
    await stop_playing()
    
    # Get final statistics
    stats = {}
    if isinstance(agent, AdvancedRLAgent):
        stats = {
            'episodes': agent.episodes,
            'steps': agent.steps,
            'epsilon': agent.epsilon,
            'memory_size': len(agent.memory),
            'average_loss': np.mean(agent.losses[-100:]) if agent.losses else 0.0
        }
    elif hasattr(agent, 'get_statistics'):
        stats = agent.get_statistics()
    
    return {
        "message": "Gameplay stopped",
        "statistics": stats
    }


@app.get("/play/status")
async def play_status():
    """Get gameplay status"""
    stats = {}
    if isinstance(agent, AdvancedRLAgent):
        stats = {
            'episodes': agent.episodes,
            'steps': agent.steps,
            'epsilon': agent.epsilon,
            'memory_size': len(agent.memory),
            'training_enabled': training_enabled
        }
    elif hasattr(agent, 'get_statistics'):
        stats = agent.get_statistics()
    
    return {
        "playing": is_playing,
        "ai_active": ai_active,
        "agent": agent.__class__.__name__ if agent else None,
        "session_id": current_session_id,
        "game_id": current_game_id,
        "statistics": stats
    }


@app.get("/play/latest-screenshot")
async def get_latest_screenshot():
    """Get the latest screenshot path that AI is currently analyzing"""
    global current_screenshot_path, current_screenshot_count, ai_active
    
    try:
        return {
            "latest_screenshot": current_screenshot_path,
            "screenshot_count": current_screenshot_count,
            "capturing": ai_active and is_playing,
            "session_id": current_session_id,
            "ai_active": ai_active,
            "status": "analyzing" if ai_active else "paused"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/play/current-screenshot-image")
async def get_current_screenshot_image():
    """Serve the actual screenshot image that AI is analyzing"""
    global current_screenshot_path
    
    if not current_screenshot_path or not os.path.exists(current_screenshot_path):
        # Fallback: get fresh screenshot from emulator-manager
        try:
            screenshot_response = await http_client.get(f"{emulator_manager_url}/screenshot")
            if screenshot_response.status_code == 200:
                from fastapi.responses import Response
                return Response(content=screenshot_response.content, media_type="image/png")
        except:
            pass
        raise HTTPException(status_code=404, detail="No screenshot available")
    
    from fastapi.responses import FileResponse
    return FileResponse(current_screenshot_path, media_type="image/png")


@app.get("/agent/statistics")
async def get_agent_statistics():
    """Get detailed agent statistics"""
    if not agent:
        raise HTTPException(status_code=404, detail="No active agent")
    
    if isinstance(agent, AdvancedRLAgent):
        return {
            'agent_type': 'AdvancedRLAgent',
            'episodes': agent.episodes,
            'steps': agent.steps,
            'epsilon': agent.epsilon,
            'memory_size': len(agent.memory),
            'memory_capacity': agent.memory.capacity,
            'recent_losses': agent.losses[-10:] if agent.losses else [],
            'average_loss_100': np.mean(agent.losses[-100:]) if agent.losses else 0.0,
            'training_enabled': training_enabled,
            'training_interval': training_interval
        }
    elif hasattr(agent, 'get_statistics'):
        return agent.get_statistics()
    else:
        return {'agent_type': agent.__class__.__name__}


@app.post("/agent/training/configure")
async def configure_training(config: TrainingConfig):
    """Configure training parameters"""
    global training_enabled, training_interval
    
    training_enabled = config.enabled
    training_interval = config.interval
    
    return {
        "message": "Training configuration updated",
        "enabled": training_enabled,
        "interval": training_interval
    }


@app.post("/agent/model/save")
async def save_model(request: SaveModelRequest):
    """Manually save current RL model"""
    if not isinstance(agent, AdvancedRLAgent):
        raise HTTPException(status_code=400, detail="Current agent is not an RL agent")
    
    if not current_game_id:
        raise HTTPException(status_code=400, detail="No active game session")
    
    try:
        await agent.save_model(current_game_id, version=request.version)
        return {
            "message": "Model saved successfully",
            "game_id": current_game_id,
            "version": request.version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save model: {str(e)}")


@app.get("/agent/memory/stats")
async def get_memory_stats():
    """Get experience replay memory statistics"""
    if not isinstance(agent, AdvancedRLAgent):
        raise HTTPException(status_code=400, detail="Current agent is not an RL agent")
    
    return {
        "size": len(agent.memory),
        "capacity": agent.memory.capacity,
        "utilization": len(agent.memory) / agent.memory.capacity * 100,
        "alpha": agent.memory.alpha,
        "beta": agent.memory.beta,
        "game_id": current_game_id,
        "session_id": current_session_id
    }


if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
