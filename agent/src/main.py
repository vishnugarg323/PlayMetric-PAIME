"""
Agent Service - Main API for AI agent control
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import uvicorn

from .actions import ActionSpace, ActionType
from .agents.random_agent import RandomAgent
from .agents.heuristic_agent import HeuristicAgent
from .agents.rl_agent import RLAgent

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
agent = None
action_space = None
play_task: Optional[asyncio.Task] = None
is_playing = False
observation_url = None
http_client: Optional[httpx.AsyncClient] = None


# Pydantic models
class StartPlayingRequest(BaseModel):
    agent_mode: str = "heuristic"  # random, heuristic, rl
    session_id: str = "default"
    package_name: Optional[str] = None


class ActionIntervalRequest(BaseModel):
    interval: float


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global action_space, observation_url, http_client
    
    # Startup
    logger.info("Starting AI Agent Service...")
    
    # Initialize action space
    screen_width = int(os.getenv("SCREEN_WIDTH", "1080"))
    screen_height = int(os.getenv("SCREEN_HEIGHT", "1920"))
    action_space = ActionSpace(screen_width=screen_width, screen_height=screen_height)
    
    # Get observation service URL
    observation_url = os.getenv("OBSERVATION_URL", "http://observation:8001")
    
    # Create HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    logger.info("AI Agent Service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Service...")
    await stop_playing()
    if http_client:
        await http_client.aclose()


app = FastAPI(
    title="PlayMetric AI Agent",
    description="AI/RL agent for automated game playing",
    version="1.0.0",
    lifespan=lifespan
)


async def play_loop():
    """Main gameplay loop"""
    global is_playing, agent
    
    action_interval = float(os.getenv("ACTION_INTERVAL", "1.5"))
    logger.info(f"Starting gameplay loop (interval: {action_interval}s)")
    
    while is_playing:
        try:
            # Get current observation
            observation = await get_observation()
            
            # Agent decides action
            action = agent.decide_action(observation)
            
            # Execute action
            await execute_action(action)
            
            # Wait before next action
            await asyncio.sleep(action_interval)
            
        except Exception as e:
            logger.error(f"Error in play loop: {e}")
            await asyncio.sleep(5)


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
            'action_count': agent.action_count if agent else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting observation: {e}")
        return {'screenshot': None, 'ui_elements': []}


async def execute_action(action):
    """Execute action via observation service"""
    try:
        if action.action_type == ActionType.TAP:
            await http_client.post(
                f"{observation_url}/action/tap",
                json={"x": action.x, "y": action.y}
            )
            
        elif action.action_type in [ActionType.SWIPE_UP, ActionType.SWIPE_DOWN, 
                                     ActionType.SWIPE_LEFT, ActionType.SWIPE_RIGHT]:
            await http_client.post(
                f"{observation_url}/action/swipe",
                json={
                    "x1": action.x,
                    "y1": action.y,
                    "x2": action.x2,
                    "y2": action.y2,
                    "duration": action.duration
                }
            )
            
        elif action.action_type == ActionType.BACK:
            await http_client.post(
                f"{observation_url}/action/key",
                json={"keycode": "BACK"}
            )
            
        elif action.action_type == ActionType.WAIT:
            # Just wait, no action needed
            pass
            
        logger.debug(f"Executed action: {action.action_type.value}")
        
    except Exception as e:
        logger.error(f"Error executing action: {e}")


async def stop_playing():
    """Stop the gameplay loop"""
    global is_playing, play_task
    
    if is_playing:
        is_playing = False
        if play_task:
            play_task.cancel()
            try:
                await play_task
            except asyncio.CancelledError:
                pass
        logger.info("Gameplay stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "playing": is_playing,
        "agent_type": agent.__class__.__name__ if agent else None,
        "action_count": agent.action_count if agent else 0
    }


@app.post("/play/start")
async def start_playing(request: StartPlayingRequest):
    """Start automated gameplay"""
    global agent, is_playing, play_task
    
    if is_playing:
        return {"message": "Already playing", "agent": agent.__class__.__name__}
    
    # Create agent based on mode
    config = {
        'model_path': os.getenv('RL_MODEL_PATH', '/data/models/dqn_model.zip'),
        'learning_rate': float(os.getenv('RL_LEARNING_RATE', '0.0003')),
        'exploration_rate': float(os.getenv('RL_EXPLORATION_RATE', '0.1'))
    }
    
    if request.agent_mode == "random":
        agent = RandomAgent(action_space, config)
    elif request.agent_mode == "rl":
        agent = RLAgent(action_space, config)
    else:
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
        "session_id": request.session_id
    }


@app.post("/play/stop")
async def stop_playing_endpoint():
    """Stop automated gameplay"""
    await stop_playing()
    
    # Get final statistics
    stats = agent.get_statistics() if agent else {}
    
    return {
        "message": "Gameplay stopped",
        "statistics": stats
    }


@app.get("/play/status")
async def play_status():
    """Get gameplay status"""
    return {
        "playing": is_playing,
        "agent": agent.__class__.__name__ if agent else None,
        "statistics": agent.get_statistics() if agent else {}
    }


@app.get("/agent/statistics")
async def get_agent_statistics():
    """Get agent statistics"""
    if not agent:
        raise HTTPException(status_code=404, detail="No active agent")
    
    return agent.get_statistics()


if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
