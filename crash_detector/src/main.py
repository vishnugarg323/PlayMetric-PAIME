"""
Crash Detector Service - Main API for crash detection and monitoring
"""
import os
import asyncio
import subprocess
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

from .detector import CrashDetector, CrashType

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
detector: Optional[CrashDetector] = None
monitor_task: Optional[asyncio.Task] = None
is_monitoring = False
current_package = None
emulator_device = None


# Pydantic models
class MonitorRequest(BaseModel):
    package_name: Optional[str] = None
    session_id: str = "default"


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global detector, emulator_device
    
    # Startup
    logger.info("Starting Crash Detector Service...")
    
    detector = CrashDetector()
    
    # Connect to emulator
    emulator_host = os.getenv("EMULATOR_HOST", "emulator")
    adb_port = int(os.getenv("ADB_PORT", "5555"))
    emulator_device = f"{emulator_host}:{adb_port}"
    
    logger.info(f"Connecting to emulator at {emulator_device}")
    
    # Connect via ADB
    try:
        subprocess.run(
            ["adb", "connect", emulator_device],
            capture_output=True,
            timeout=10
        )
        logger.info("Connected to emulator")
    except Exception as e:
        logger.error(f"Failed to connect to emulator: {e}")
    
    logger.info("Crash Detector Service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Crash Detector Service...")
    await stop_monitoring()


app = FastAPI(
    title="PlayMetric Crash Detector",
    description="Monitors logcat for crashes and ANRs",
    version="1.0.0",
    lifespan=lifespan
)


async def monitoring_loop():
    """Background task for continuous crash monitoring"""
    global is_monitoring, current_package
    
    check_interval = float(os.getenv("CRASH_CHECK_INTERVAL", "2.0"))
    log_lines = 200
    
    logger.info(f"Starting monitoring loop (interval: {check_interval}s)")
    
    while is_monitoring:
        try:
            # Get logcat
            result = subprocess.run(
                ["adb", "-s", emulator_device, "logcat", "-d", "-t", str(log_lines)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Analyze for crashes
                crashes = detector.analyze_logcat(
                    result.stdout,
                    package_filter=current_package
                )
                
                if crashes:
                    logger.warning(f"Detected {len(crashes)} new crashes")
                    
                    # Save crash report
                    session_dir = f"/data/crashes/{current_package or 'all'}"
                    os.makedirs(session_dir, exist_ok=True)
                    detector.save_crash_report(f"{session_dir}/crash_report.json")
            
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(5)


async def stop_monitoring():
    """Stop the monitoring loop"""
    global is_monitoring, monitor_task
    
    if is_monitoring:
        is_monitoring = False
        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "monitoring": is_monitoring,
        "package": current_package,
        "total_crashes": len(detector.crashes) if detector else 0
    }


@app.post("/monitor/start")
async def start_monitoring(request: MonitorRequest):
    """Start crash monitoring"""
    global is_monitoring, monitor_task, current_package
    
    if is_monitoring:
        return {
            "message": "Monitoring already running",
            "package": current_package
        }
    
    current_package = request.package_name
    is_monitoring = True
    
    # Clear logcat to start fresh
    try:
        subprocess.run(
            ["adb", "-s", emulator_device, "logcat", "-c"],
            capture_output=True,
            timeout=5
        )
    except Exception as e:
        logger.warning(f"Failed to clear logcat: {e}")
    
    monitor_task = asyncio.create_task(monitoring_loop())
    
    return {
        "message": "Monitoring started",
        "package": current_package,
        "interval": float(os.getenv("CRASH_CHECK_INTERVAL", "2.0"))
    }


@app.post("/monitor/stop")
async def stop_monitoring_endpoint():
    """Stop crash monitoring"""
    await stop_monitoring()
    return {"message": "Monitoring stopped"}


@app.get("/monitor/status")
async def monitoring_status():
    """Get monitoring status"""
    return {
        "monitoring": is_monitoring,
        "package": current_package,
        "total_crashes": len(detector.crashes) if detector else 0
    }


@app.get("/crashes")
async def get_crashes():
    """Get all detected crashes"""
    if not detector:
        return {"crashes": [], "count": 0}
    
    crashes = [crash.to_dict() for crash in detector.crashes]
    return {
        "crashes": crashes,
        "count": len(crashes)
    }


@app.get("/crashes/statistics")
async def get_crash_statistics():
    """Get crash statistics"""
    if not detector:
        return {
            "total_crashes": 0,
            "by_type": {},
            "by_severity": {}
        }
    
    return detector.get_crash_statistics()


@app.post("/crashes/clear")
async def clear_crashes():
    """Clear crash history"""
    if detector:
        detector.clear_crashes()
    return {"message": "Crash history cleared"}


@app.get("/logcat")
async def get_logcat(lines: int = 100):
    """Get recent logcat output"""
    try:
        result = subprocess.run(
            ["adb", "-s", emulator_device, "logcat", "-d", "-t", str(lines)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "logcat": result.stdout,
            "lines": len(result.stdout.split('\n'))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logcat: {str(e)}")


@app.post("/logcat/clear")
async def clear_logcat():
    """Clear logcat buffer"""
    try:
        subprocess.run(
            ["adb", "-s", emulator_device, "logcat", "-c"],
            capture_output=True,
            timeout=5
        )
        return {"message": "Logcat cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logcat: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("CRASH_DETECTOR_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
