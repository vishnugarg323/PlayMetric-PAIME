"""
Emulator Manager Service
Manages Android emulator lifecycle, APK installation, and app launching
"""
import os
import sys
import asyncio
import logging
import subprocess
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import uvicorn

sys.path.append('/app/shared')
from database import DatabaseManager

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_manager: Optional[DatabaseManager] = None

# Emulator configuration
EMULATOR_HOST = os.getenv("EMULATOR_HOST", "emulator")
EMULATOR_PORT = os.getenv("EMULATOR_PORT", "5555")
USE_HOST_ADB = os.getenv("USE_HOST_ADB", "false").lower() == "true"

# Set ADB server host for Docker containers to connect to Windows host
if USE_HOST_ADB:
    os.environ["ADB_SERVER_SOCKET"] = f"tcp:192.168.137.202:5037"
    logger.info(f"Using host ADB server at 192.168.137.202:5037")

# Device address - for host ADB, just use the device serial
if USE_HOST_ADB:
    ADB_DEVICE = None  # Will be auto-detected from adb devices
else:
    ADB_DEVICE = f"{EMULATOR_HOST}:{EMULATOR_PORT}"


# Pydantic models
class InstallAPKRequest(BaseModel):
    apk_path: str

class LaunchAppRequest(BaseModel):
    package_name: str
    activity: Optional[str] = None

class TapRequest(BaseModel):
    x: int
    y: int

class SwipeRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    duration: int = 300

class TypeTextRequest(BaseModel):
    text: str


def get_adb_base_command() -> list[str]:
    """Get base ADB command with device selector if needed"""
    if USE_HOST_ADB:
        # When using host ADB server, don't specify device (or use first available)
        return ['adb']
    else:
        # When using networked emulator, specify device
        return ['adb', '-s', ADB_DEVICE]


def run_adb_command(command: list[str], timeout: int = 30) -> str:
    """Run ADB command and return output"""
    try:
        adb_cmd = get_adb_base_command() + command
        result = subprocess.run(
            adb_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"ADB command failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"ADB command failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"ADB command timed out: {command}")
        raise HTTPException(status_code=500, detail="ADB command timed out")


async def wait_for_device(timeout: int = 120) -> bool:
    """Wait for Android device to be ready"""
    if USE_HOST_ADB:
        logger.info("Waiting for device on host ADB server...")
    else:
        logger.info(f"Waiting for device {ADB_DEVICE}...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if not USE_HOST_ADB:
                # Connect to network emulator
                subprocess.run(['adb', 'connect', ADB_DEVICE], 
                             capture_output=True, timeout=10, check=True)
            
            # Check if any device is ready
            adb_cmd = get_adb_base_command() + ['shell', 'getprop', 'sys.boot_completed']
            result = subprocess.run(adb_cmd, capture_output=True, text=True, timeout=10)
            
            if result.stdout.strip() == '1':
                # Get device info
                devices_result = subprocess.run(['adb', 'devices'], 
                                              capture_output=True, text=True, timeout=5)
                logger.info(f"Device ready! Connected devices:\n{devices_result.stdout}")
                return True
        except Exception as e:
            logger.debug(f"Device not ready yet: {e}")
        
        await asyncio.sleep(5)
    
    logger.error(f"Device not ready after {timeout}s")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_manager
    
    logger.info("Starting Emulator Manager Service...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.connect()
    logger.info("Database connected")
    
    # Wait for emulator
    if not await wait_for_device():
        logger.warning("Emulator not ready, but continuing...")
    
    logger.info("Emulator Manager Service ready")
    
    yield
    
    logger.info("Shutting down Emulator Manager Service...")
    if db_manager:
        await db_manager.disconnect()


app = FastAPI(title="Emulator Manager", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if device is connected
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        device_connected = ADB_DEVICE in result.stdout or 'emulator' in result.stdout
        
        return {
            "status": "healthy" if device_connected else "emulator_not_connected",
            "device": ADB_DEVICE,
            "connected": device_connected
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/emulator/connect")
async def connect_to_emulator():
    """Connect to emulator via ADB"""
    try:
        subprocess.run(['adb', 'connect', ADB_DEVICE], check=True, timeout=10)
        return {"status": "connected", "device": ADB_DEVICE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")


@app.post("/apk/install")
async def install_apk(request: InstallAPKRequest):
    """Install APK on emulator"""
    try:
        apk_path = request.apk_path
        if not Path(apk_path).exists():
            raise HTTPException(status_code=404, detail=f"APK not found: {apk_path}")
        
        logger.info(f"Installing APK: {apk_path}")
        # Use -r (replace), -t (allow test packages), -g (grant all permissions), -d (allow downgrade)
        output = run_adb_command(['install', '-r', '-t', '-g', '-d', apk_path], timeout=120)
        
        return {
            "status": "installed",
            "apk_path": apk_path,
            "output": output
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to install APK: {error_msg}")
        
        # Provide helpful error message for split APK issue
        if "INSTALL_FAILED_MISSING_SPLIT" in error_msg:
            raise HTTPException(
                status_code=400, 
                detail="This APK is a split APK (from Google Play App Bundle). Please upload a universal/standalone APK instead. You can generate one using bundletool or use APKs from sources other than Play Store."
            )
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/app/launch")
async def launch_app(request: LaunchAppRequest):
    """Launch app on emulator"""
    try:
        package_name = request.package_name
        
        # If activity not provided, try to get main activity
        if not request.activity:
            # Get main activity from package
            output = run_adb_command([
                'shell', 'cmd', 'package', 'resolve-activity',
                '--brief', package_name
            ])
            if output:
                # Parse the activity name from output like "com.package.name/com.package.MainActivity"
                lines = output.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if '/' in line and 'priority=' not in line:
                        # Extract activity name after the /
                        parts = line.split('/')
                        if len(parts) >= 2:
                            request.activity = parts[1].split()[0]  # Take first part before any spaces
                            break
        
        if not request.activity:
            raise HTTPException(status_code=400, detail="Could not determine main activity")
        
        logger.info(f"Launching {package_name}/{request.activity}")
        
        # Launch app
        output = run_adb_command([
            'shell', 'am', 'start',
            '-n', f"{package_name}/{request.activity}",
            '-a', 'android.intent.action.MAIN',
            '-c', 'android.intent.category.LAUNCHER'
        ])
        
        return {
            "status": "launched",
            "package": package_name,
            "activity": request.activity,
            "output": output
        }
    except Exception as e:
        logger.error(f"Failed to launch app: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/app/stop")
async def stop_app(package_name: str):
    """Stop/force close app"""
    try:
        output = run_adb_command(['shell', 'am', 'force-stop', package_name])
        return {"status": "stopped", "package": package_name, "output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/app/running")
async def is_app_running(package: str):
    """Check if app package is running"""
    try:
        # Use pidof to check if the package process is running
        output = run_adb_command(['shell', 'pidof', package])
        is_running = bool(output and output.strip())
        
        return {
            "running": is_running,
            "package": package,
            "pid": output.strip() if is_running else None
        }
    except Exception as e:
        logger.error(f"Failed to check app running status: {e}")
        # If command fails, assume not running
        return {"running": False, "package": package, "error": str(e)}


@app.post("/input/tap")
async def tap(request: TapRequest):
    """Perform tap action"""
    try:
        output = run_adb_command(['shell', 'input', 'tap', str(request.x), str(request.y)])
        return {"status": "success", "action": "tap", "x": request.x, "y": request.y}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/input/swipe")
async def swipe(request: SwipeRequest):
    """Perform swipe action"""
    try:
        output = run_adb_command([
            'shell', 'input', 'swipe',
            str(request.x1), str(request.y1),
            str(request.x2), str(request.y2),
            str(request.duration)
        ])
        return {
            "status": "success",
            "action": "swipe",
            "from": [request.x1, request.y1],
            "to": [request.x2, request.y2]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/input/text")
async def type_text(request: TypeTextRequest):
    """Type text"""
    try:
        # Escape special characters for shell
        text = request.text.replace(' ', '%s').replace('&', '\\&')
        output = run_adb_command(['shell', 'input', 'text', text])
        return {"status": "success", "action": "type", "text": request.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/input/back")
async def press_back():
    """Press Android BACK button"""
    try:
        output = run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_BACK'])
        return {"status": "success", "action": "back"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/input/home")
async def press_home():
    """Press Android HOME button"""
    try:
        output = run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
        return {"status": "success", "action": "home"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screenshot")
async def capture_screenshot():
    """Capture screenshot from emulator"""
    try:
        # Capture screenshot to device
        run_adb_command(['shell', 'screencap', '/sdcard/screenshot.png'])
        
        # Pull screenshot
        timestamp = int(time.time())
        local_path = f"/tmp/screenshot_{timestamp}.png"
        run_adb_command(['pull', '/sdcard/screenshot.png', local_path])
        
        return {
            "status": "success",
            "path": local_path,
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/device/info")
async def get_device_info():
    """Get device information"""
    try:
        info = {
            "device": ADB_DEVICE,
            "android_version": run_adb_command(['shell', 'getprop', 'ro.build.version.release']),
            "sdk_version": run_adb_command(['shell', 'getprop', 'ro.build.version.sdk']),
            "manufacturer": run_adb_command(['shell', 'getprop', 'ro.product.manufacturer']),
            "model": run_adb_command(['shell', 'getprop', 'ro.product.model']),
            "display_size": run_adb_command(['shell', 'wm', 'size']),
        }
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8005"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
