from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import os
import logging
import requests
import base64
import time
from typing import Optional, Dict, Any
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PlayMetric Cloud Device Adapter")

class DeviceProvider(str, Enum):
    BROWSERSTACK = "browserstack"
    AWS = "aws"
    FIREBASE = "firebase"

# Configuration
DEVICE_PROVIDER = os.getenv("DEVICE_PROVIDER", "browserstack")
BROWSERSTACK_USERNAME = os.getenv("BROWSERSTACK_USERNAME", "")
BROWSERSTACK_ACCESS_KEY = os.getenv("BROWSERSTACK_ACCESS_KEY", "")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEVICE_FARM_PROJECT_ARN = os.getenv("AWS_DEVICE_FARM_PROJECT_ARN", "")

class BrowserStackAdapter:
    """BrowserStack App Automate adapter"""
    
    def __init__(self, username: str, access_key: str):
        self.username = username
        self.access_key = access_key
        self.base_url = "https://api-cloud.browserstack.com/app-automate/v2"
        self.auth = (username, access_key)
        self.current_session = None
    
    def upload_app(self, apk_path: str) -> str:
        """Upload APK to BrowserStack"""
        url = f"{self.base_url}/upload"
        
        with open(apk_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files, auth=self.auth)
        
        if response.status_code == 200:
            app_url = response.json().get('app_url')
            logger.info(f"APK uploaded to BrowserStack: {app_url}")
            return app_url
        else:
            raise Exception(f"Failed to upload APK: {response.text}")
    
    def start_session(self, app_url: str, device_config: Dict[str, Any]) -> str:
        """Start a new device session"""
        capabilities = {
            "deviceName": device_config.get("device_name", "Samsung Galaxy S22"),
            "platformVersion": device_config.get("platform_version", "12.0"),
            "platformName": "Android",
            "app": app_url,
            "browserstack.debug": True,
            "browserstack.networkLogs": True,
            "browserstack.appiumLogs": True,
            "project": "PlayMetric",
            "build": f"Build_{int(time.time())}",
        }
        
        # Create Appium session
        url = f"https://{self.username}:{self.access_key}@hub-cloud.browserstack.com/wd/hub/session"
        response = requests.post(
            url,
            json={"capabilities": {"alwaysMatch": capabilities}},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data.get('value', {}).get('sessionId')
            self.current_session = session_id
            logger.info(f"BrowserStack session started: {session_id}")
            return session_id
        else:
            raise Exception(f"Failed to start session: {response.text}")
    
    def take_screenshot(self, session_id: str) -> bytes:
        """Capture screenshot from device"""
        url = f"https://{self.username}:{self.access_key}@hub-cloud.browserstack.com/wd/hub/session/{session_id}/screenshot"
        response = requests.get(url)
        
        if response.status_code == 200:
            screenshot_base64 = response.json().get('value')
            return base64.b64decode(screenshot_base64)
        else:
            raise Exception(f"Failed to capture screenshot: {response.text}")
    
    def perform_action(self, session_id: str, action_type: str, params: Dict[str, Any]) -> bool:
        """Perform action on device (tap, swipe, etc.)"""
        url = f"https://{self.username}:{self.access_key}@hub-cloud.browserstack.com/wd/hub/session/{session_id}"
        
        if action_type == "tap":
            # Perform tap action
            tap_url = f"{url}/element"
            response = requests.post(
                tap_url,
                json={
                    "using": "xpath",
                    "value": f"//*[@bounds='[{params['x']},{params['y']}][{params['x']+10},{params['y']+10}]']"
                }
            )
            
            if response.status_code == 200:
                element_id = response.json().get('value', {}).get('ELEMENT')
                click_url = f"{url}/element/{element_id}/click"
                requests.post(click_url)
                return True
        
        elif action_type == "swipe":
            # Perform swipe action
            actions_url = f"{url}/actions"
            response = requests.post(
                actions_url,
                json={
                    "actions": [{
                        "type": "pointer",
                        "id": "finger1",
                        "parameters": {"pointerType": "touch"},
                        "actions": [
                            {"type": "pointerMove", "duration": 0, "x": params['start_x'], "y": params['start_y']},
                            {"type": "pointerDown", "button": 0},
                            {"type": "pointerMove", "duration": params.get('duration', 500), "x": params['end_x'], "y": params['end_y']},
                            {"type": "pointerUp", "button": 0}
                        ]
                    }]
                }
            )
            return response.status_code == 200
        
        return False
    
    def stop_session(self, session_id: str):
        """Stop device session"""
        url = f"https://{self.username}:{self.access_key}@hub-cloud.browserstack.com/wd/hub/session/{session_id}"
        response = requests.delete(url)
        
        if response.status_code == 200:
            logger.info(f"BrowserStack session stopped: {session_id}")
        else:
            logger.error(f"Failed to stop session: {response.text}")
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status and metadata"""
        url = f"{self.base_url}/sessions/{session_id}.json"
        response = requests.get(url, auth=self.auth)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": response.text}


# Initialize adapter based on provider
if DEVICE_PROVIDER == DeviceProvider.BROWSERSTACK:
    if not BROWSERSTACK_USERNAME or not BROWSERSTACK_ACCESS_KEY:
        logger.warning("BrowserStack credentials not provided. Set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY environment variables.")
        adapter = None
    else:
        adapter = BrowserStackAdapter(BROWSERSTACK_USERNAME, BROWSERSTACK_ACCESS_KEY)
        logger.info("✅ BrowserStack adapter initialized")
else:
    adapter = None
    logger.warning(f"Device provider '{DEVICE_PROVIDER}' not yet implemented. Only 'browserstack' is currently supported.")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PlayMetric Cloud Device Adapter",
        "provider": DEVICE_PROVIDER,
        "status": "ready" if adapter else "not_configured"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "provider": DEVICE_PROVIDER,
        "configured": adapter is not None
    }

@app.post("/upload-app")
async def upload_app(file: UploadFile = File(...)):
    """Upload APK to cloud provider"""
    if not adapter:
        raise HTTPException(status_code=503, detail="Device adapter not configured")
    
    try:
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Upload to cloud provider
        app_url = adapter.upload_app(temp_path)
        
        # Cleanup
        os.remove(temp_path)
        
        return {
            "success": True,
            "app_url": app_url,
            "filename": file.filename
        }
    
    except Exception as e:
        logger.error(f"Failed to upload app: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-session")
async def start_session(
    app_url: str,
    device_name: str = "Samsung Galaxy S22",
    platform_version: str = "12.0"
):
    """Start a new device session"""
    if not adapter:
        raise HTTPException(status_code=503, detail="Device adapter not configured")
    
    try:
        device_config = {
            "device_name": device_name,
            "platform_version": platform_version
        }
        
        session_id = adapter.start_session(app_url, device_config)
        
        return {
            "success": True,
            "session_id": session_id,
            "device_name": device_name,
            "platform_version": platform_version
        }
    
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screenshot/{session_id}")
async def get_screenshot(session_id: str):
    """Get screenshot from device session"""
    if not adapter:
        raise HTTPException(status_code=503, detail="Device adapter not configured")
    
    try:
        screenshot_bytes = adapter.take_screenshot(session_id)
        
        # Return as base64
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        return {
            "success": True,
            "screenshot": screenshot_base64,
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Failed to get screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/action/{session_id}")
async def perform_action(
    session_id: str,
    action_type: str,
    params: Dict[str, Any]
):
    """Perform action on device"""
    if not adapter:
        raise HTTPException(status_code=503, detail="Device adapter not configured")
    
    try:
        success = adapter.perform_action(session_id, action_type, params)
        
        return {
            "success": success,
            "action_type": action_type,
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Failed to perform action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def stop_session(session_id: str):
    """Stop device session"""
    if not adapter:
        raise HTTPException(status_code=503, detail="Device adapter not configured")
    
    try:
        adapter.stop_session(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session stopped"
        }
    
    except Exception as e:
        logger.error(f"Failed to stop session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session-status/{session_id}")
async def get_session_status(session_id: str):
    """Get session status and metadata"""
    if not adapter:
        raise HTTPException(status_code=503, detail="Device adapter not configured")
    
    try:
        status = adapter.get_session_status(session_id)
        
        return {
            "success": True,
            "status": status
        }
    
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
