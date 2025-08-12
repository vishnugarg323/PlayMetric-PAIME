import asyncio
import aiohttp
import numpy as np
from typing import Dict, Optional, Tuple
import cv2
import time
import logging
import base64
from PIL import Image
import io

logger = logging.getLogger(__name__)

class GameEnvironment:
    def __init__(self, device_serial: Optional[str] = None):
        self.api_url = "http://emulator:5555"
        self.package_name = None
        self.connected = False
        self.screen_size = (1080, 1920)
        
    async def connect(self):
        """Connect to mock emulator"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/") as resp:
                    if resp.status == 200:
                        self.connected = True
                        logger.info("Connected to mock emulator")
                    else:
                        raise Exception("Failed to connect to emulator")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def install_apk(self, package_name: str, game_name: str, apk_path: str = None) -> Dict:
        """Install APK in emulator"""
        if not self.connected:
            await self.connect()
        
        try:
            async with aiohttp.ClientSession() as session:
                install_data = {
                    "package_name": package_name,
                    "game_name": game_name
                }
                if apk_path:
                    install_data["apk_path"] = apk_path
                    
                async with session.post(
                    f"{self.api_url}/install-apk",
                    json=install_data
                ) as resp:
                    data = await resp.json()
                    logger.info(f"Installed APK: {data}")
                    return data
        except Exception as e:
            logger.error(f"Failed to install APK: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def launch_game(self, package_name: str) -> Dict:
        """Launch game application"""
        if not self.connected:
            await self.connect()
        
        self.package_name = package_name
        
        try:
            async with aiohttp.ClientSession() as session:
                # Use the correct endpoint and format for the enhanced emulator
                async with session.post(
                    f"{self.api_url}/launch-app",
                    json={"package_name": package_name}
                ) as resp:
                    data = await resp.json()
                    logger.info(f"Launched game: {data}")
            
            await asyncio.sleep(2)  # Wait for game to "load"
            
            return {
                'status': 'launched',
                'package': package_name
            }
        except Exception as e:
            logger.error(f"Failed to launch game: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    async def get_screenshot(self) -> Optional[np.ndarray]:
        """Capture current screen"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/screenshot") as resp:
                    data = await resp.json()
                    
                    # Decode base64 image - emulator returns 'screenshot' key
                    img_data = base64.b64decode(data['screenshot'])
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Convert to numpy array (BGR for OpenCV)
                    screen_array = np.array(img)
                    screen_bgr = cv2.cvtColor(screen_array, cv2.COLOR_RGB2BGR)
                    
                    return screen_bgr
                    
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    async def tap(self, x: int, y: int):
        """Perform tap action"""
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.api_url}/tap/{x}/{y}")
        await asyncio.sleep(0.1)
    
    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300):
        """Perform swipe action"""
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.api_url}/swipe/{x1}/{y1}/{x2}/{y2}")
        await asyncio.sleep(duration / 1000 + 0.1)
    
    async def press_back(self):
        """Press back button"""
        # Mock implementation
        await asyncio.sleep(0.1)
    
    async def check_crash(self) -> bool:
        """Check if app has crashed"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/check_crash") as resp:
                    data = await resp.json()
                    return data.get('crashed', False)
        except:
            return False
    
    async def get_memory_usage(self) -> Dict:
        """Get app memory usage"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/memory_usage") as resp:
                    return await resp.json()
        except:
            return {'total_pss': 0, 'native_heap': 0, 'dalvik_heap': 0}
    
    async def close(self):
        """Close the game"""
        logger.info("Closing game environment")