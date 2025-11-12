"""
User Input Monitor - Detects and records user touch inputs
Uses ADB to monitor touch events from the device
"""
import asyncio
import logging
import re
from typing import Optional, Callable
import subprocess

logger = logging.getLogger(__name__)


class UserInputMonitor:
    """Monitors user touch inputs on Android device via ADB"""
    
    def __init__(self, device_id: str = None):
        """
        Initialize user input monitor
        
        Args:
            device_id: ADB device ID (e.g., "emulator-5554" or "192.168.0.80:5555")
        """
        self.device_id = device_id
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.callback: Optional[Callable] = None
        self.touch_device = None  # Will be detected automatically
        
    async def detect_touch_device(self) -> Optional[str]:
        """
        Detect the touch input device path
        
        Returns:
            Device path (e.g., "/dev/input/event2") or None
        """
        try:
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["shell", "getevent", "-lp"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse output to find touchscreen device
            lines = result.stdout.split('\n')
            current_device = None
            
            for line in lines:
                # Look for device path
                if line.startswith('add device'):
                    match = re.search(r'/dev/input/event\d+', line)
                    if match:
                        current_device = match.group(0)
                
                # Check if this device supports touch
                if current_device and ('ABS_MT_POSITION' in line or 'ABS_MT_TRACKING_ID' in line):
                    logger.info(f"✅ Detected touch device: {current_device}")
                    return current_device
            
            # Fallback: try common event devices
            for i in range(10):
                device_path = f"/dev/input/event{i}"
                logger.debug(f"Trying fallback device: {device_path}")
                return device_path  # Return first one as fallback
                
            logger.warning("Could not detect touch device, using /dev/input/event2 as default")
            return "/dev/input/event2"
            
        except Exception as e:
            logger.error(f"Error detecting touch device: {e}")
            return "/dev/input/event2"  # Default fallback
    
    async def start_monitoring(self, callback: Callable):
        """
        Start monitoring user touch inputs
        
        Args:
            callback: Async function called with (x, y, event_type) on touch events
        """
        if self.is_monitoring:
            logger.warning("Already monitoring user inputs")
            return
        
        # Detect touch device
        self.touch_device = await self.detect_touch_device()
        if not self.touch_device:
            logger.error("Failed to detect touch device")
            return
        
        self.callback = callback
        self.is_monitoring = True
        
        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info(f"👆 Started user input monitoring on {self.touch_device}")
    
    async def stop_monitoring(self):
        """Stop monitoring user inputs"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️  Stopped user input monitoring")
    
    async def _monitor_loop(self):
        """Main monitoring loop that reads getevent output"""
        try:
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["shell", "getevent", "-lt", self.touch_device])
            
            logger.info(f"📱 Starting getevent monitor: {' '.join(cmd)}")
            
            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Track current touch position
            current_x = None
            current_y = None
            touch_active = False
            
            # Read events line by line
            while self.is_monitoring and process.stdout:
                line = await process.stdout.readline()
                if not line:
                    break
                
                try:
                    line_str = line.decode('utf-8').strip()
                    
                    # Parse getevent output
                    # Format: [timestamp] device_path type code value
                    # Example: [   12345.678] /dev/input/event2 EV_ABS       ABS_MT_POSITION_X    000001a4
                    
                    if 'ABS_MT_POSITION_X' in line_str or 'ABS_X' in line_str:
                        # Extract X coordinate
                        match = re.search(r'([0-9a-f]+)$', line_str)
                        if match:
                            current_x = int(match.group(1), 16)
                    
                    elif 'ABS_MT_POSITION_Y' in line_str or 'ABS_Y' in line_str:
                        # Extract Y coordinate  
                        match = re.search(r'([0-9a-f]+)$', line_str)
                        if match:
                            current_y = int(match.group(1), 16)
                    
                    elif 'ABS_MT_TRACKING_ID' in line_str:
                        # Touch down/up event
                        match = re.search(r'([0-9a-f]+)$', line_str)
                        if match:
                            value = int(match.group(1), 16)
                            if value != 0xffffffff and not touch_active:
                                # Touch started
                                touch_active = True
                                logger.debug(f"👆 Touch down")
                            elif value == 0xffffffff and touch_active:
                                # Touch released - this is a tap!
                                touch_active = False
                                if current_x is not None and current_y is not None:
                                    logger.info(f"✅ User TAP detected: ({current_x}, {current_y})")
                                    
                                    # Call callback
                                    if self.callback:
                                        await self.callback(current_x, current_y, 'tap')
                    
                    elif 'BTN_TOUCH' in line_str:
                        # Alternative touch detection
                        match = re.search(r'([0-9a-f]+)$', line_str)
                        if match:
                            value = int(match.group(1), 16)
                            if value == 1 and not touch_active:
                                touch_active = True
                            elif value == 0 and touch_active:
                                touch_active = False
                                if current_x is not None and current_y is not None:
                                    logger.info(f"✅ User TAP detected (BTN): ({current_x}, {current_y})")
                                    if self.callback:
                                        await self.callback(current_x, current_y, 'tap')
                    
                except Exception as e:
                    logger.debug(f"Error parsing event line: {e}")
                    continue
            
            # Cleanup
            if process.returncode is None:
                process.kill()
                await process.wait()
                
        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
        finally:
            self.is_monitoring = False
    
    def get_status(self) -> dict:
        """Get current monitoring status"""
        return {
            'is_monitoring': self.is_monitoring,
            'touch_device': self.touch_device,
            'device_id': self.device_id
        }
