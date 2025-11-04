from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import subprocess
import base64
import io
from PIL import Image
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Emulator Stream Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMULATOR_HOST = os.getenv("EMULATOR_HOST", "emulator")
ADB_PORT = os.getenv("ADB_PORT", "5555")
FPS = int(os.getenv("STREAM_FPS", "3"))
FRAME_DELAY = 1.0 / FPS

class EmulatorStreamer:
    def __init__(self):
        self.connected = False
        self.adb_device = f"{EMULATOR_HOST}:{ADB_PORT}"
    
    async def connect(self):
        """Connect to emulator via ADB"""
        try:
            # Check if already connected
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if self.adb_device not in result.stdout:
                # Connect to emulator
                subprocess.run(
                    ["adb", "connect", self.adb_device],
                    capture_output=True,
                    timeout=10
                )
                await asyncio.sleep(2)
            
            self.connected = True
            logger.info(f"Connected to emulator: {self.adb_device}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to emulator: {e}")
            return False
    
    async def capture_screenshot(self):
        """Capture screenshot from emulator"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.adb_device, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout:
                return result.stdout
            return None
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    async def get_boot_status(self):
        """Get emulator boot status"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.adb_device, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            boot_completed = result.stdout.strip() == "1"
            
            # Get additional info
            device_info = {}
            if boot_completed:
                # Get device model
                model_result = subprocess.run(
                    ["adb", "-s", self.adb_device, "shell", "getprop", "ro.product.model"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                device_info["model"] = model_result.stdout.strip()
                
                # Get Android version
                version_result = subprocess.run(
                    ["adb", "-s", self.adb_device, "shell", "getprop", "ro.build.version.release"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                device_info["android_version"] = version_result.stdout.strip()
            
            return {
                "booted": boot_completed,
                "status": "ready" if boot_completed else "booting",
                "device_info": device_info
            }
        except Exception as e:
            logger.error(f"Failed to get boot status: {e}")
            return {
                "booted": False,
                "status": "error",
                "error": str(e)
            }

streamer = EmulatorStreamer()

@app.on_event("startup")
async def startup_event():
    """Connect to emulator on startup"""
    await streamer.connect()

@app.get("/")
async def root():
    """Root endpoint with web viewer"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PlayMetric Emulator Stream</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #1a1a1a;
                color: #fff;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                color: #4CAF50;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                background: #333;
            }
            .status.ready {
                background: #2e7d32;
            }
            .status.booting {
                background: #f57c00;
            }
            .status.error {
                background: #c62828;
            }
            #screen {
                border: 2px solid #4CAF50;
                border-radius: 10px;
                max-width: 100%;
                height: auto;
                background: #000;
            }
            .info {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
                margin: 20px 0;
            }
            .info-card {
                background: #333;
                padding: 15px;
                border-radius: 5px;
            }
            .info-card h3 {
                margin: 0 0 10px 0;
                color: #4CAF50;
            }
            .loading {
                text-align: center;
                padding: 40px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 PlayMetric Emulator Live Stream</h1>
            <div id="status" class="status">Checking status...</div>
            
            <div class="info">
                <div class="info-card">
                    <h3>Stream FPS</h3>
                    <p id="fps">3 FPS</p>
                </div>
                <div class="info-card">
                    <h3>Device Model</h3>
                    <p id="model">-</p>
                </div>
                <div class="info-card">
                    <h3>Android Version</h3>
                    <p id="version">-</p>
                </div>
                <div class="info-card">
                    <h3>Connection</h3>
                    <p id="connection">Connecting...</p>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <h2>📱 Waiting for emulator boot...</h2>
            </div>
            
            <img id="screen" style="display:none;" />
        </div>
        
        <script>
            const statusEl = document.getElementById('status');
            const screenEl = document.getElementById('screen');
            const loadingEl = document.getElementById('loading');
            const connectionEl = document.getElementById('connection');
            const modelEl = document.getElementById('model');
            const versionEl = document.getElementById('version');
            
            let ws = null;
            let reconnectAttempts = 0;
            
            async function checkStatus() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    statusEl.textContent = `Status: ${data.status}`;
                    statusEl.className = `status ${data.status}`;
                    
                    if (data.booted) {
                        loadingEl.style.display = 'none';
                        screenEl.style.display = 'block';
                        connectWebSocket();
                        
                        if (data.device_info) {
                            modelEl.textContent = data.device_info.model || '-';
                            versionEl.textContent = data.device_info.android_version || '-';
                        }
                    } else {
                        setTimeout(checkStatus, 2000);
                    }
                } catch (error) {
                    console.error('Status check failed:', error);
                    statusEl.textContent = 'Connection error';
                    statusEl.className = 'status error';
                    setTimeout(checkStatus, 5000);
                }
            }
            
            function connectWebSocket() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    return;
                }
                
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/stream`);
                
                ws.onopen = () => {
                    console.log('WebSocket connected');
                    connectionEl.textContent = 'Connected';
                    connectionEl.style.color = '#4CAF50';
                    reconnectAttempts = 0;
                };
                
                ws.onmessage = (event) => {
                    screenEl.src = 'data:image/png;base64,' + event.data;
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    connectionEl.textContent = 'Error';
                    connectionEl.style.color = '#f44336';
                };
                
                ws.onclose = () => {
                    console.log('WebSocket closed');
                    connectionEl.textContent = 'Reconnecting...';
                    connectionEl.style.color = '#ff9800';
                    
                    reconnectAttempts++;
                    const delay = Math.min(5000, 1000 * reconnectAttempts);
                    setTimeout(connectWebSocket, delay);
                };
            }
            
            checkStatus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/status")
async def get_status():
    """Get emulator boot status"""
    if not streamer.connected:
        await streamer.connect()
    
    status = await streamer.get_boot_status()
    return status

@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming screenshots"""
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        if not streamer.connected:
            await streamer.connect()
        
        while True:
            screenshot = await streamer.capture_screenshot()
            
            if screenshot:
                # Convert to base64
                base64_image = base64.b64encode(screenshot).decode('utf-8')
                await websocket.send_text(base64_image)
            
            await asyncio.sleep(FRAME_DELAY)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

@app.get("/screenshot")
async def get_screenshot():
    """Get single screenshot"""
    if not streamer.connected:
        await streamer.connect()
    
    screenshot = await streamer.capture_screenshot()
    
    if screenshot:
        return StreamingResponse(
            io.BytesIO(screenshot),
            media_type="image/png"
        )
    else:
        return {"error": "Failed to capture screenshot"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected": streamer.connected,
        "fps": FPS
    }
