"""
Observation Service - Main API for screen capture and device interaction
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from .adb_controller import ADBController
from .capture import ScreenCapture

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
adb: Optional[ADBController] = None
capture: Optional[ScreenCapture] = None
capture_task: Optional[asyncio.Task] = None
is_capturing = False
current_session_id = "default"


# Pydantic models
class TapRequest(BaseModel):
    x: int
    y: int


class SwipeRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    duration: int = 300


class KeyEventRequest(BaseModel):
    keycode: str  # BACK, HOME, MENU, etc.


class InstallAPKRequest(BaseModel):
    apk_path: str


class LaunchAppRequest(BaseModel):
    package_name: str


class SessionRequest(BaseModel):
    session_id: str


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global adb, capture
    
    # Startup
    logger.info("Starting Observation Service...")
    
    # Initialize ADB
    emulator_host = os.getenv("EMULATOR_HOST", "emulator")
    adb_port = int(os.getenv("ADB_PORT", "5555"))
    adb = ADBController(host=emulator_host, port=adb_port)
    
    # Connect to emulator
    logger.info(f"Connecting to emulator at {emulator_host}:{adb_port}")
    if not adb.connect():
        logger.error("Failed to connect to emulator")
    
    # Initialize screen capture
    screenshot_format = os.getenv("SCREENSHOT_FORMAT", "png")
    screenshot_quality = int(os.getenv("SCREENSHOT_QUALITY", "85"))
    capture = ScreenCapture(format=screenshot_format, quality=screenshot_quality)
    
    logger.info("Observation Service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Observation Service...")
    await stop_capture()


app = FastAPI(
    title="PlayMetric Observation Service",
    description="Captures screenshots and controls Android device",
    version="1.0.0",
    lifespan=lifespan
)


async def capture_loop():
    """Background task for continuous screenshot capture"""
    global is_capturing, current_session_id
    
    screenshot_interval = float(os.getenv("SCREENSHOT_INTERVAL", "1.0"))
    temp_screenshot = "/tmp/screen.png"
    
    logger.info(f"Starting capture loop (interval: {screenshot_interval}s)")
    
    while is_capturing:
        try:
            # Take screenshot
            if adb.take_screenshot(temp_screenshot):
                # Save to storage
                capture.save_screenshot(temp_screenshot, session_id=current_session_id)
            
            await asyncio.sleep(screenshot_interval)
            
        except Exception as e:
            logger.error(f"Error in capture loop: {e}")
            await asyncio.sleep(1)


async def stop_capture():
    """Stop the capture loop"""
    global is_capturing, capture_task
    
    if is_capturing:
        is_capturing = False
        if capture_task:
            capture_task.cancel()
            try:
                await capture_task
            except asyncio.CancelledError:
                pass
        logger.info("Capture stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "adb_connected": adb.connected if adb else False,
        "capturing": is_capturing,
        "session_id": current_session_id
    }


@app.post("/capture/start")
async def start_capture(session: SessionRequest, background_tasks: BackgroundTasks):
    """Start continuous screenshot capture"""
    global is_capturing, capture_task, current_session_id
    
    if is_capturing:
        return {"message": "Capture already running", "session_id": current_session_id}
    
    current_session_id = session.session_id
    is_capturing = True
    capture_task = asyncio.create_task(capture_loop())
    
    return {
        "message": "Capture started",
        "session_id": current_session_id,
        "interval": float(os.getenv("SCREENSHOT_INTERVAL", "1.0"))
    }


@app.post("/capture/stop")
async def stop_capture_endpoint():
    """Stop screenshot capture"""
    await stop_capture()
    return {"message": "Capture stopped"}


@app.get("/capture/status")
async def capture_status():
    """Get capture status"""
    return {
        "capturing": is_capturing,
        "session_id": current_session_id,
        "screenshot_count": capture.screenshot_count if capture else 0,
        "last_screenshot": capture.last_screenshot if capture else None
    }


@app.get("/screenshot/latest")
async def get_latest_screenshot():
    """Get the latest screenshot"""
    if not capture or not capture.last_screenshot:
        raise HTTPException(status_code=404, detail="No screenshots available")
    
    return FileResponse(capture.last_screenshot)


@app.post("/screenshot/single")
async def take_single_screenshot():
    """Take a single screenshot on demand"""
    temp_screenshot = "/tmp/screen_single.png"
    
    if not adb.take_screenshot(temp_screenshot):
        raise HTTPException(status_code=500, detail="Failed to capture screenshot")
    
    saved_path = capture.save_screenshot(temp_screenshot, session_id=current_session_id)
    
    return {
        "message": "Screenshot captured",
        "path": saved_path
    }


@app.post("/action/tap")
async def perform_tap(request: TapRequest):
    """Perform tap action on device"""
    success = adb.tap(request.x, request.y)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to perform tap")
    
    return {"message": f"Tapped at ({request.x}, {request.y})"}


@app.post("/action/swipe")
async def perform_swipe(request: SwipeRequest):
    """Perform swipe action on device"""
    success = adb.swipe(request.x1, request.y1, request.x2, request.y2, request.duration)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to perform swipe")
    
    return {
        "message": f"Swiped from ({request.x1}, {request.y1}) to ({request.x2}, {request.y2})"
    }


@app.post("/action/key")
async def press_key(request: KeyEventRequest):
    """Press a key on device"""
    success = adb.press_key(request.keycode)
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to press key {request.keycode}")
    
    return {"message": f"Pressed key: {request.keycode}"}


@app.get("/device/screen-size")
async def get_screen_size():
    """Get device screen dimensions"""
    width, height = adb.get_screen_size()
    return {"width": width, "height": height}


@app.get("/device/current-app")
async def get_current_app():
    """Get currently focused app"""
    package = adb.get_current_app()
    return {"package_name": package}


@app.post("/device/install")
async def install_apk(request: InstallAPKRequest):
    """Install APK on device"""
    success = adb.install_apk(request.apk_path)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to install APK")
    
    return {"message": "APK installed successfully", "path": request.apk_path}


@app.post("/device/launch")
async def launch_app(request: LaunchAppRequest):
    """Launch application"""
    success = adb.launch_app(request.package_name)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to launch app")
    
    return {"message": "App launched", "package_name": request.package_name}


@app.post("/device/stop")
async def stop_app(request: LaunchAppRequest):
    """Stop application"""
    success = adb.stop_app(request.package_name)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop app")
    
    return {"message": "App stopped", "package_name": request.package_name}


@app.get("/device/packages")
async def list_packages():
    """List installed packages"""
    packages = adb.get_installed_packages()
    return {"packages": packages, "count": len(packages)}


@app.get("/analysis/ui-elements")
async def detect_ui_elements():
    """Detect UI elements in latest screenshot"""
    if not capture or not capture.last_screenshot:
        raise HTTPException(status_code=404, detail="No screenshots available")
    
    elements = capture.detect_ui_elements(capture.last_screenshot)
    return {"ui_elements": elements, "count": len(elements)}


if __name__ == "__main__":
    port = int(os.getenv("OBSERVATION_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
