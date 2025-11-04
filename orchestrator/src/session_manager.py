"""
Session Manager - Manages testing sessions
"""
import uuid
import time
import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session status"""
    CREATED = "created"
    INSTALLING = "installing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class Session:
    """Represents a testing session"""
    
    def __init__(
        self,
        package_name: str,
        apk_path: Optional[str] = None,
        agent_mode: str = "heuristic",
        duration_minutes: Optional[int] = None
    ):
        self.session_id = str(uuid.uuid4())[:8]
        self.package_name = package_name
        self.apk_path = apk_path
        self.agent_mode = agent_mode
        self.duration_minutes = duration_minutes
        
        self.status = SessionStatus.CREATED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        
        self.metrics = {
            'actions_performed': 0,
            'screenshots_captured': 0,
            'crashes_detected': 0,
            'levels_completed': 0
        }
        
    def start(self):
        """Mark session as started"""
        self.status = SessionStatus.RUNNING
        self.started_at = datetime.now()
        logger.info(f"Session {self.session_id} started")
    
    def stop(self):
        """Mark session as stopped"""
        self.status = SessionStatus.STOPPED
        self.ended_at = datetime.now()
        logger.info(f"Session {self.session_id} stopped")
    
    def complete(self):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED
        self.ended_at = datetime.now()
        logger.info(f"Session {self.session_id} completed")
    
    def fail(self, reason: str):
        """Mark session as failed"""
        self.status = SessionStatus.FAILED
        self.ended_at = datetime.now()
        logger.error(f"Session {self.session_id} failed: {reason}")
    
    def update_metrics(self, **kwargs):
        """Update session metrics"""
        for key, value in kwargs.items():
            if key in self.metrics:
                self.metrics[key] = value
    
    def get_duration(self) -> float:
        """Get session duration in seconds"""
        if not self.started_at:
            return 0.0
        
        end_time = self.ended_at if self.ended_at else datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'package_name': self.package_name,
            'apk_path': self.apk_path,
            'agent_mode': self.agent_mode,
            'duration_minutes': self.duration_minutes,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': self.get_duration(),
            'metrics': self.metrics
        }


class SessionManager:
    """Manages all testing sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.active_session: Optional[Session] = None
        
    def create_session(
        self,
        package_name: str,
        apk_path: Optional[str] = None,
        agent_mode: str = "heuristic",
        duration_minutes: Optional[int] = None
    ) -> Session:
        """Create a new session"""
        session = Session(
            package_name=package_name,
            apk_path=apk_path,
            agent_mode=agent_mode,
            duration_minutes=duration_minutes
        )
        
        self.sessions[session.session_id] = session
        logger.info(f"Created session {session.session_id} for {package_name}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def get_active_session(self) -> Optional[Session]:
        """Get currently active session"""
        return self.active_session
    
    def set_active_session(self, session_id: str) -> bool:
        """Set active session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        self.active_session = session
        return True
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions"""
        return [session.to_dict() for session in self.sessions.values()]
    
    def get_sessions_by_status(self, status: SessionStatus) -> List[Session]:
        """Get sessions by status"""
        return [s for s in self.sessions.values() if s.status == status]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove old completed/failed sessions"""
        current_time = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
                age = (current_time - session.created_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
            logger.info(f"Removed old session {session_id}")
