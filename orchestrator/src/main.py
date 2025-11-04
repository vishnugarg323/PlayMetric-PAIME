"""
Orchestrator API - Main coordinator for the PlayMetric system
"""
import os
import asyncio
import subprocess
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import uvicorn

from .session_manager import SessionManager, SessionStatus

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
session_manager: Optional[SessionManager] = None
http_client: Optional[httpx.AsyncClient] = None

# Service URLs
OBSERVATION_URL = os.getenv("OBSERVATION_URL", "http://observation:8001")
CRASH_DETECTOR_URL = os.getenv("CRASH_DETECTOR_URL", "http://crash-detector:8002")
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://analytics:8003")
AGENT_URL = os.getenv("AGENT_URL", "http://agent:8004")


# Pydantic models
class InstallAPKRequest(BaseModel):
    apk_path: str


class StartSessionRequest(BaseModel):
    package_name: str
    apk_path: Optional[str] = None
    agent_mode: str = "heuristic"
    duration_minutes: Optional[int] = 30
    auto_install: bool = True


class StopSessionRequest(BaseModel):
    session_id: str
    save_analytics: bool = True


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global session_manager, http_client
    
    # Startup
    logger.info("Starting Orchestrator Service...")
    
    session_manager = SessionManager()
    http_client = httpx.AsyncClient(timeout=30.0)
    
    logger.info("Orchestrator Service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Orchestrator Service...")
    if http_client:
        await http_client.aclose()


app = FastAPI(
    title="PlayMetric Orchestrator",
    description="Main coordinator for AI-powered game testing",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "name": "PlayMetric Orchestrator",
        "version": "1.0.0",
        "description": "AI-powered mobile game testing system",
        "docs_url": "/docs",
        "services": {
            "observation": OBSERVATION_URL,
            "crash_detector": CRASH_DETECTOR_URL,
            "analytics": ANALYTICS_URL,
            "agent": AGENT_URL
        }
    }


@app.get("/health")
async def health_check():
    """System health check"""
    services_status = {}
    
    # Check each service
    services = {
        "observation": OBSERVATION_URL,
        "crash_detector": CRASH_DETECTOR_URL,
        "analytics": ANALYTICS_URL,
        "agent": AGENT_URL
    }
    
    for name, url in services.items():
        try:
            response = await http_client.get(f"{url}/health", timeout=5.0)
            services_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services_status[name] = "unavailable"
    
    active_session = session_manager.get_active_session()
    
    return {
        "status": "healthy",
        "services": services_status,
        "active_session": active_session.session_id if active_session else None,
        "total_sessions": len(session_manager.sessions)
    }


@app.post("/api/install-apk")
async def install_apk(request: InstallAPKRequest):
    """Install APK on emulator"""
    try:
        response = await http_client.post(
            f"{OBSERVATION_URL}/device/install",
            json={"apk_path": request.apk_path}
        )
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to install APK: {str(e)}")


@app.post("/api/start-session")
async def start_session(request: StartSessionRequest, background_tasks: BackgroundTasks):
    """Start a new testing session"""
    try:
        # Create session
        session = session_manager.create_session(
            package_name=request.package_name,
            apk_path=request.apk_path,
            agent_mode=request.agent_mode,
            duration_minutes=request.duration_minutes
        )
        
        session_manager.set_active_session(session.session_id)
        
        # Install APK if needed
        if request.auto_install and request.apk_path:
            logger.info(f"Installing APK: {request.apk_path}")
            session.status = SessionStatus.INSTALLING
            
            try:
                await http_client.post(
                    f"{OBSERVATION_URL}/device/install",
                    json={"apk_path": request.apk_path}
                )
            except Exception as e:
                session.fail(f"APK installation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Launch app
        logger.info(f"Launching app: {request.package_name}")
        try:
            await http_client.post(
                f"{OBSERVATION_URL}/device/launch",
                json={"package_name": request.package_name}
            )
        except Exception as e:
            logger.warning(f"Failed to launch app: {e}")
        
        # Start observation capture
        await http_client.post(
            f"{OBSERVATION_URL}/capture/start",
            json={"session_id": session.session_id}
        )
        
        # Start crash monitoring
        await http_client.post(
            f"{CRASH_DETECTOR_URL}/monitor/start",
            json={
                "package_name": request.package_name,
                "session_id": session.session_id
            }
        )
        
        # Start agent
        await http_client.post(
            f"{AGENT_URL}/play/start",
            json={
                "agent_mode": request.agent_mode,
                "session_id": session.session_id,
                "package_name": request.package_name
            }
        )
        
        session.start()
        
        # Schedule auto-stop if duration specified
        if request.duration_minutes:
            background_tasks.add_task(
                auto_stop_session,
                session.session_id,
                request.duration_minutes * 60
            )
        
        return {
            "message": "Session started successfully",
            "session": session.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def auto_stop_session(session_id: str, delay_seconds: int):
    """Auto-stop session after delay"""
    await asyncio.sleep(delay_seconds)
    
    logger.info(f"Auto-stopping session {session_id}")
    
    try:
        await http_client.post(
            "/api/stop-session",
            json={"session_id": session_id, "save_analytics": True}
        )
    except Exception as e:
        logger.error(f"Error auto-stopping session: {e}")


@app.post("/api/stop-session")
async def stop_session(request: StopSessionRequest):
    """Stop a testing session"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status not in [SessionStatus.RUNNING, SessionStatus.PAUSED]:
        raise HTTPException(status_code=400, detail=f"Session is {session.status}")
    
    try:
        # Stop agent
        agent_response = await http_client.post(f"{AGENT_URL}/play/stop")
        agent_stats = agent_response.json().get('statistics', {})
        
        # Stop crash monitoring
        await http_client.post(f"{CRASH_DETECTOR_URL}/monitor/stop")
        
        # Stop capture
        await http_client.post(f"{OBSERVATION_URL}/capture/stop")
        
        # Get crash statistics
        crash_response = await http_client.get(f"{CRASH_DETECTOR_URL}/crashes/statistics")
        crash_stats = crash_response.json()
        
        # Update session metrics
        session.update_metrics(
            actions_performed=agent_stats.get('total_actions', 0),
            crashes_detected=crash_stats.get('total_crashes', 0)
        )
        
        # Save analytics if requested
        if request.save_analytics:
            # Add session to analytics
            await http_client.post(
                f"{ANALYTICS_URL}/session/add",
                json={
                    "session_id": session.session_id,
                    "duration": session.get_duration(),
                    "crashes": crash_stats.get('total_crashes', 0),
                    "levels_completed": 0,  # Would need to track this
                    "actions_performed": agent_stats.get('total_actions', 0)
                }
            )
            
            # Save reports
            await http_client.post(
                f"{ANALYTICS_URL}/analytics/save",
                params={"session_id": session.session_id}
            )
        
        session.complete()
        
        return {
            "message": "Session stopped successfully",
            "session": session.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        session.fail(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions():
    """List all sessions"""
    return {
        "sessions": session_manager.list_sessions(),
        "active_session": session_manager.active_session.session_id if session_manager.active_session else None
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@app.get("/api/analytics/latest")
async def get_latest_analytics():
    """Get latest analytics summary"""
    try:
        response = await http_client.get(f"{ANALYTICS_URL}/analytics/summary")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@app.get("/api/analytics/{session_id}")
async def get_session_analytics(session_id: str):
    """Get analytics for specific session"""
    import json
    
    analytics_dir = f"/data/analytics/{session_id}"
    
    try:
        result = {}
        
        # Load difficulty analysis
        difficulty_path = f"{analytics_dir}/difficulty_analysis.json"
        if os.path.exists(difficulty_path):
            with open(difficulty_path) as f:
                result['difficulty'] = json.load(f)
        
        # Load retention estimate
        retention_path = f"{analytics_dir}/retention_estimate.json"
        if os.path.exists(retention_path):
            with open(retention_path) as f:
                result['retention'] = json.load(f)
        
        if not result:
            raise HTTPException(status_code=404, detail="Analytics not found for session")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading analytics: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
