"""
ADB Controller - Handles all ADB interactions with the emulator
"""
import subprocess
import time
import logging
from typing import Tuple, Optional, List
import re

logger = logging.getLogger(__name__)


class ADBController:
    """Controls Android device via ADB"""
    
    def __init__(self, host: str = "emulator", port: int = 5555):
        self.host = host
        self.port = port
        self.device = f"{host}:{port}"
        self.connected = False
        
    def connect(self, retry_count: int = 5) -> bool:
        """Connect to ADB device"""
        for attempt in range(retry_count):
            try:
                # Connect to device
                result = subprocess.run(
                    ["adb", "connect", self.device],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if "connected" in result.stdout.lower():
                    self.connected = True
                    logger.info(f"Connected to {self.device}")
                    
                    # Wait for device to be ready
                    self.wait_for_device()
                    return True
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(5)
                
        logger.error(f"Failed to connect to {self.device}")
        return False
    
    def wait_for_device(self, timeout: int = 60):
        """Wait for device to be fully booted"""
        try:
            subprocess.run(
                ["adb", "-s", self.device, "wait-for-device"],
                timeout=timeout,
                check=True
            )
            
            # Wait for boot to complete
            for _ in range(timeout):
                result = subprocess.run(
                    ["adb", "-s", self.device, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "1" in result.stdout:
                    logger.info("Device fully booted")
                    return True
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error waiting for device: {e}")
            
        return False
    
    def take_screenshot(self, output_path: str) -> bool:
        """Capture screenshot from device"""
        try:
            # Capture to device storage
            device_path = "/sdcard/screen.png"
            
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "screencap", "-p", device_path],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error(f"Screenshot failed: {result.stderr}")
                return False
            
            # Pull to host
            result = subprocess.run(
                ["adb", "-s", self.device, "pull", device_path, output_path],
                capture_output=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
    
    def tap(self, x: int, y: int) -> bool:
        """Perform tap action"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "input", "tap", str(x), str(y)],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error performing tap: {e}")
            return False
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """Perform swipe action"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "input", "swipe", 
                 str(x1), str(y1), str(x2), str(y2), str(duration)],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error performing swipe: {e}")
            return False
    
    def press_key(self, keycode: str) -> bool:
        """Press a key (BACK, HOME, MENU, etc.)"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "input", "keyevent", keycode],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return False
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get device screen dimensions"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "wm", "size"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse output: "Physical size: 1080x1920"
            match = re.search(r'(\d+)x(\d+)', result.stdout)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                return width, height
                
        except Exception as e:
            logger.error(f"Error getting screen size: {e}")
            
        return 1080, 1920  # Default
    
    def install_apk(self, apk_path: str) -> bool:
        """Install APK on device"""
        try:
            logger.info(f"Installing APK: {apk_path}")
            result = subprocess.run(
                ["adb", "-s", self.device, "install", "-r", apk_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if "Success" in result.stdout:
                logger.info("APK installed successfully")
                return True
            else:
                logger.error(f"Installation failed: {result.stdout}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing APK: {e}")
            return False
    
    def launch_app(self, package_name: str) -> bool:
        """Launch application by package name"""
        try:
            # Get main activity
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "monkey", "-p", package_name, "-c", 
                 "android.intent.category.LAUNCHER", "1"],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Launched app: {package_name}")
                return True
            else:
                logger.error(f"Failed to launch app: {package_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error launching app: {e}")
            return False
    
    def stop_app(self, package_name: str) -> bool:
        """Force stop application"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "am", "force-stop", package_name],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error stopping app: {e}")
            return False
    
    def get_logcat(self, lines: int = 100) -> str:
        """Get recent logcat entries"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "logcat", "-d", "-t", str(lines)],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Error getting logcat: {e}")
            return ""
    
    def clear_logcat(self):
        """Clear logcat buffer"""
        try:
            subprocess.run(
                ["adb", "-s", self.device, "logcat", "-c"],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            logger.error(f"Error clearing logcat: {e}")
    
    def get_current_app(self) -> Optional[str]:
        """Get currently focused app package name"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "dumpsys", "window", "windows"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Find current focus
            for line in result.stdout.split('\n'):
                if 'mCurrentFocus' in line or 'mFocusedApp' in line:
                    match = re.search(r'([a-zA-Z0-9._]+)/([a-zA-Z0-9._]+)', line)
                    if match:
                        return match.group(1)
                        
        except Exception as e:
            logger.error(f"Error getting current app: {e}")
            
        return None
    
    def get_installed_packages(self) -> List[str]:
        """Get list of installed packages"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "shell", "pm", "list", "packages"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            packages = []
            for line in result.stdout.split('\n'):
                if line.startswith('package:'):
                    packages.append(line.replace('package:', '').strip())
                    
            return packages
            
        except Exception as e:
            logger.error(f"Error getting packages: {e}")
            return []
