"""
Multi-Session Orchestration Manager
Manages parallel testing of multiple games and sessions with resource allocation
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
import logging
from dataclasses import dataclass
import sys
sys.path.append('/app/shared')
from database import DatabaseManager

logger = logging.getLogger(__name__)


class SessionPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ResourceType(Enum):
    EMULATOR = "emulator"
    CPU = "cpu"
    MEMORY = "memory"


@dataclass
class ResourceLimits:
    max_concurrent_sessions: int = 10
    max_emulator_instances: int = 5
    max_cpu_percent: float = 80.0
    max_memory_mb: int = 8192


@dataclass
class SessionResource:
    session_id: str
    emulator_id: Optional[str]
    cpu_percent: float
    memory_mb: int
    started_at: datetime


class SessionQueue:
    """Priority-based session queue"""
    
    def __init__(self):
        self.queues: Dict[SessionPriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in SessionPriority
        }
        self.session_priorities: Dict[str, SessionPriority] = {}
    
    async def enqueue(self, session_id: str, priority: SessionPriority = SessionPriority.NORMAL):
        """Add session to queue with priority"""
        self.session_priorities[session_id] = priority
        await self.queues[priority].put(session_id)
        logger.info(f"Session {session_id} enqueued with priority {priority.name}")
    
    async def dequeue(self) -> Optional[str]:
        """Dequeue highest priority session"""
        # Check queues from highest to lowest priority
        for priority in sorted(SessionPriority, key=lambda x: x.value, reverse=True):
            queue = self.queues[priority]
            if not queue.empty():
                session_id = await queue.get()
                return session_id
        return None
    
    def get_queue_size(self) -> Dict[str, int]:
        """Get size of each priority queue"""
        return {
            priority.name: self.queues[priority].qsize()
            for priority in SessionPriority
        }
    
    def remove(self, session_id: str):
        """Remove session from tracking"""
        if session_id in self.session_priorities:
            del self.session_priorities[session_id]


class ResourceManager:
    """Manages resource allocation for sessions"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.allocated_resources: Dict[str, SessionResource] = {}
        self.available_emulators: Set[str] = set()  # Will be populated dynamically
        self._lock = asyncio.Lock()
        self.last_device_scan = None
        self.device_scan_interval = 30  # Rescan devices every 30 seconds
    
    async def refresh_available_devices(self):
        """Scan and refresh list of available devices via emulator-manager service"""
        from datetime import datetime, timedelta
        
        # Only scan if we haven't scanned recently
        now = datetime.utcnow()
        if self.last_device_scan and (now - self.last_device_scan).total_seconds() < self.device_scan_interval:
            return
        
        try:
            # Use emulator-manager service to get available devices
            import httpx
            import os
            emulator_manager_url = os.getenv("EMULATOR_MANAGER_URL", "http://emulator-manager:8005")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{emulator_manager_url}/devices/available")
                
                if response.status_code == 200:
                    data = response.json()
                    devices = data.get('devices', [])
                    
                    # Track both emulators and physical devices
                    emulator_count = sum(1 for d in devices if d.get('device_mode') == 'emulator')
                    physical_count = sum(1 for d in devices if d.get('device_mode') == 'physical')
                    
                    self.last_device_scan = now
                    logger.info(f"🔍 Device scan: Found {len(devices)} devices ({emulator_count} emulators, {physical_count} physical)")
                    
                    if not devices:
                        logger.warning("⚠️ No devices found. Sessions will wait for devices to connect.")
                else:
                    logger.warning(f"Failed to scan devices: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error scanning devices: {e}")
    
    async def can_allocate(self) -> bool:
        """Check if resources available for new session"""
        # Refresh device list before checking (for monitoring purposes only)
        await self.refresh_available_devices()
        
        async with self._lock:
            if len(self.allocated_resources) >= self.limits.max_concurrent_sessions:
                return False
            
            # Check CPU usage
            total_cpu = sum(r.cpu_percent for r in self.allocated_resources.values())
            if total_cpu >= self.limits.max_cpu_percent:
                return False
            
            # Check memory usage
            total_memory = sum(r.memory_mb for r in self.allocated_resources.values())
            if total_memory >= self.limits.max_memory_mb:
                return False
            
            # Note: Device availability will be checked by emulator-manager during connection
            return True
    
    async def allocate(self, session_id: str, estimated_cpu: float = 10.0, estimated_memory: int = 512) -> Optional[SessionResource]:
        """Allocate resources for session"""
        # Refresh device list for monitoring (device assignment happens at connection time)
        await self.refresh_available_devices()
        
        async with self._lock:
            # Check allocation constraints without calling can_allocate() to avoid deadlock
            if len(self.allocated_resources) >= self.limits.max_concurrent_sessions:
                logger.warning(f"Cannot allocate: max concurrent sessions ({self.limits.max_concurrent_sessions}) reached")
                return None
            
            total_cpu = sum(r.cpu_percent for r in self.allocated_resources.values())
            if total_cpu >= self.limits.max_cpu_percent:
                logger.warning(f"Cannot allocate: CPU limit ({self.limits.max_cpu_percent}%) reached")
                return None
            
            total_memory = sum(r.memory_mb for r in self.allocated_resources.values())
            if total_memory >= self.limits.max_memory_mb:
                logger.warning(f"Cannot allocate: memory limit ({self.limits.max_memory_mb}MB) reached")
                return None
            
            # Note: Device assignment will happen automatically when session connects
            # based on device_mode (emulator/physical) in session config
            
            resource = SessionResource(
                session_id=session_id,
                emulator_id=None,  # Will be assigned at connection time
                cpu_percent=estimated_cpu,
                memory_mb=estimated_memory,
                started_at=datetime.utcnow()
            )
            
            self.allocated_resources[session_id] = resource
            logger.info(f"✅ Allocated resources for session {session_id} (device will be assigned at connection)")
            return resource
    
    async def deallocate(self, session_id: str):
        """Free resources from session"""
        async with self._lock:
            if session_id in self.allocated_resources:
                resource = self.allocated_resources[session_id]
                # Note: Device cleanup happens in emulator-manager
                del self.allocated_resources[session_id]
                logger.info(f"Deallocated resources for session {session_id}")
    
    def get_resource_usage(self) -> Dict:
        """Get current resource usage stats"""
        total_cpu = sum(r.cpu_percent for r in self.allocated_resources.values())
        total_memory = sum(r.memory_mb for r in self.allocated_resources.values())
        
        return {
            "active_sessions": len(self.allocated_resources),
            "max_sessions": self.limits.max_concurrent_sessions,
            "available_emulators": len(self.available_emulators),
            "total_emulators": self.limits.max_emulator_instances,
            "cpu_usage_percent": round(total_cpu, 2),
            "memory_usage_mb": total_memory,
            "memory_limit_mb": self.limits.max_memory_mb
        }


class MultiSessionOrchestrator:
    """Main orchestrator for managing multiple parallel sessions"""
    
    def __init__(self, db_manager: DatabaseManager, resource_limits: Optional[ResourceLimits] = None):
        self.db = db_manager
        self.resource_limits = resource_limits or ResourceLimits()
        self.queue = SessionQueue()
        self.resource_manager = ResourceManager(self.resource_limits)
        self.running_sessions: Dict[str, asyncio.Task] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the orchestrator"""
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Multi-session orchestrator started")
    
    async def stop(self):
        """Stop the orchestrator"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Stop all running sessions
        for task in self.running_sessions.values():
            task.cancel()
        
        logger.info("Multi-session orchestrator stopped")
    
    async def submit_session(self, session_id: str, game_id: str, version_id: str, 
                            config: Dict, priority: SessionPriority = SessionPriority.NORMAL):
        """Submit a new session for execution"""
        # Update session status in database
        await self.db.execute_write(
            "UPDATE sessions SET status = 'queued' WHERE id = $1",
            session_id
        )
        
        # Add to queue
        await self.queue.enqueue(session_id, priority)
        
        logger.info(f"Session {session_id} submitted for game {game_id}")
    
    async def cancel_session(self, session_id: str):
        """Cancel a queued or running session"""
        # Remove from queue
        self.queue.remove(session_id)
        
        # Cancel if running
        if session_id in self.running_sessions:
            task = self.running_sessions[session_id]
            task.cancel()
            await self.resource_manager.deallocate(session_id)
            del self.running_sessions[session_id]
        
        # Update status in database
        await self.db.execute_write(
            "UPDATE sessions SET status = 'stopped', completed_at = NOW() WHERE id = $1",
            session_id
        )
        
        logger.info(f"Session {session_id} cancelled")
    
    async def _scheduler_loop(self):
        """Main scheduling loop"""
        logger.info("Scheduler loop started")
        while self._running:
            try:
                # Check if we can start new session
                can_alloc = await self.resource_manager.can_allocate()
                logger.debug(f"Can allocate: {can_alloc}, Queue sizes: {self.queue.get_queue_size()}")
                
                if can_alloc:
                    # Get next session from queue
                    session_id = await self.queue.dequeue()
                    
                    if session_id:
                        logger.info(f"Dequeued session {session_id} for execution")
                        # Allocate resources
                        resource = await self.resource_manager.allocate(session_id)
                        
                        if resource:
                            logger.info(f"Resources allocated for session {session_id}: {resource}")
                            # Start session execution
                            task = asyncio.create_task(self._execute_session(session_id, resource))
                            self.running_sessions[session_id] = task
                        else:
                            logger.warning(f"Failed to allocate resources for session {session_id}, re-queuing")
                            # Resource allocation failed, re-queue
                            await self.queue.enqueue(session_id, SessionPriority.NORMAL)
                
                # Clean up completed sessions
                completed = [sid for sid, task in self.running_sessions.items() if task.done()]
                for session_id in completed:
                    await self.resource_manager.deallocate(session_id)
                    del self.running_sessions[session_id]
                
                # Wait before next iteration
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _execute_session(self, session_id: str, resource: SessionResource):
        """Execute a session"""
        try:
            logger.info(f"Starting session {session_id} on {resource.emulator_id}")
            
            # Get session details
            session = await self.db.execute_one(
                "SELECT * FROM sessions WHERE id = $1",
                session_id
            )
            
            if not session:
                logger.error(f"Session {session_id} not found")
                return
            
            # Call orchestrator's internal setup endpoint to install APK and launch app
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    setup_response = await client.post(
                        f"http://localhost:8000/internal/session/setup",
                        params={"session_id": session_id}
                    )
                    
                    if setup_response.status_code == 200:
                        logger.info(f"Session {session_id} setup complete, agent started")
                    else:
                        logger.error(f"Session {session_id} setup failed: {setup_response.text}")
                        await self.db.execute_write(
                            "UPDATE sessions SET status = 'failed', completed_at = NOW() WHERE id = $1",
                            session_id
                        )
                        return
                        
                except Exception as e:
                    logger.error(f"Error calling setup endpoint: {e}")
                    await self.db.execute_write(
                        "UPDATE sessions SET status = 'failed', completed_at = NOW() WHERE id = $1",
                        session_id
                    )
                    return
            
            # Wait for session to complete (agent will run gameplay loop)
            # Monitor session status periodically
            while True:
                await asyncio.sleep(10)
                
                # Check if session is still running
                current_session = await self.db.execute_one(
                    "SELECT status FROM sessions WHERE id = $1",
                    session_id
                )
                
                if not current_session or current_session['status'] != 'running':
                    break
            
            # Session completed or stopped
            logger.info(f"Session {session_id} finished")
            
        except asyncio.CancelledError:
            # Session was cancelled
            logger.info(f"Session {session_id} was cancelled")
            await self.db.execute_write(
                "UPDATE sessions SET status = 'stopped', completed_at = NOW() WHERE id = $1",
                session_id
            )
            raise
            
        except Exception as e:
            logger.error(f"Error executing session {session_id}: {e}", exc_info=True)
            await self.db.execute_write(
                """UPDATE sessions 
                   SET status = 'failed', completed_at = NOW() 
                   WHERE id = $1""",
                session_id
            )
    
    def get_status(self) -> Dict:
        """Get orchestrator status"""
        return {
            "running": self._running,
            "queue_sizes": self.queue.get_queue_size(),
            "running_sessions": list(self.running_sessions.keys()),
            "resource_usage": self.resource_manager.get_resource_usage()
        }


# Singleton instance
_orchestrator_instance: Optional[MultiSessionOrchestrator] = None


async def get_orchestrator(db_manager: DatabaseManager) -> MultiSessionOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiSessionOrchestrator(db_manager)
        await _orchestrator_instance.start()
    return _orchestrator_instance
