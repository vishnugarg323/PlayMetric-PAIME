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
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
from .advanced_game_intelligence import AdvancedGameIntelligence
from .hybrid_intelligence import HybridGameIntelligence
from .learning_recorder import LearningRecorder
from .learning_recorder_v2 import ObservationRecorder, DecisionRecorder
from .high_performance_capture import HighPerformanceCapture, ScreenshotBatch
from .vision_intelligence import VisionIntelligence
from .reward_system import RewardSystem
from .user_demo_matcher import UserDemonstrationMatcher
from .training_pipeline import TrainingPipeline

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
agent = None
action_space = None
game_intelligence = None  # Smart game analysis engine (OCR + CV)
advanced_intelligence = None  # Advanced game intelligence layer (Phase 1 CV only)
hybrid_intelligence = None  # Hybrid intelligence (Phase 1 + 2 + 3)
learning_recorder = None  # Learning data recorder for building training datasets
observation_recorder = None  # NEW: High-performance user observation recorder
decision_recorder = None  # NEW: AI decision recorder
hp_capture = None  # NEW: High-performance 16 FPS capture system
dual_mode_controller = None  # NEW: Dual-mode controller for user observation and AI auto-play
vision_intelligence = None  # NEW: Vision AI for deep game understanding
reward_system = None  # NEW: Advanced reward calculation system
user_demo_matcher = None  # NEW: Smart user demonstration matching
training_pipeline = None  # NEW: Automated training pipeline
play_task: Optional[asyncio.Task] = None
is_playing = False
ai_active = False  # NEW: Controls when AI actually starts making actions
learning_mode = 'auto_play'  # 'auto_play' (AI executes actions) or 'user_guided' (AI observes only)
observation_url = None
observation_service_url = None
emulator_manager_url = None
orchestrator_url = None
http_client: Optional[httpx.AsyncClient] = None
db_manager = None

# Session context
current_session_id = None
current_game_id = None
current_game_version_id = None
current_package_name = None
current_device_mode = 'emulator'
current_device_ip = 'localhost'

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
    game_version_id: str = None  # Game version ID for learning data
    package_name: str
    enable_training: bool = True
    training_interval: int = 10
    learning_mode: str = "auto_play"  # auto_play (AI plays) or user_guided (user plays, AI observes)
    device_mode: str = "emulator"  # emulator or physical
    device_ip: str = "localhost"  # IP for physical device


class TrainingConfig(BaseModel):
    enabled: bool = True
    interval: int = 10


class SaveModelRequest(BaseModel):
    version: int = 1


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global action_space, observation_url, observation_service_url, emulator_manager_url, orchestrator_url, http_client, db_manager, learning_recorder, observation_recorder, decision_recorder, hp_capture
    
    # Startup
    logger.info("Starting AI Agent Service V2...")
    
    # Initialize database (if available)
    if DatabaseManager is not None:
        try:
            db_manager = DatabaseManager()
            await db_manager.connect()
            logger.info("Database connected")
            
            # Initialize learning recorder (legacy)
            learning_recorder = LearningRecorder(db_manager)
            logger.info("Learning recorder initialized")
            
            # Initialize NEW high-performance recorders
            observation_recorder = ObservationRecorder(db_manager)
            decision_recorder = DecisionRecorder(db_manager)
            logger.info("✅ High-performance observation & decision recorders initialized")
            
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Running without database support.")
            db_manager = None
            learning_recorder = None
            observation_recorder = None
            decision_recorder = None
    else:
        logger.warning("DatabaseManager not available. Running without database support.")
        db_manager = None
        learning_recorder = None
        observation_recorder = None
        decision_recorder = None
    
    # NOTE: action_space and intelligence systems are initialized per-session
    # with dynamically detected screen dimensions (see start_playing endpoint)
    logger.info("⚙️  Action space and intelligence systems will be initialized per session with detected screen dimensions")
    
    # Get service URLs
    observation_url = os.getenv("OBSERVATION_URL", "http://observation:8001")
    observation_service_url = observation_url  # Alias for clarity
    emulator_manager_url = os.getenv("EMULATOR_MANAGER_URL", "http://emulator-manager:8005")
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    
    # Create HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    # Start pre-loading LLaVA model in background
    try:
        from .llava_loader import start_preload
        await start_preload()
        logger.info("🔮 LLaVA model pre-loading started in background")
    except Exception as e:
        logger.debug(f"LLaVA pre-load not started: {e}")
    
    logger.info("🚀 AI Agent Service V2 ready (16 FPS High-Performance Mode)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Service V2...")
    await stop_playing()
    
    # Stop high-performance capture if running
    if hp_capture:
        await hp_capture.stop_capture()
    
    # Flush any pending learning data
    if learning_recorder:
        await learning_recorder.flush()
    
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

# Mount static files directory for serving HTML/CSS/JS
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
try:
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception as e:
    logger.debug(f"Could not mount static directory: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main visualization page"""
    html_path = static_dir / "vision_learning.html"
    if html_path.exists():
        return html_path.read_text()
    return """
    <html>
        <head><title>PlayMetric AI Agent</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: #e2e8f0;">
            <h1>🎮 PlayMetric AI Agent V2</h1>
            <p>Advanced RL agent with database-backed learning</p>
            <p><a href="/docs" style="color: #60a5fa;">API Documentation</a></p>
        </body>
    </html>
    """


async def play_loop():
    """Main gameplay loop with RL training"""
    global is_playing, agent, steps_since_training, training_enabled, training_interval
    global current_session_id, ai_active, current_screenshot_path, current_screenshot_count
    
    # Get action interval from environment (default 0.7s for speed, can override)
    action_interval = float(os.getenv("ACTION_INTERVAL", "0.7"))
    logger.info(f"Starting gameplay loop (interval: {action_interval}s - Optimized for fast gameplay)")
    
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
            vision_analysis = None
            
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
                
                # === NEW: VISION AI DEEP ANALYSIS ===
                if vision_intelligence:
                    try:
                        context = {
                            'game_id': current_game_id,
                            'session_id': current_session_id,
                            'last_action': last_action_params
                        }
                        vision_analysis = await vision_intelligence.analyze_game_screen(
                            screenshot_path=screenshot,
                            context=context
                        )
                        if vision_analysis:
                            logger.info(f"🔮 Vision AI: {vision_analysis.get('scene_type', 'unknown')} scene - "
                                       f"Recommended: {vision_analysis.get('recommended_action', {}).get('action', 'none')}")
                    except Exception as e:
                        logger.warning(f"Vision AI analysis failed: {e}")
                        vision_analysis = None
            
            # Load screenshot for RL agent
            if isinstance(agent, AdvancedRLAgent) and screenshot:
                screenshot_array = load_screenshot(screenshot)
                current_state = agent.preprocess_observation(screenshot_array)
            else:
                current_state = None
            
            # === NEW: ADVANCED REWARD CALCULATION ===
            if reward_system and last_state is not None:
                # Build before/after state for reward calculation
                before_state = {
                    'screenshot': last_action_params.get('screenshot') if last_action_params else None,
                    'ui_elements': last_action_params.get('ui_elements', []) if last_action_params else [],
                    'ocr_data': last_action_params.get('ocr_data', {}) if last_action_params else {}
                }
                after_state = {
                    'screenshot': screenshot,
                    'ui_elements': ui_elements,
                    'ocr_data': ocr_data,
                    'observation': observation
                }
                
                reward_breakdown = reward_system.calculate_reward(
                    before_state=before_state,
                    action=last_action,
                    after_state=after_state,
                    vision_analysis=vision_analysis,
                    ocr_data=ocr_data
                )
                
                reward = reward_breakdown['total_reward']
                logger.info(f"💎 Advanced Reward: {reward:.2f} (breakdown: {reward_breakdown['breakdown']})")
            elif game_intelligence:
                # Fallback to smart reward
                screen_changed = screenshot_comparison.get('changed_significantly', False)
                reward = game_intelligence.calculate_smart_reward(
                    observation, screen_changed, ocr_data
                )
            else:
                # Basic reward
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
            
            # === INTELLIGENT ACTION DECISION (Hybrid or Advanced) ===
            advanced_recommendation = None
            user_demo_recommendation = None
            
            # === NEW: CHECK USER DEMONSTRATIONS FIRST ===
            if user_demo_matcher and screenshot:
                try:
                    # Extract features from current screen
                    current_features = {
                        'ui_elements': ui_elements,
                        'ocr_text': ocr_data.get('text', ''),
                        'scene_type': vision_analysis.get('scene_type') if vision_analysis else 'unknown',
                        'screenshot_path': screenshot
                    }
                    
                    # Find best action from user demonstrations
                    demo_action = await user_demo_matcher.get_best_action_for_state(
                        current_screen_features=current_features,
                        game_id=current_game_id
                    )
                    
                    if demo_action and demo_action['confidence'] > 0.75:
                        user_demo_recommendation = {
                            'action': demo_action['action_type'],
                            'coordinates': demo_action.get('coordinates'),
                            'reasoning': f"Learned from user (confidence: {demo_action['confidence']:.2%}, "
                                        f"similarity: {demo_action['similarity']:.2%})",
                            'confidence': demo_action['confidence']
                        }
                        logger.info(f"🎓 Using learned user action: {demo_action['action_type']} "
                                   f"(confidence: {demo_action['confidence']:.2%})")
                except Exception as e:
                    logger.warning(f"User demo matcher failed: {e}")
            
            if hybrid_intelligence and current_screenshot_path:
                # Use Hybrid Intelligence (Phase 1 + 2 + 3)
                try:
                    advanced_recommendation = hybrid_intelligence.analyze_and_decide(
                        screenshot_path=current_screenshot_path,
                        ocr_data=ocr_data,
                        ui_elements=ui_elements,
                        game_state=None  # Will be extracted internally
                    )
                    
                    # Update RL after action (if enabled)
                    if hybrid_intelligence.rl_agent:
                        hybrid_intelligence.update_after_action({
                            'observation': observation,
                            'screen_changed': screenshot_comparison.get('changed_significantly', False)
                        })
                        
                except Exception as e:
                    logger.error(f"Hybrid intelligence error: {e}", exc_info=True)
                    
            elif advanced_intelligence and current_screenshot_path:
                # Use Advanced Intelligence (Phase 1 CV only)
                try:
                    advanced_recommendation = advanced_intelligence.analyze_and_decide(
                        current_screenshot_path,
                        ocr_data,
                        ui_elements
                    )
                except Exception as e:
                    logger.error(f"Advanced intelligence error: {e}", exc_info=True)
            
            # Fallback to basic smart recommendation if advanced fails
            smart_recommendation = None
            if not advanced_recommendation and not user_demo_recommendation and game_intelligence:
                screen_changed = screenshot_comparison.get('changed_significantly', False)
                smart_recommendation = game_intelligence.get_smart_action_recommendation(
                    ocr_data, ui_elements, screen_changed
                )
            
            # Decide action priority: User Demo > Vision AI > Hybrid/Advanced > Smart > RL agent
            if user_demo_recommendation:
                # Use learned user demonstration (HIGHEST PRIORITY)
                action_name = user_demo_recommendation['action']
                
                if action_name == 'tap' and user_demo_recommendation['coordinates']:
                    action = action_space.get_tap_at(
                        user_demo_recommendation['coordinates'][0],
                        user_demo_recommendation['coordinates'][1]
                    )
                elif action_name == 'swipe_up':
                    action = action_space.get_swipe_up()
                elif action_name == 'swipe_down':
                    action = action_space.get_swipe_down()
                elif action_name == 'swipe_left':
                    action = action_space.get_swipe_left()
                elif action_name == 'swipe_right':
                    action = action_space.get_swipe_right()
                elif action_name == 'back':
                    action = action_space.get_back_action()
                else:
                    action = action_space.get_random_tap()
                
                await broadcast_ai_thinking({
                    "type": "user_demo_decision",
                    "action": action.action_type.value,
                    "position": {"x": action.x, "y": action.y},
                    "reasoning": user_demo_recommendation['reasoning'],
                    "confidence": user_demo_recommendation['confidence'],
                    "source": "learned_from_user",
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
                
            elif vision_analysis and vision_analysis.get('recommended_action'):
                # Use Vision AI recommendation (SECOND PRIORITY)
                vision_action = vision_analysis['recommended_action']
                action_name = vision_action.get('action')
                
                if action_name == 'tap' and vision_action.get('coordinates'):
                    action = action_space.get_tap_at(
                        vision_action['coordinates'][0],
                        vision_action['coordinates'][1]
                    )
                elif action_name == 'swipe_up':
                    action = action_space.get_swipe_up()
                elif action_name == 'swipe_down':
                    action = action_space.get_swipe_down()
                elif action_name == 'swipe_left':
                    action = action_space.get_swipe_left()
                elif action_name == 'swipe_right':
                    action = action_space.get_swipe_right()
                elif action_name == 'back':
                    action = action_space.get_back_action()
                else:
                    action = action_space.get_random_tap()
                
                await broadcast_ai_thinking({
                    "type": "vision_ai_decision",
                    "action": action.action_type.value,
                    "position": {"x": action.x, "y": action.y},
                    "reasoning": vision_action.get('reasoning', 'Vision AI recommendation'),
                    "confidence": vision_action.get('confidence', 0.7),
                    "scene_type": vision_analysis.get('scene_type'),
                    "game_state": vision_analysis.get('game_state'),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
                
            elif advanced_recommendation:
                # Use advanced intelligence (Phase 1 - Smart game-specific logic)
                action_name = advanced_recommendation['action']
                
                if action_name == 'tap' and advanced_recommendation['coordinates']:
                    action = action_space.get_tap_at(
                        advanced_recommendation['coordinates'][0],
                        advanced_recommendation['coordinates'][1]
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
                
                reasoning = advanced_recommendation['reasoning']
                
                # Add OCR text to reasoning if available
                ocr_text = ocr_data.get('text', '')
                if ocr_text:
                    reasoning = f"{reasoning}\n\n📝 OCR detected text: {ocr_text[:200]}"
                
                await broadcast_ai_thinking({
                    "type": "advanced_decision",
                    "action": action.action_type.value,
                    "position": {"x": action.x, "y": action.y},
                    "reasoning": reasoning,
                    "ocr_text": ocr_text[:500] if ocr_text else None,
                    "ocr_detected": bool(ocr_data.get('buttons_detected')),
                    "ui_elements_detected": len(ui_elements),
                    "screen_changed": screenshot_comparison.get('changed_significantly', False),
                    "screen_type": advanced_recommendation.get('screen_type', 'unknown'),
                    "level": advanced_recommendation.get('level'),
                    "progress": advanced_recommendation.get('progress', 'unknown'),
                    "confidence": advanced_recommendation.get('confidence', 0.5),
                    "stuck": game_intelligence.is_stuck() if game_intelligence else False,
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                })
                
            elif smart_recommendation:
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
            
            # === EXECUTE ACTION (only in AI mode) ===
            screenshot_before = screenshot  # Store screenshot before action
            
            # Store action params for next iteration's reward calculation
            action_params_for_next = {
                'screenshot': screenshot_before,
                'ui_elements': ui_elements,
                'ocr_data': ocr_data,
                'action_type': action.action_type.value,
                'coordinates': (action.x, action.y)
            }
            
            if learning_mode == 'auto_play':
                # AI GAMEPLAY MODE: Execute action
                logger.info(f"🤖 [AI MODE] Executing action: {action.action_type.value} at ({action.x}, {action.y})")
                await execute_action(action)
                
                # Record AI gameplay to learning dataset
                if learning_recorder and current_session_id and current_game_id and current_game_version_id:
                    await learning_recorder.record_action(
                        session_id=current_session_id,
                        game_id=current_game_id,
                        game_version_id=current_game_version_id,
                        action_type=action.action_type.value,
                        action_params={
                            'x': action.x,
                            'y': action.y,
                            'x2': getattr(action, 'x2', None),
                            'y2': getattr(action, 'y2', None),
                            'duration': getattr(action, 'duration', None)
                        },
                        screenshot_before=screenshot_before,
                        screenshot_after=None,  # Will capture after wait
                        is_user_action=False,  # AI action
                        learning_mode='auto_play',
                        game_state={'ocr': ocr_data, 'ui_elements_count': len(ui_elements)},
                        level_identifier=observation.get('level', 'unknown'),
                        reward=reward,
                        success=True,
                        led_to_progress=screen_changed,
                        device_type=current_device_mode,
                        agent_mode=agent.__class__.__name__.lower(),
                        ui_elements=ui_elements,
                        detected_text=ocr_data.get('text'),
                        metadata={'episode_reward': episode_reward}
                    )
            else:
                # USER GAMEPLAY MODE: Don't execute, just observe
                logger.info(f"👤 [USER MODE] Observing... (AI would suggest: {action.action_type.value} at ({action.x}, {action.y}))")
                logger.info(f"📝 Waiting for user to play. AI is learning from observations...")
                
                # Check for user taps from observation service
                try:
                    taps_response = await http_client.get(f"{observation_url}/user-input/taps?limit=10")
                    if taps_response.status_code == 200:
                        taps_data = taps_response.json()
                        recent_taps = taps_data.get('taps', [])
                        
                        if recent_taps and learning_recorder and current_session_id and current_game_id and current_game_version_id:
                            # Record the most recent user tap
                            last_tap = recent_taps[-1]
                            tap_x = last_tap.get('x')
                            tap_y = last_tap.get('y')
                            
                            if tap_x and tap_y:
                                logger.info(f"✅ Recording user tap: ({tap_x}, {tap_y})")
                                
                                await learning_recorder.record_action(
                                    session_id=current_session_id,
                                    game_id=current_game_id,
                                    game_version_id=current_game_version_id,
                                    action_type='tap',
                                    action_params={'x': tap_x, 'y': tap_y},
                                    screenshot_before=screenshot_before,
                                    screenshot_after=None,
                                    is_user_action=True,  # USER action
                                    learning_mode='user_guided',
                                    game_state={'ocr': ocr_data, 'ui_elements_count': len(ui_elements)},
                                    level_identifier=observation.get('level', 'unknown'),
                                    reward=reward,
                                    success=True,
                                    led_to_progress=screen_changed,
                                    device_type=current_device_mode,
                                    agent_mode='user',
                                    ui_elements=ui_elements,
                                    detected_text=ocr_data.get('text'),
                                    metadata={'observation_mode': True}
                                )
                                
                                # === NEW: Store in user demonstration matcher ===
                                if user_demo_matcher and screenshot_before:
                                    try:
                                        await user_demo_matcher.store_action_outcome(
                                            game_id=current_game_id,
                                            session_id=current_session_id,
                                            screen_features={
                                                'ui_elements': ui_elements,
                                                'ocr_text': ocr_data.get('text', ''),
                                                'scene_type': vision_analysis.get('scene_type') if vision_analysis else 'unknown',
                                                'screenshot_path': screenshot_before
                                            },
                                            action_type='tap',
                                            action_params={'x': tap_x, 'y': tap_y},
                                            outcome_positive=screen_changed,
                                            reward=reward
                                        )
                                        logger.info("📚 Stored user action in demonstration matcher")
                                    except Exception as e:
                                        logger.warning(f"Failed to store user demo: {e}")
                except Exception as e:
                    logger.debug(f"Could not fetch user taps: {e}")
            
            logger.info(f"⏳ Waiting {action_interval} seconds before next analysis...")
            
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
            last_action_params = action_params_for_next  # Use enriched params with screenshot, OCR, UI data
            
            # ADAPTIVE TIMING: Wait less if screen changed (faster), more if no change
            screen_changed = screenshot_comparison.get('changed_significantly', False)
            if screen_changed:
                # Screen changed - short wait (UI is loading/responding)
                await asyncio.sleep(action_interval * 0.6)  # 60% of normal interval
                logger.debug("⚡ Fast wait (screen changed)")
            else:
                # No change - normal wait
                await asyncio.sleep(action_interval)
                logger.debug("⏱️ Normal wait (no screen change)")
            
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
        
        # Save hybrid intelligence RL model
        if hybrid_intelligence and hybrid_intelligence.rl_agent:
            try:
                hybrid_intelligence.save_rl_model()
                hybrid_intelligence.end_session({'total_reward': 0})  # Placeholder
                logger.info("Saved hybrid intelligence RL model")
            except Exception as e:
                logger.error(f"Error saving hybrid RL model: {e}")
        
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


async def detect_screen_dimensions():
    """Detect actual screen dimensions from connected device"""
    try:
        # Try emulator-manager first
        response = await http_client.get(f"{emulator_manager_url}/device/screen-size", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            width = data.get('width', 1080)
            height = data.get('height', 1920)
            logger.info(f"📱 Detected screen dimensions from emulator-manager: {width}x{height}")
            return width, height
    except Exception as e:
        logger.warning(f"Could not get screen size from emulator-manager: {e}")
    
    # Fallback: Use environment variables
    width = int(os.getenv("SCREEN_WIDTH", "1080"))
    height = int(os.getenv("SCREEN_HEIGHT", "1920"))
    logger.warning(f"⚠️  Using default screen dimensions from .env: {width}x{height}")
    return width, height


@app.post("/play/start")
async def start_playing(request: StartPlayingRequest):
    """Start automated gameplay with advanced RL"""
    global agent, is_playing, play_task, current_session_id, current_game_id, current_game_version_id
    global current_package_name, training_enabled, training_interval, game_intelligence, ai_active
    global action_space, advanced_intelligence, hybrid_intelligence, learning_mode
    global current_device_mode, current_device_ip, dual_mode_controller
    global vision_intelligence, reward_system, user_demo_matcher, training_pipeline
    
    if is_playing:
        return {"message": "Already playing", "agent": agent.__class__.__name__}
    
    # Store learning configuration
    learning_mode = request.learning_mode
    current_device_mode = request.device_mode
    current_device_ip = request.device_ip
    
    logger.info(f"🎮 Starting session with learning_mode={learning_mode}, device_mode={current_device_mode}")
    
    # === STEP 1: DETECT SCREEN DIMENSIONS ===
    screen_width, screen_height = await detect_screen_dimensions()
    logger.info(f"🖥️  Session screen dimensions: {screen_width}x{screen_height}")
    
    # === STEP 2: REINITIALIZE ACTION SPACE WITH CORRECT DIMENSIONS ===
    action_space = ActionSpace(screen_width=screen_width, screen_height=screen_height)
    logger.info(f"✅ Action space reinitialized for {screen_width}x{screen_height}")
    
    # === STEP 3: REINITIALIZE INTELLIGENCE SYSTEMS WITH CORRECT DIMENSIONS ===
    vision_ai_enabled = os.getenv("VISION_AI_ENABLED", "false").lower() == "true"
    rl_enabled = os.getenv("RL_ENABLED", "true").lower() == "true"
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if vision_ai_enabled or rl_enabled:
        # Reinitialize Hybrid Intelligence with detected dimensions
        hybrid_intelligence = HybridGameIntelligence(
            screen_dimensions=(screen_width, screen_height),
            gemini_api_key=gemini_api_key,
            rl_model_path=os.getenv("RL_MODEL_PATH", "/app/data/rl_model.pkl"),
            enable_vision_ai=vision_ai_enabled,
            enable_rl=rl_enabled
        )
        logger.info(f"🚀 Hybrid Intelligence reinitialized for {screen_width}x{screen_height}")
    else:
        # Reinitialize Advanced Intelligence with detected dimensions
        advanced_intelligence = AdvancedGameIntelligence(
            screen_dimensions=(screen_width, screen_height)
        )
        logger.info(f"🧠 Advanced Intelligence reinitialized for {screen_width}x{screen_height}")
    
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
    current_game_version_id = request.game_version_id
    current_package_name = request.package_name
    training_enabled = request.enable_training
    training_interval = request.training_interval
    
    # Initialize Dual-Mode Controller for user observation and AI auto-play
    from .dual_mode_controller import DualModeController
    dual_mode_controller = DualModeController(
        db_manager=db_manager,
        emulator_manager_url=emulator_manager_url,
        observation_service_url=observation_service_url,
        http_client=http_client
    )
    logger.info("✅ Dual-Mode Controller initialized")
    
    # Initialize Vision Intelligence (LLaVA/GPT-4V/Gemini)
    vision_intelligence = VisionIntelligence(model_type="auto")
    logger.info("✅ Vision Intelligence initialized")
    
    # Initialize Advanced Reward System
    reward_system = RewardSystem()
    logger.info("✅ Advanced Reward System initialized")
    
    # Initialize User Demonstration Matcher
    user_demo_matcher = UserDemonstrationMatcher(db_manager=db_manager)
    logger.info("✅ User Demonstration Matcher initialized")
    
    # Initialize Automated Training Pipeline
    training_pipeline = TrainingPipeline(
        db_manager=db_manager,
        rl_agent=agent if request.agent_mode == "advanced_rl" else None,
        vision_intelligence=vision_intelligence,
        reward_system=reward_system
    )
    # Start continuous training loop
    await training_pipeline.start_training_loop()
    logger.info("✅ Automated Training Pipeline started")
    
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
    
    # === LEARNING MODE LOGIC ===
    if learning_mode == 'user_guided':
        logger.info("👤 USER GAMEPLAY MODE: AI will observe and learn from user actions")
        logger.info("📝 Recording user gameplay to build training dataset...")
        
        # Start user input monitoring in observation service
        try:
            device_id = f"{current_device_ip}:5555" if current_device_mode == 'physical' else None
            await http_client.post(
                f"{observation_url}/user-input/start",
                json={"device_id": device_id}
            )
            logger.info("✅ User input monitoring started in observation service")
        except Exception as e:
            logger.error(f"❌ Failed to start user input monitoring: {e}")
        
        # In user gameplay mode, agent is still created for observation/analysis
        # but actions will not be executed
    else:
        logger.info("🤖 AI GAMEPLAY MODE: AI will play and learn from its own actions")
        
        # Make sure user monitoring is stopped in AI mode
        try:
            await http_client.post(f"{observation_url}/user-input/stop")
        except:
            pass
    
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
    """
    Activate AI Auto-Play Mode - AI plays the game using learned data
    
    In this mode:
    - AI controls the game
    - Captures screenshots at 16 FPS (62.5ms interval)
    - Analyzes batch of 16 frames every second
    - Makes collective decision based on:
      - User demonstrations (from observations)
      - Own past successful actions
      - Exploration of unknown scenarios
    - Stores decision process to database
    """
    global ai_active, learning_mode, is_playing, dual_mode_controller, current_session_id, current_game_id
    
    if not dual_mode_controller:
        return {
            "error": "Dual mode controller not initialized",
            "message": "System not ready. Please try again."
        }
    
    learning_mode = 'auto_play'
    ai_active = True
    is_playing = True
    
    logger.info("🤖 AI AUTO-PLAY MODE: AI will play using learned data at 16 FPS")
    logger.info("📊 High-performance capture and batch analysis started")
    
    try:
        # Start AI auto-play mode with DualModeController
        await dual_mode_controller.start_ai_autoplay_mode(
            session_id=current_session_id,
            game_id=current_game_id
        )
        logger.info("✅ AI auto-play mode started with 16 FPS capture and batch analysis")
    except Exception as e:
        logger.error(f"Failed to start AI auto-play mode: {e}")
        return {
            "error": str(e),
            "message": "Failed to start AI auto-play mode"
        }
    
    return {
        "message": "AI auto-play mode activated",
        "mode": "auto_play",
        "ai_active": True,
        "learning_enabled": True,
        "session_id": current_session_id,
        "fps": 16,
        "info": "AI is playing at 16 FPS, analyzing batches of frames, and making collective decisions."
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


@app.post("/play/observe")
async def start_user_observation(request: dict):
    """
    Start User Gameplay Mode - AI observes and learns from user actions at 16 FPS
    
    In this mode:
    - AI does NOT control the game
    - User plays manually
    - AI captures screenshots at 16 FPS (62.5ms interval)
    - AI analyzes user actions with full context (UI elements, OCR, visual features)
    - AI stores observations to database for future learning
    - This data will be used when AI plays in auto_play mode
    """
    global ai_active, learning_mode, is_playing, dual_mode_controller, current_session_id, current_game_id
    
    if not dual_mode_controller:
        return {
            "error": "Dual mode controller not initialized",
            "message": "System not ready. Please try again."
        }
    
    learning_mode = 'user_guided'
    ai_active = False  # AI doesn't play, only observes
    is_playing = True
    
    logger.info("👤 USER GAMEPLAY MODE: AI will observe and learn from user actions at 16 FPS")
    logger.info("📊 High-performance capture and analysis started")
    
    try:
        # Start user observation mode with DualModeController
        await dual_mode_controller.start_user_observation_mode(
            session_id=current_session_id,
            game_id=current_game_id
        )
        logger.info("✅ User observation mode started with 16 FPS capture")
    except Exception as e:
        logger.error(f"Failed to start user observation mode: {e}")
        return {
            "error": str(e),
            "message": "Failed to start observation mode"
        }
    
    return {
        "message": "User gameplay observation started",
        "mode": "user_guided",
        "ai_active": False,
        "learning_enabled": True,
        "session_id": current_session_id,
        "fps": 16,
        "info": "AI is observing your gameplay at 16 FPS and learning from your actions. Data will be stored for future AI sessions."
    }


@app.get("/play/user-observations")
async def get_user_observations(limit: int = 20):
    """
    Get AI's analysis of user actions from database
    
    Returns observations showing:
    - Screen state before action (UI elements, OCR text, visual features)
    - User action (tap/swipe with coordinates)
    - Screen state after action
    - AI's analysis of what happened
    - Outcome (success/failure, progress made)
    """
    global current_session_id, observation_recorder
    
    if not current_session_id or not observation_recorder:
        return {
            "observations": [],
            "total": 0,
            "message": "No active session or recorder not available"
        }
    
    try:
        # Fetch from database
        query = """
            SELECT 
                id, session_id, timestamp,
                screen_before, user_action, screen_after,
                ai_analysis, outcome, led_to_progress,
                metadata
            FROM user_observations
            WHERE session_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """
        
        rows = await db_manager.pool.fetch(query, current_session_id, limit)
        
        observations = []
        for row in rows:
            observations.append({
                "id": str(row['id']),
                "timestamp": row['timestamp'].isoformat(),
                "screen_before": row['screen_before'],
                "user_action": row['user_action'],
                "screen_after": row['screen_after'],
                "ai_analysis": row['ai_analysis'],
                "outcome": row['outcome'],
                "led_to_progress": row['led_to_progress'],
                "metadata": row['metadata']
            })
        
        return {
            "observations": observations,
            "total": len(observations),
            "session_id": current_session_id,
            "learning_mode": "user_guided"
        }
        
    except Exception as e:
        logger.error(f"Failed to get user observations: {e}")
        return {
            "observations": [],
            "total": 0,
            "error": str(e)
        }


@app.get("/play/ai-decisions")
async def get_ai_decisions(limit: int = 20):
    """
    Get AI's decision-making process from database
    
    Returns decisions showing:
    - Screen state analysis (batch of 16 frames)
    - Decision reasoning (why AI chose this action)
    - Action taken
    - Confidence level
    - Result
    - Learning source (user demo / own experience / exploration)
    """
    global current_session_id, decision_recorder
    
    if not current_session_id or not decision_recorder:
        return {
            "decisions": [],
            "total": 0,
            "message": "No active session or recorder not available"
        }
    
    try:
        # Fetch from database
        query = """
            SELECT 
                id, session_id, timestamp,
                screen_state, decision_reasoning, action_taken,
                confidence, result, learned_from,
                observation_refs, metadata
            FROM ai_decisions
            WHERE session_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """
        
        rows = await db_manager.pool.fetch(query, current_session_id, limit)
        
        decisions = []
        for row in rows:
            decisions.append({
                "id": str(row['id']),
                "timestamp": row['timestamp'].isoformat(),
                "screen_state": row['screen_state'],
                "decision_reasoning": row['decision_reasoning'],
                "action_taken": row['action_taken'],
                "confidence": float(row['confidence']),
                "result": row['result'],
                "learned_from": row['learned_from'],
                "observation_refs": [str(ref) for ref in (row['observation_refs'] or [])],
                "metadata": row['metadata']
            })
        
        return {
            "decisions": decisions,
            "total": len(decisions),
            "session_id": current_session_id,
            "learning_mode": "auto_play"
        }
        
    except Exception as e:
        logger.error(f"Failed to get AI decisions: {e}")
        return {
            "decisions": [],
            "total": 0,
            "error": str(e)
        }


@app.post("/play/stop")
async def stop_playing_endpoint():
    """Stop automated gameplay"""
    global ai_active, training_pipeline
    ai_active = False
    
    # Stop training pipeline if running
    if training_pipeline:
        await training_pipeline.stop_training_loop()
    
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
    
    # Get user observation status from observation service
    observation_status = {}
    if learning_mode == 'user_guided':
        try:
            response = await http_client.get(f"{observation_url}/user-input/status", timeout=2.0)
            if response.status_code == 200:
                observation_status = response.json()
        except Exception as e:
            logger.debug(f"Could not get observation status: {e}")
    
    return {
        "playing": is_playing,
        "ai_active": ai_active,
        "learning_mode": learning_mode,
        "agent": agent.__class__.__name__ if agent else None,
        "session_id": current_session_id,
        "game_id": current_game_id,
        "statistics": stats,
        "observation": observation_status if learning_mode == 'user_guided' else None
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


@app.get("/vision/llava/status")
async def get_llava_status():
    """Get LLaVA model loading status"""
    try:
        from .llava_loader import llava_loader
        status = llava_loader.get_status()
        
        # Add model info if loaded
        if status['loaded']:
            import torch
            status['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
            if torch.cuda.is_available():
                status['gpu_name'] = torch.cuda.get_device_name(0)
        
        return status
    except Exception as e:
        return {"error": str(e)}


@app.get("/vision/learned-data")
async def get_vision_learned_data(game_id: Optional[str] = None, limit: int = 100):
    """
    Get visual data that has been learned from user demonstrations
    Returns screenshots + actions for visualization
    """
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        query = """
            SELECT 
                la.id, la.timestamp, la.game_id, la.session_id,
                la.action_type, la.action_params,
                la.screenshot_before, la.screenshot_after,
                la.is_user_action, la.reward, la.success, la.led_to_progress,
                la.ui_elements, la.detected_text,
                la.metadata
            FROM learning_actions la
            WHERE la.is_user_action = true
        """
        
        params = []
        if game_id:
            query += " AND la.game_id = $1"
            params.append(game_id)
        
        query += " ORDER BY la.timestamp DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        rows = await db_manager.execute(query, *params)
        
        learned_data = []
        for row in rows:
            learned_data.append({
                "id": str(row['id']),
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "game_id": row['game_id'],
                "session_id": row['session_id'],
                "action": {
                    "type": row['action_type'],
                    "params": row['action_params']
                },
                "screenshots": {
                    "before": row['screenshot_before'],
                    "after": row['screenshot_after']
                },
                "outcome": {
                    "reward": float(row['reward']) if row['reward'] else 0.0,
                    "success": row['success'],
                    "led_to_progress": row['led_to_progress']
                },
                "analysis": {
                    "ui_elements": row['ui_elements'] or [],
                    "detected_text": row['detected_text'] or ""
                },
                "metadata": row['metadata'] or {}
            })
        
        return {
            "total": len(learned_data),
            "game_id": game_id,
            "demonstrations": learned_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get learned data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vision/learning-progress")
async def get_learning_progress(game_id: Optional[str] = None):
    """
    Get learning progress statistics and visualization data
    """
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Get user demonstrations count over time
        query = """
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as count,
                AVG(reward) as avg_reward,
                COUNT(CASE WHEN led_to_progress = true THEN 1 END) as successful_count
            FROM learning_actions
            WHERE is_user_action = true
        """
        
        params = []
        if game_id:
            query += " AND game_id = $1"
            params.append(game_id)
        
        query += " GROUP BY hour ORDER BY hour DESC LIMIT 24"
        
        rows = await db_manager.execute(query, *params)
        
        timeline = []
        for row in rows:
            timeline.append({
                "hour": row['hour'].isoformat() if row['hour'] else None,
                "demonstrations": row['count'],
                "avg_reward": float(row['avg_reward']) if row['avg_reward'] else 0.0,
                "successful": row['successful_count'],
                "success_rate": row['successful_count'] / row['count'] if row['count'] > 0 else 0.0
            })
        
        # Get action distribution
        action_query = """
            SELECT 
                action_type,
                COUNT(*) as count,
                AVG(reward) as avg_reward
            FROM learning_actions
            WHERE is_user_action = true
        """
        
        action_params = []
        if game_id:
            action_query += " AND game_id = $1"
            action_params.append(game_id)
        
        action_query += " GROUP BY action_type ORDER BY count DESC"
        
        action_rows = await db_manager.execute(action_query, *action_params)
        
        actions = []
        for row in action_rows:
            actions.append({
                "type": row['action_type'],
                "count": row['count'],
                "avg_reward": float(row['avg_reward']) if row['avg_reward'] else 0.0
            })
        
        return {
            "game_id": game_id,
            "timeline": timeline,
            "action_distribution": actions,
            "total_demonstrations": sum(t['demonstrations'] for t in timeline)
        }
        
    except Exception as e:
        logger.error(f"Failed to get learning progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/stats")
async def get_training_stats():
    """Get automated training pipeline statistics"""
    if not training_pipeline:
        return {"error": "Training pipeline not initialized"}
    
    try:
        stats = training_pipeline.get_training_stats()
        
        # Add vision intelligence stats if available
        if vision_intelligence:
            stats['vision_intelligence'] = {
                'model_type': vision_intelligence.model_type,
                'available': vision_intelligence.vision_available
            }
        
        # Add reward system stats
        if reward_system:
            stats['reward_system'] = {
                'weights': reward_system.weights
            }
        
        # Add demo matcher stats
        if user_demo_matcher:
            stats['user_demo_matcher'] = {
                'cache_size': len(user_demo_matcher.demo_cache) if hasattr(user_demo_matcher, 'demo_cache') else 0
            }
        
        # Add LLaVA status
        try:
            from .llava_loader import llava_loader
            stats['llava'] = llava_loader.get_status()
        except:
            pass
        
        return stats
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
    """Get detailed agent statistics including hybrid intelligence"""
    # Hybrid intelligence stats (if enabled)
    if hybrid_intelligence:
        try:
            return {
                'agent_type': 'HybridIntelligence',
                'hybrid_stats': hybrid_intelligence.get_statistics(),
                'phases': {
                    'phase_1_cv': 'enabled',
                    'phase_2_vision_ai': 'enabled' if hybrid_intelligence.vision_ai and hybrid_intelligence.vision_ai.enabled else 'disabled',
                    'phase_3_rl': 'enabled' if hybrid_intelligence.rl_agent else 'disabled'
                },
                'training_enabled': training_enabled,
                'training_interval': training_interval
            }
        except Exception as e:
            logger.error(f"Error getting hybrid stats: {e}")
    
    # Legacy agent stats
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


# ============================================================================
# LEARNING DATA ENDPOINTS
# ============================================================================

@app.get("/learning/data")
async def get_learning_data(
    game_id: Optional[str] = None,
    game_version_id: Optional[str] = None,
    level_identifier: Optional[str] = None,
    is_user_action: Optional[bool] = None,
    learning_mode: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Retrieve learning data for AI training
    
    Filter by game, version, level, action type (user/AI), learning mode
    """
    if not learning_recorder:
        raise HTTPException(status_code=503, detail="Learning recorder not available")
    
    data = await learning_recorder.get_learning_data(
        game_id=game_id,
        game_version_id=game_version_id,
        level_identifier=level_identifier,
        is_user_action=is_user_action,
        learning_mode=learning_mode,
        limit=limit,
        offset=offset
    )
    
    return {
        "data": data,
        "count": len(data),
        "filters": {
            "game_id": game_id,
            "game_version_id": game_version_id,
            "level_identifier": level_identifier,
            "is_user_action": is_user_action,
            "learning_mode": learning_mode
        },
        "pagination": {
            "limit": limit,
            "offset": offset
        }
    }


@app.get("/learning/statistics")
async def get_learning_statistics(
    game_id: Optional[str] = None,
    game_version_id: Optional[str] = None
):
    """Get statistics about collected learning data"""
    if not learning_recorder:
        raise HTTPException(status_code=503, detail="Learning recorder not available")
    
    stats = await learning_recorder.get_statistics(
        game_id=game_id,
        game_version_id=game_version_id
    )
    
    return {
        "statistics": stats,
        "filters": {
            "game_id": game_id,
            "game_version_id": game_version_id
        }
    }


@app.post("/learning/flush")
async def flush_learning_data():
    """Manually flush buffered learning data to database"""
    if not learning_recorder:
        raise HTTPException(status_code=503, detail="Learning recorder not available")
    
    await learning_recorder.flush()
    
    return {"message": "Learning data flushed successfully"}


if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
