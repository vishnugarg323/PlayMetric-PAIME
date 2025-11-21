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
current_device: Optional[str] = None  # Currently connected device ID

# Default configuration (can be overridden per session)
DEFAULT_EMULATOR_HOST = os.getenv("EMULATOR_HOST", "host.docker.internal")
DEFAULT_EMULATOR_PORT = os.getenv("EMULATOR_PORT", "5555")


# Pydantic models
class DeviceConfig(BaseModel):
    """Device configuration for connecting to physical device or emulator"""
    device_mode: str  # 'physical' or 'emulator'
    device_ip: Optional[str] = None  # For physical devices
    emulator_name: Optional[str] = None  # For emulators (e.g., 'emulator-5554')
    port: int = 5555

class InstallAPKRequest(BaseModel):
    apk_path: str
    device_id: Optional[str] = None  # Optional: target specific device

class LaunchAppRequest(BaseModel):
    package_name: str
    activity: Optional[str] = None
    device_id: Optional[str] = None  # Optional: target specific device

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


def get_adb_base_command(device_id: Optional[str] = None) -> list[str]:
    """
    Get base ADB command with device selector if needed
    
    Args:
        device_id: Specific device ID to target, or None to use current_device
    """
    global current_device
    
    target_device = device_id or current_device
    
    if target_device:
        return ['adb', '-s', target_device]
    else:
        # No device specified - use first available
        return ['adb']


def run_adb_command(command: list[str], timeout: int = 30, device_id: Optional[str] = None) -> str:
    """
    Run ADB command and return output
    
    Args:
        command: ADB command arguments (without 'adb' prefix)
        timeout: Command timeout in seconds
        device_id: Specific device ID to target
    """
    try:
        adb_cmd = get_adb_base_command(device_id) + command
        logger.debug(f"Running ADB command: {' '.join(adb_cmd)}")
        result = subprocess.run(
            adb_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        logger.debug(f"ADB command output: {result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"ADB command failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"ADB command failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"ADB command timed out: {command}")
        raise HTTPException(status_code=500, detail="ADB command timed out")


async def connect_device(config: DeviceConfig) -> dict:
    """
    Connect to a device (physical or emulator) based on configuration
    
    Args:
        config: Device configuration specifying mode and connection details
        
    Returns:
        dict with device info and connection status
    """
    global current_device
    
    try:
        if config.device_mode == 'physical':
            # Physical device - handle both direct IP and USB-connected devices
            
            # Disconnect any existing connections first
            if current_device:
                try:
                    subprocess.run(['adb', 'disconnect', current_device], 
                                 capture_output=True, timeout=5)
                    logger.info(f"Disconnected previous device: {current_device}")
                except:
                    pass
            
            # If device_ip is provided, connect directly via TCP
            if config.device_ip:
                device_address = f"{config.device_ip}:{config.port}"
                logger.info(f"Connecting to physical device via TCP: {device_address}")
                
                # Connect to the device
                result = subprocess.run(['adb', 'connect', device_address], 
                                      capture_output=True, text=True, timeout=15, check=True)
                
                # Wait for device to be ready
                for attempt in range(10):
                    await asyncio.sleep(2)
                    try:
                        boot_check = subprocess.run(
                            ['adb', '-s', device_address, 'shell', 'getprop', 'sys.boot_completed'],
                            capture_output=True, text=True, timeout=5
                        )
                        if boot_check.stdout.strip() == '1':
                            current_device = device_address
                            
                            # Get device info
                            model = subprocess.run(['adb', '-s', device_address, 'shell', 'getprop', 'ro.product.model'],
                                                 capture_output=True, text=True, timeout=5).stdout.strip()
                            android_version = subprocess.run(['adb', '-s', device_address, 'shell', 'getprop', 'ro.build.version.release'],
                                                            capture_output=True, text=True, timeout=5).stdout.strip()
                            
                            logger.info(f"✅ Connected to physical device: {model} (Android {android_version})")
                            return {
                                "status": "connected",
                                "device_id": device_address,
                                "device_mode": "physical",
                                "model": model,
                                "android_version": android_version,
                                "connection_output": result.stdout,
                                "connection_method": "tcp_direct"
                            }
                    except Exception as e:
                        logger.debug(f"Device not ready yet (attempt {attempt + 1}/10): {e}")
                
                raise HTTPException(status_code=500, detail="Device connected but not ready after 20 seconds")
            
            # No device_ip provided - Auto-detect USB-connected physical device and configure TCP access
            else:
                logger.info("🔍 Auto-detecting USB-connected physical device...")
                
                # First, try to get device IP from already TCP-connected devices
                devices_result = subprocess.run(['adb', 'devices'], 
                                              capture_output=True, text=True, timeout=5)
                
                # Check for TCP-connected devices first (format: IP:port)
                lines = devices_result.stdout.strip().split('\n')[1:]  # Skip header
                tcp_devices = []
                usb_devices = []
                
                for line in lines:
                    if '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        
                        # TCP devices have IP:port format
                        if ':' in device_id and not device_id.startswith('emulator-'):
                            tcp_devices.append(device_id)
                        # USB devices have serial numbers (not emulator-XXXX, not IP:port format)
                        elif not device_id.startswith('emulator-'):
                            usb_devices.append(device_id)
                
                # If we already have a TCP-connected device, use it
                if tcp_devices:
                    tcp_address = tcp_devices[0]
                    logger.info(f"📱 Found already TCP-connected device: {tcp_address}")
                    
                    # Get device info
                    try:
                        model = subprocess.run(['adb', '-s', tcp_address, 'shell', 'getprop', 'ro.product.model'],
                                             capture_output=True, text=True, timeout=5).stdout.strip()
                        android_version = subprocess.run(['adb', '-s', tcp_address, 'shell', 'getprop', 'ro.build.version.release'],
                                                        capture_output=True, text=True, timeout=5).stdout.strip()
                    except:
                        model = "Unknown"
                        android_version = "Unknown"
                    
                    current_device = tcp_address
                    
                    logger.info(f"✅ Using TCP-connected device: {model} (Android {android_version})")
                    return {
                        "status": "connected",
                        "device_id": tcp_address,
                        "device_mode": "physical",
                        "model": model,
                        "android_version": android_version,
                        "connection_method": "tcp_existing"
                    }
                
                # No TCP device found, look for USB device and configure it
                if not usb_devices:
                    raise HTTPException(
                        status_code=404,
                        detail="No physical device found. Please:\n"
                               "1. Connect device via USB, OR\n"
                               "2. Ensure device is already connected via TCP (run: adb tcpip 5555 && adb connect <DEVICE_IP>:5555)\n"
                               "3. Run 'adb devices' on host to verify connection"
                    )
                
                # Use first USB device - but we can't configure it from Docker!
                usb_device_id = usb_devices[0]
                logger.error(f"❌ Found USB device '{usb_device_id}' but cannot access USB from Docker container")
                
                raise HTTPException(
                    status_code=400,
                    detail=f"USB device detected ('{usb_device_id}') but Docker cannot access USB devices.\n\n"
                           f"Please run these commands on your HOST machine:\n"
                           f"1. adb -s {usb_device_id} tcpip 5555\n"
                           f"2. Get device IP: adb -s {usb_device_id} shell ip route | findstr src\n"
                           f"3. adb connect <DEVICE_IP>:5555\n\n"
                           f"OR use the automated script:\n"
                           f"   .\\setup-physical-device.ps1\n\n"
                           f"Then try creating the session again."
                )
            
        elif config.device_mode == 'emulator':
            # Android Studio emulator or local emulator
            # First try to connect to host's emulator via host.docker.internal
            host_emulator = f"{DEFAULT_EMULATOR_HOST}:{DEFAULT_EMULATOR_PORT}"
            
            logger.info(f"Attempting to connect to host emulator at {host_emulator}")
            
            # Disconnect previous device
            if current_device:
                try:
                    subprocess.run(['adb', 'disconnect', current_device], 
                                 capture_output=True, timeout=5)
                    logger.info(f"Disconnected previous device: {current_device}")
                except:
                    pass
            
            # Try to connect to host emulator
            try:
                connect_result = subprocess.run(['adb', 'connect', host_emulator], 
                                              capture_output=True, text=True, timeout=10)
                logger.info(f"ADB connect result: {connect_result.stdout}")
                
                # Wait a bit for connection to establish
                await asyncio.sleep(2)
                
                # Check if device is responding
                devices_result = subprocess.run(['adb', 'devices'], 
                                              capture_output=True, text=True, timeout=5)
                
                # Check if host emulator is connected
                if host_emulator in devices_result.stdout and 'device' in devices_result.stdout:
                    current_device = host_emulator
                    
                    # Get emulator info
                    try:
                        model = subprocess.run(['adb', '-s', host_emulator, 'shell', 'getprop', 'ro.product.model'],
                                             capture_output=True, text=True, timeout=5).stdout.strip()
                        android_version = subprocess.run(['adb', '-s', host_emulator, 'shell', 'getprop', 'ro.build.version.release'],
                                                        capture_output=True, text=True, timeout=5).stdout.strip()
                    except:
                        model = "Android Emulator"
                        android_version = "Unknown"
                    
                    logger.info(f"✅ Connected to host emulator: {model} (Android {android_version})")
                    return {
                        "status": "connected",
                        "device_id": host_emulator,
                        "device_mode": "emulator",
                        "model": model,
                        "android_version": android_version,
                        "connection_type": "host_emulator"
                    }
            except Exception as e:
                logger.warning(f"Failed to connect to host emulator: {e}")
            
            # Fallback: Check for already running emulators (emulator-XXXX)
            logger.info("Checking for running emulator instances...")
            devices_result = subprocess.run(['adb', 'devices'], 
                                          capture_output=True, text=True, timeout=5)
            
            # Parse available emulators
            lines = devices_result.stdout.strip().split('\n')[1:]  # Skip header
            emulators = [line.split('\t')[0] for line in lines if 'emulator-' in line and '\tdevice' in line]
            
            if not emulators:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No emulators found. Please start an emulator first:\n"
                           f"1. Start Android Studio emulator on host machine\n"
                           f"2. Ensure emulator is accessible at {DEFAULT_EMULATOR_HOST}:{DEFAULT_EMULATOR_PORT}\n"
                           f"3. On host, run: adb devices (should show emulator-XXXX)\n"
                           f"Available devices: {devices_result.stdout}"
                )
            
            # Use specified emulator or first available
            if config.emulator_name:
                if config.emulator_name not in emulators:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Emulator '{config.emulator_name}' not found. Available: {emulators}"
                    )
                target_emulator = config.emulator_name
            else:
                target_emulator = emulators[0]
            
            current_device = target_emulator
            
            # Get emulator info
            model = subprocess.run(['adb', '-s', target_emulator, 'shell', 'getprop', 'ro.product.model'],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
            android_version = subprocess.run(['adb', '-s', target_emulator, 'shell', 'getprop', 'ro.build.version.release'],
                                            capture_output=True, text=True, timeout=5).stdout.strip()
            
            logger.info(f"✅ Connected to emulator: {target_emulator} ({model}, Android {android_version})")
            return {
                "status": "connected",
                "device_id": target_emulator,
                "device_mode": "emulator",
                "model": model,
                "android_version": android_version,
                "available_emulators": emulators,
                "connection_type": "local_emulator"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Invalid device_mode: {config.device_mode}. Must be 'physical' or 'emulator'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect device: {e}")
        raise HTTPException(status_code=500, detail=f"Device connection failed: {str(e)}")


async def wait_for_device(timeout: int = 120, device_id: Optional[str] = None) -> bool:
    """
    Wait for Android device to be ready
    
    Args:
        timeout: Maximum time to wait in seconds
        device_id: Specific device ID to wait for, or None to use current_device
        
    Returns:
        bool: True if device is ready, False otherwise
    """
    global current_device
    target_device = device_id or current_device
    
    if not target_device:
        logger.warning("No device specified to wait for")
        return False
    
    logger.info(f"Waiting for device {target_device} to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if device is ready
            adb_cmd = get_adb_base_command(target_device) + ['shell', 'getprop', 'sys.boot_completed']
            result = subprocess.run(adb_cmd, capture_output=True, text=True, timeout=10)
            
            if result.stdout.strip() == '1':
                logger.info(f"✅ Device {target_device} is ready!")
                return True
        except Exception as e:
            logger.debug(f"Device not ready yet: {e}")
        
        await asyncio.sleep(5)
    
    logger.error(f"Device {target_device} not ready after {timeout}s")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_manager, current_device
    
    logger.info("Starting Emulator Manager Service...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.connect()
    logger.info("Database connected")
    
    # Auto-detect and connect physical devices and emulators on startup
    logger.info("🔍 Auto-detecting devices on host machine...")
    
    try:
        # Check what devices are on the host via adb (uses host.docker.internal ADB server)
        # Note: This sees host's ADB server through Docker bridge
        devices_on_host = []
        
        # Try multiple common device IPs that might be connected
        common_ips = [
            f"{DEFAULT_EMULATOR_HOST}:{DEFAULT_EMULATOR_PORT}",  # Emulator
            "192.168.0.80:5555",  # Physical device (your IP)
            "192.168.1.100:5555",  # Common router IP range
        ]
        
        for device_addr in common_ips:
            try:
                logger.info(f"Trying to connect to {device_addr}...")
                connect_result = subprocess.run(
                    ['adb', 'connect', device_addr],
                    capture_output=True, text=True, timeout=5
                )
                
                if 'connected' in connect_result.stdout.lower() or 'already connected' in connect_result.stdout.lower():
                    logger.info(f"✅ Connected to {device_addr}")
                    devices_on_host.append(device_addr)
                    await asyncio.sleep(1)  # Give time for connection to stabilize
                    
            except Exception as e:
                logger.debug(f"Could not connect to {device_addr}: {e}")
        
        # Now check all connected devices
        await asyncio.sleep(2)
        devices_check = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        logger.info(f"📱 Devices after auto-connect:\n{devices_check.stdout}")
        
        # Count connected devices
        lines = devices_check.stdout.strip().split('\n')[1:]
        connected_count = sum(1 for line in lines if line.strip() and '\tdevice' in line)
        
        if connected_count > 0:
            logger.info(f"✅ {connected_count} device(s) ready for sessions")
        else:
            logger.info("⚠️  No devices auto-connected. Will try to connect when session starts.")
            
    except Exception as e:
        logger.warning(f"Auto-device detection failed: {e}")
        logger.info("Devices will be connected when session is created")
    
    logger.info("✅ Emulator Manager Service ready")
    
    yield
    
    logger.info("Shutting down Emulator Manager Service...")
    
    # Disconnect all devices on shutdown
    if current_device:
        try:
            subprocess.run(['adb', 'disconnect', current_device], 
                         capture_output=True, timeout=5)
            logger.info(f"Disconnected device: {current_device}")
        except:
            pass
    
    if db_manager:
        await db_manager.disconnect()


app = FastAPI(title="Emulator Manager", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """
    Health check endpoint - Always returns 200 OK if service is running.
    Device connection status is informational only and does not affect health.
    This prevents the container from showing as 'unhealthy' when device is not connected.
    """
    global current_device
    
    device_info = {
        "status": "healthy",
        "service": "running",
        "timestamp": time.time(),
        "current_device": current_device
    }
    
    try:
        # Try to check ADB server status
        result = subprocess.run(
            ['adb', 'devices'], 
            capture_output=True, 
            text=True, 
            timeout=3
        )
        
        # Parse adb devices output to check for actual devices
        lines = result.stdout.strip().split('\n')
        devices = [line.split('\t')[0] for line in lines[1:] if '\tdevice' in line]
        
        device_info.update({
            "adb_server": "running",
            "devices_available": len(devices),
            "device_list": devices,
            "device_connected": current_device is not None,
            "message": "Ready for device connections" if not current_device else f"Connected to {current_device}"
        })
        
        # Check if current device is still connected
        if current_device:
            if current_device in devices:
                try:
                    boot_check = subprocess.run(
                        get_adb_base_command(current_device) + ['shell', 'getprop', 'sys.boot_completed'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    device_ready = boot_check.stdout.strip() == '1'
                    device_info["current_device_ready"] = device_ready
                except:
                    device_info["current_device_ready"] = False
            else:
                device_info["current_device_ready"] = False
                device_info["message"] = f"Warning: Current device {current_device} disconnected"
            
    except subprocess.TimeoutExpired:
        device_info.update({
            "adb_server": "timeout",
            "devices_available": 0,
            "message": "ADB server timeout (service healthy, check ADB configuration)"
        })
    except Exception as e:
        logger.debug(f"Health check device query failed (non-critical): {e}")
        device_info.update({
            "adb_server": "error",
            "devices_available": 0,
            "error_detail": str(e),
            "message": "Cannot query devices (service healthy, may need device connection)"
        })
    
    # Always return 200 OK - service is running
    return device_info


@app.post("/device/connect")
async def connect_to_device(config: DeviceConfig):
    """
    Connect to a device (physical or emulator) based on configuration.
    This should be called when starting a new session.
    
    Example for physical device:
    {
        "device_mode": "physical",
        "device_ip": "192.168.1.100",
        "port": 5555
    }
    
    Example for emulator:
    {
        "device_mode": "emulator",
        "emulator_name": "emulator-5554"  // optional, will use first available if not specified
    }
    """
    return await connect_device(config)


@app.post("/device/disconnect")
async def disconnect_device(device_id: Optional[str] = None):
    """
    Disconnect from current device or specific device
    
    Args:
        device_id: Specific device to disconnect, or None to disconnect current device
    """
    global current_device
    
    target = device_id or current_device
    
    if not target:
        return {"status": "no_device", "message": "No device connected"}
    
    try:
        subprocess.run(['adb', 'disconnect', target], 
                     capture_output=True, timeout=10, check=True)
        
        if target == current_device:
            current_device = None
        
        logger.info(f"Disconnected device: {target}")
        return {"status": "disconnected", "device": target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


@app.get("/devices/available")
async def list_available_devices():
    """
    List all available devices (both emulators and physical devices)
    Includes USB-connected devices, TCP-connected devices, and emulators
    """
    try:
        result = subprocess.run(['adb', 'devices', '-l'], 
                              capture_output=True, text=True, timeout=5)
        
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        devices = []
        emulator_count = 0
        physical_count = 0
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check if line contains 'device' status anywhere (handles tabs/multiple spaces)
            if '\tdevice' not in line and ' device ' not in line:
                continue
                
            parts = line.split()
            if len(parts) < 2:
                continue
                
            device_id = parts[0]
            device_status = parts[1] if len(parts) > 1 else ''
            
            # Only include devices with 'device' status (not 'offline', 'unauthorized', etc.)
            if device_status != 'device':
                continue
            
            # Determine device type
            is_emulator = 'emulator-' in device_id
            # TCP connections (IP:port) or USB serial numbers
            is_tcp = ':' in device_id
            is_usb = not is_emulator and not is_tcp
            
            if is_emulator:
                device_mode = 'emulator'
                connection_type = 'local'
                emulator_count += 1
            elif is_tcp:
                device_mode = 'physical'
                connection_type = 'tcp'
                physical_count += 1
            else:  # USB
                device_mode = 'physical'
                connection_type = 'usb'
                physical_count += 1
            
            # Parse additional info
            info = {
                "device_id": device_id,
                "device_mode": device_mode,
                "connection_type": connection_type,
                "status": "available",
                "ready_for_docker": is_tcp or is_emulator  # USB devices need TCP conversion
            }
            
            # Extract model and product if available from adb output
            for part in parts[2:]:  # Skip device_id and status
                if ':' in part:
                    key, value = part.split(':', 1)
                    info[key] = value
            
            # Try to get more details via ADB
            try:
                model = subprocess.run(['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
                                     capture_output=True, text=True, timeout=2).stdout.strip()
                android_ver = subprocess.run(['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'],
                                            capture_output=True, text=True, timeout=2).stdout.strip()
                cpu_abi = subprocess.run(['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.cpu.abi'],
                                        capture_output=True, text=True, timeout=2).stdout.strip()
                
                info['model'] = model
                info['android_version'] = android_ver
                info['cpu_architecture'] = cpu_abi
                
                # Add helpful note for USB devices
                if connection_type == 'usb':
                    info['note'] = 'Will be automatically configured for TCP access when session starts'
                    
            except Exception as e:
                logger.debug(f"Could not get full device info for {device_id}: {e}")
                pass
            
            devices.append(info)
        
        return {
            "total_devices": len(devices),
            "emulators": emulator_count,
            "physical_devices": physical_count,
            "devices": devices,
            "current_device": current_device,
            "note": "USB-connected physical devices will be automatically configured for TCP access during session creation"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")


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
        logger.info(f"🎯 Executing ADB TAP: adb shell input tap {request.x} {request.y}")
        output = run_adb_command(['shell', 'input', 'tap', str(request.x), str(request.y)])
        logger.info(f"✅ ADB TAP executed successfully. Output: {output}")
        return {"status": "success", "action": "tap", "x": request.x, "y": request.y}
    except Exception as e:
        logger.error(f"❌ ADB TAP FAILED: {e}")
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
    """Capture screenshot from emulator and return the image"""
    try:
        # Capture screenshot to device
        run_adb_command(['shell', 'screencap', '/sdcard/screenshot.png'])
        
        # Pull screenshot
        timestamp = int(time.time())
        local_path = f"/tmp/screenshot_{timestamp}.png"
        run_adb_command(['pull', '/sdcard/screenshot.png', local_path])
        
        # Return the actual image file
        from fastapi.responses import FileResponse
        return FileResponse(local_path, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screenshot/info")
async def get_screenshot_info():
    """Get screenshot metadata (path and timestamp)"""
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


@app.get("/device/screen-size")
async def get_screen_size():
    """Get device screen dimensions (width x height)"""
    try:
        # Get display size
        # Output format:
        # "Physical size: 1440x3200"
        # OR
        # "Physical size: 1440x3200\nOverride size: 1080x2400"
        display_size = run_adb_command(['shell', 'wm', 'size'])
        
        # Parse the output - prefer Override size if present (that's what apps see)
        if "Override size:" in display_size:
            size_str = display_size.split("Override size:")[1].strip()
        elif "Physical size:" in display_size:
            size_str = display_size.split("Physical size:")[1].strip()
            # Remove any trailing newlines or additional text
            size_str = size_str.split('\n')[0].strip()
        else:
            size_str = display_size.strip()
        
        # Extract width and height
        width, height = map(int, size_str.split('x'))
        
        logger.info(f"📱 Device screen size: {width}x{height} (from: {display_size.strip()})")
        
        return {
            "width": width,
            "height": height,
            "raw_output": display_size
        }
    except Exception as e:
        logger.error(f"Failed to get screen size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/device/info")
async def get_device_info(device_id: Optional[str] = None):
    """
    Get device information for current device or specific device
    
    Args:
        device_id: Optional specific device ID. If not provided, uses current_device
    """
    global current_device
    
    target = device_id or current_device
    
    if not target:
        raise HTTPException(
            status_code=400, 
            detail="No device connected. Please connect a device first using POST /device/connect"
        )
    
    try:
        info = {
            "device": target,
            "is_current_device": target == current_device,
            "android_version": run_adb_command(['shell', 'getprop', 'ro.build.version.release'], device_id=target),
            "sdk_version": run_adb_command(['shell', 'getprop', 'ro.build.version.sdk'], device_id=target),
            "manufacturer": run_adb_command(['shell', 'getprop', 'ro.product.manufacturer'], device_id=target),
            "model": run_adb_command(['shell', 'getprop', 'ro.product.model'], device_id=target),
            "display_size": run_adb_command(['shell', 'wm', 'size'], device_id=target),
            "boot_completed": run_adb_command(['shell', 'getprop', 'sys.boot_completed'], device_id=target)
        }
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device info: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8005"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
