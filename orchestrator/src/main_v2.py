"""
Orchestrator API V2 - Main coordinator with Multi-Session & WebSocket support
"""
import os
import asyncio
import sys
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import httpx
import uvicorn

sys.path.append('/app/shared')
from database import DatabaseManager
from src.multi_session import get_orchestrator, SessionPriority
from src.websocket_manager import get_websocket_manager
from src.version_manager import VersionTracker

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_manager: Optional[DatabaseManager] = None
ws_manager = None
multi_session_orchestrator = None
version_tracker = None
http_client: Optional[httpx.AsyncClient] = None

# Service URLs
OBSERVATION_URL = os.getenv("OBSERVATION_URL", "http://observation:8001")
CRASH_DETECTOR_URL = os.getenv("CRASH_DETECTOR_URL", "http://crash-detector:8002")
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://analytics:8003")
AGENT_URL = os.getenv("AGENT_URL", "http://agent:8004")


# Pydantic models
class CreateGameRequest(BaseModel):
    display_name: str
    package_name: str
    genre: str
    metadata: Optional[Dict] = None


class CreateSessionRequest(BaseModel):
    game_id: str
    version_id: str
    agent_mode: str = "advanced_rl"
    config: Optional[Dict] = None
    priority: str = "normal"  # low, normal, high, urgent


class StartSessionRequest(BaseModel):
    session_id: str


class UpdateBugRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_manager, ws_manager, multi_session_orchestrator, http_client, version_tracker
    
    # Startup
    logger.info("Starting Orchestrator Service V2...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.connect()
    logger.info("Database connected")
    
    # Initialize WebSocket manager
    ws_manager = get_websocket_manager()
    logger.info("WebSocket manager initialized")
    
    # Initialize multi-session orchestrator
    multi_session_orchestrator = await get_orchestrator(db_manager)
    logger.info("Multi-session orchestrator started")
    
    # Initialize version tracker
    version_tracker = VersionTracker(db_manager)
    logger.info("Version tracker initialized")
    
    # HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    logger.info("Orchestrator Service V2 ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Orchestrator Service V2...")
    
    if multi_session_orchestrator:
        await multi_session_orchestrator.stop()
    
    if http_client:
        await http_client.aclose()
    
    if db_manager:
        await db_manager.disconnect()


app = FastAPI(
    title="PlayMetric Orchestrator V2",
    description="Multi-session AI-powered game testing coordinator",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: Socket.IO ASGI wrapper will be applied after all routes are defined.
# We avoid mounting here because the FastAPI `app` is populated with routes
# afterwards. At module end we will wrap the FastAPI app with the Socket.IO
# ASGIApp so both websocket and HTTP requests are handled correctly.


# ==============================================================================
# SYSTEM ENDPOINTS
# ==============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "PlayMetric Orchestrator V2",
        "version": "2.0.0",
        "features": [
            "Multi-session parallel testing",
            "Real-time WebSocket updates",
            "Advanced RL agent with experience replay",
            "PostgreSQL + TimescaleDB data storage",
            "Cross-game knowledge sharing"
        ],
        "docs_url": "/docs"
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    # Database health
    db_healthy = False
    try:
        await db_manager.execute("SELECT 1")
        db_healthy = True
    except:
        pass
    
    # Orchestrator status
    orchestrator_status = multi_session_orchestrator.get_status()
    
    # WebSocket stats
    ws_stats = await ws_manager.get_stats()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "orchestrator": orchestrator_status,
        "websocket": ws_stats
    }


# ==============================================================================
# GAME MANAGEMENT ENDPOINTS
# ==============================================================================

@app.get("/games")
async def list_games():
    """List all games"""
    games = await db_manager.execute(
        """SELECT g.*, 
           COUNT(DISTINCT s.id) as total_sessions,
           COUNT(DISTINCT b.id) as total_bugs
           FROM games g
           LEFT JOIN game_versions gv ON gv.game_id = g.id
           LEFT JOIN sessions s ON s.game_version_id = gv.id
           LEFT JOIN bugs b ON b.game_version_id = gv.id
           GROUP BY g.id
           ORDER BY g.created_at DESC"""
    )
    return games


@app.post("/games")
async def create_game(request: CreateGameRequest):
    """Create new game"""
    game_id = await db_manager.execute_one(
        """INSERT INTO games (display_name, package_name, genre, metadata)
           VALUES ($1, $2, $3, $4)
           RETURNING id""",
        request.display_name, request.package_name, request.genre, request.metadata
    )
    
    return {"id": game_id['id'], **request.dict()}


@app.get("/games/{game_id}")
async def get_game(game_id: str):
    """Get game details"""
    game = await db_manager.execute_one(
        "SELECT * FROM games WHERE id = $1", game_id
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.get("/games/{game_id}/versions")
async def get_game_versions(game_id: str):
    """Get all versions of a game"""
    versions = await db_manager.execute(
        """SELECT * FROM game_versions 
           WHERE game_id = $1 
           ORDER BY version_code DESC""",
        game_id
    )
    return versions


@app.post("/games/upload")
async def upload_game_apk(genre: str = Body(...), apk: UploadFile = File(...)):
    """Upload APK and auto-create game with extracted metadata"""
    import tempfile
    from src.version_manager import APKParser
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as temp_file:
            content = await apk.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Parse APK to extract metadata
        apk_info = APKParser.get_apk_info(temp_path)
        package_name = apk_info.get('package_name', 'unknown')
        display_name = apk_info.get('app_label', package_name.split('.')[-1])
        
        # Check if game already exists
        existing_game = await db_manager.execute_one(
            "SELECT id FROM games WHERE package_name = $1", package_name
        )
        
        if existing_game:
            game_id = str(existing_game['id'])
            logger.info(f"Game already exists: {game_id}, uploading new version")
        else:
            # Create new game
            game_id = await db_manager.execute_one(
                """INSERT INTO games (display_name, package_name, genre)
                   VALUES ($1, $2, $3)
                   RETURNING id""",
                display_name, package_name, genre
            )
            game_id = str(game_id['id'])
            logger.info(f"Created new game: {game_id}")
        
        # Upload version
        result = await version_tracker.upload_version(
            game_id=game_id,
            apk_file_path=temp_path,
            uploaded_by="api_user"
        )
        
        # Clean up temp file
        os.unlink(temp_path)
        
        return {
            "message": "Game and APK uploaded successfully",
            "game_id": game_id,
            "display_name": display_name,
            "package_name": package_name,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error uploading game APK: {e}", exc_info=True)
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/games/{game_id}/versions/upload")
async def upload_apk(game_id: str, version: Optional[str] = None, file: UploadFile = File(...)):
    """Upload APK file"""
    import tempfile
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process and store APK
        result = await version_tracker.upload_version(
            game_id=game_id,
            apk_file_path=temp_path,
            uploaded_by="api_user"  # TODO: Get from auth
        )
        
        # Clean up temp file
        os.unlink(temp_path)
        
        return {
            "message": "APK uploaded successfully",
            **result
        }
        
    except Exception as e:
        logger.error(f"Error uploading APK: {e}", exc_info=True)
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/games/{game_id}/versions")
async def upload_version(game_id: str, version: str, apk: UploadFile = File(...)):
    """Upload APK file for a specific version"""
    import tempfile
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as temp_file:
            content = await apk.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process and store APK
        result = await version_tracker.upload_version(
            game_id=game_id,
            apk_file_path=temp_path,
            uploaded_by="api_user"  # TODO: Get from auth
        )
        
        # Clean up temp file
        os.unlink(temp_path)
        
        return {
            "message": "APK uploaded successfully",
            **result
        }
        
    except Exception as e:
        logger.error(f"Error uploading APK: {e}", exc_info=True)
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}/versions/history")
async def get_version_history(game_id: str):
    """Get version history for game"""
    try:
        history = await version_tracker.get_version_history(game_id)
        return {"versions": history}
    except Exception as e:
        logger.error(f"Error fetching version history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}/versions/{version_id}/comparison")
async def get_version_comparison(game_id: str, version_id: str):
    """Get version comparison details"""
    try:
        comparison = await version_tracker.get_version_comparison(version_id)
        if not comparison:
            raise HTTPException(status_code=404, detail="Comparison not found")
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching version comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ==============================================================================

@app.get("/sessions")
async def list_sessions(game_id: Optional[str] = None, status: Optional[str] = None):
    """List sessions with optional filters"""
    query = "SELECT * FROM sessions WHERE 1=1"
    params = []
    
    if game_id:
        params.append(game_id)
        query += f" AND game_id = ${len(params)}"
    
    if status:
        params.append(status)
        query += f" AND status = ${len(params)}"
    
    query += " ORDER BY created_at DESC LIMIT 100"
    
    sessions = await db_manager.execute(query, *params)
    return sessions


@app.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """Create new session (queued for execution)"""
    # Map priority string to enum
    priority_map = {
        'low': SessionPriority.LOW,
        'normal': SessionPriority.NORMAL,
        'high': SessionPriority.HIGH,
        'urgent': SessionPriority.URGENT
    }
    priority = priority_map.get(request.priority.lower(), SessionPriority.NORMAL)
    
    # Ensure game and version exist, create if needed
    try:
        # Check if version_id is a valid UUID
        import uuid
        uuid.UUID(request.version_id)
        game_version_id = request.version_id
    except (ValueError, AttributeError):
        # version_id is not a UUID, need to create game and version
        # Check if game exists
        game = await db_manager.execute_one(
            "SELECT id FROM games WHERE id = $1",
            request.game_id
        )
        
        if not game:
            # Create default game entry
            game_id = await db_manager.execute_one(
                """INSERT INTO games (id, package_name, display_name, genre)
                   VALUES ($1, $2, $3, 'puzzle')
                   RETURNING id""",
                request.game_id, f"com.game.{request.game_id}", f"Game {request.game_id}"
            )
            game_id = game_id['id']
        else:
            game_id = game['id']
        
        # Create game version
        version_result = await db_manager.execute_one(
            """INSERT INTO game_versions (game_id, version_name, version_code, apk_path)
               VALUES ($1, $2, 1, '')
               RETURNING id""",
            game_id, request.version_id or 'v1.0'
        )
        game_version_id = version_result['id']
    
    # Create session in database
    session_id = await db_manager.execute_one(
        """INSERT INTO sessions (game_version_id, agent_mode, status, config)
           VALUES ($1, $2, 'queued', $3)
           RETURNING id""",
        game_version_id, request.agent_mode, json.dumps(request.config) if request.config else '{}'
    )
    
    session_id = session_id['id']
    
    # Submit to orchestrator
    await multi_session_orchestrator.submit_session(
        session_id=session_id,
        game_id=request.game_id,
        version_id=request.version_id,
        config=request.config or {},
        priority=priority
    )
    
    return {
        "session_id": session_id,
        "status": "queued",
        "message": "Session queued for execution"
    }


@app.post("/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start a queued session immediately (bypass queue)"""
    # TODO: Implement priority escalation
    return {"message": "Start session endpoint - priority escalation pending"}


@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a running session"""
    await multi_session_orchestrator.cancel_session(session_id)
    
    return {
        "session_id": session_id,
        "status": "stopped",
        "message": "Session stopped successfully"
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session = await db_manager.execute_one(
        "SELECT * FROM sessions WHERE id = $1", session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/sessions/{session_id}/metrics")
async def get_session_metrics(
    session_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None
):
    """Get session performance metrics"""
    query = "SELECT * FROM session_metrics WHERE session_id = $1"
    params = [session_id]
    
    if start:
        params.append(start)
        query += f" AND timestamp >= ${len(params)}"
    
    if end:
        params.append(end)
        query += f" AND timestamp <= ${len(params)}"
    
    query += " ORDER BY timestamp ASC"
    
    metrics = await db_manager.execute(query, *params)
    return metrics


@app.get("/sessions/{session_id}/screenshots")
async def get_session_screenshots(session_id: str):
    """Get session screenshots"""
    screenshots = await db_manager.execute(
        """SELECT timestamp, file_path FROM screenshots 
           WHERE session_id = $1 
           ORDER BY timestamp DESC 
           LIMIT 100""",
        session_id
    )
    return screenshots


@app.get("/sessions/{session_id}/bugs")
async def get_session_bugs(session_id: str):
    """Get bugs detected in session"""
    bugs = await db_manager.execute(
        "SELECT * FROM bugs WHERE session_id = $1 ORDER BY first_seen DESC",
        session_id
    )
    return bugs


@app.get("/sessions/{session_id}/ai-thinking")
async def get_session_ai_thinking(session_id: str, limit: int = 100):
    """Get AI thinking logs for session"""
    logs = await db_manager.execute(
        """
        SELECT id, action_type, reasoning, q_values, epsilon, position, 
               ui_context, timestamp
        FROM ai_thinking_logs 
        WHERE session_id = $1 
        ORDER BY timestamp DESC 
        LIMIT $2
        """,
        session_id,
        limit
    )
    return list(reversed(logs))  # Return chronological order (oldest first)


# ==============================================================================
# BUG TRACKING ENDPOINTS
# ==============================================================================

@app.get("/bugs")
async def list_bugs(
    game_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None
):
    """List bugs with filters"""
    query = "SELECT * FROM bugs WHERE 1=1"
    params = []
    
    if game_id:
        # Join through game_versions to filter by game_id
        params.append(game_id)
        query = """
            SELECT b.* FROM bugs b
            JOIN game_versions gv ON b.game_version_id = gv.id
            WHERE gv.game_id = $1
        """
        if severity:
            params.append(severity)
            query += f" AND b.severity = ${len(params)}"
        if status:
            params.append(status)
            query += f" AND b.status = ${len(params)}"
    else:
        if severity:
            params.append(severity)
            query += f" AND severity = ${len(params)}"
        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"
    
    query += " ORDER BY detected_at DESC LIMIT 100"
    
    bugs = await db_manager.execute(query, *params)
    return bugs


@app.get("/bugs/{bug_id}")
async def get_bug(bug_id: str):
    """Get bug details"""
    bug = await db_manager.execute_one(
        "SELECT * FROM bugs WHERE id = $1", bug_id
    )
    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found")
    return bug


@app.put("/bugs/{bug_id}")
async def update_bug(bug_id: str, request: UpdateBugRequest):
    """Update bug status/assignment"""
    updates = []
    params = []
    
    if request.status:
        params.append(request.status)
        updates.append(f"status = ${len(params)}")
        
        if request.status == 'resolved':
            updates.append("resolved_at = NOW()")
    
    if request.assigned_to:
        params.append(request.assigned_to)
        updates.append(f"assigned_to = ${len(params)}")
    
    if request.resolution_notes:
        params.append(request.resolution_notes)
        updates.append(f"resolution_notes = ${len(params)}")
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(bug_id)
    query = f"UPDATE bugs SET {', '.join(updates)} WHERE id = ${len(params)}"
    
    await db_manager.execute_write(query, *params)
    
    return {"message": "Bug updated successfully"}


# ==============================================================================
# ANALYTICS ENDPOINTS
# ==============================================================================

@app.get("/analytics/games/{game_id}/statistics")
async def get_game_statistics(game_id: str):
    """Get comprehensive game statistics"""
    stats = await db_manager.execute_one(
        "SELECT * FROM game_statistics WHERE game_id = $1",
        game_id
    )
    return stats or {}


@app.get("/analytics/games/{game_id}/difficulty")
async def get_difficulty_analysis(game_id: str):
    """Get difficulty analysis for game"""
    analysis = await db_manager.execute(
        """SELECT * FROM difficulty_analysis 
           WHERE game_id = $1 
           ORDER BY level_number""",
        game_id
    )
    return analysis


@app.get("/analytics/versions/compare")
async def compare_versions(v1: str, v2: str):
    """Compare two game versions"""
    comparison = await db_manager.execute_one(
        """SELECT * FROM version_comparisons 
           WHERE (version1_id = $1 AND version2_id = $2)
              OR (version1_id = $2 AND version2_id = $1)""",
        v1, v2
    )
    
    if not comparison:
        return {"message": "No comparison data available"}
    
    return comparison


# ==============================================================================
# RL AGENT ENDPOINTS
# ==============================================================================

@app.get("/agent/statistics")
async def get_agent_statistics():
    """Get RL agent statistics"""
    try:
        response = await http_client.get(f"{AGENT_URL}/agent/statistics")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent/memory/stats")
async def get_agent_memory_stats():
    """Get RL agent memory statistics"""
    try:
        response = await http_client.get(f"{AGENT_URL}/agent/memory/stats")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/training/configure")
async def configure_agent_training(enable_training: bool, training_interval: Optional[int] = None):
    """Configure RL agent training"""
    try:
        response = await http_client.post(
            f"{AGENT_URL}/agent/training/configure",
            json={
                "enable_training": enable_training,
                "training_interval": training_interval
            }
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# ORCHESTRATOR STATUS ENDPOINTS
# ==============================================================================

@app.get("/orchestrator/status")
async def get_orchestrator_status():
    """Get multi-session orchestrator status"""
    return multi_session_orchestrator.get_status()


@app.get("/orchestrator/queue")
async def get_queue_status():
    """Get session queue status"""
    status = multi_session_orchestrator.get_status()
    return {
        "queue_sizes": status['queue_sizes'],
        "running_sessions": status['running_sessions'],
        "resource_usage": status['resource_usage']
    }


# ==============================================================================
# INTERNAL ENDPOINTS (for inter-service communication)
# ==============================================================================

@app.post("/internal/broadcast_screenshot")
async def broadcast_screenshot(data: dict):
    """Broadcast screenshot update via WebSocket"""
    try:
        await ws_manager.broadcast_screenshot(
            session_id=data['session_id'],
            screenshot_data={
                'path': data['screenshot_path'],
                'timestamp': data['timestamp']
            }
        )
        return {"status": "broadcasted"}
    except Exception as e:
        logger.error(f"Error broadcasting screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/broadcast_ai_thinking")
async def broadcast_ai_thinking(data: dict = Body(...)):
    """Broadcast AI thinking/decisions via WebSocket"""
    try:
        await ws_manager.broadcast_message(
            f"session_{data['session_id']}",
            {
                'type': 'ai_thinking',
                'data': data['thinking']
            }
        )
        return {"status": "broadcasted"}
    except Exception as e:
        logger.error(f"Error broadcasting AI thinking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/session/setup")
async def setup_session(session_id: str):
    """Setup session: install APK and launch app"""
    try:
        # Get session details
        session = await db_manager.execute_one(
            "SELECT * FROM sessions WHERE id = $1", session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get game version details
        version = await db_manager.execute_one(
            "SELECT * FROM game_versions WHERE id = $1", session['game_version_id']
        )
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Get game details
        game = await db_manager.execute_one(
            "SELECT * FROM games WHERE id = $1", version['game_id']
        )
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        emulator_manager_url = os.getenv("EMULATOR_MANAGER_URL", "http://emulator-manager:8005")
        
        # Install APK
        logger.info(f"Installing APK for session {session_id}: {version['apk_path']}")
        install_response = await http_client.post(
            f"{emulator_manager_url}/apk/install",
            json={"apk_path": version['apk_path']}
        )
        
        if install_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to install APK")
        
        # Launch app
        logger.info(f"Launching app: {game['package_name']}")
        launch_response = await http_client.post(
            f"{emulator_manager_url}/app/launch",
            json={"package_name": game['package_name']}
        )
        
        if launch_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to launch app")
        
        # Update session status
        await db_manager.execute_write(
            "UPDATE sessions SET status = 'running', started_at = NOW() WHERE id = $1",
            session_id
        )
        
        # Notify agent to start playing
        agent_url = os.getenv("AGENT_URL", "http://agent:8004")
        await http_client.post(
            f"{agent_url}/play/start",
            json={
                "session_id": str(session_id),
                "game_id": str(version['game_id']),
                "package_name": game['package_name'],
                "agent_mode": session['agent_mode']
            }
        )
        
        return {
            "status": "setup_complete",
            "session_id": session_id,
            "apk_installed": True,
            "app_launched": True,
            "agent_started": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Wrap the FastAPI app with Socket.IO ASGI app so websocket paths are
# correctly handled in the same process. This must be done after all
# routes and middleware have been registered on the FastAPI instance.
fastapi_app = app
app = get_websocket_manager().get_asgi_app(other_asgi_app=fastapi_app)

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    # uvicorn can run the wrapped ASGI app which will delegate HTTP
    # requests to the FastAPI app and handle Socket.IO websocket traffic.
    uvicorn.run(app, host=host, port=port)
