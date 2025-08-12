from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Literal

class ActivityBase(BaseModel):
    activity_id: str
    type: Literal['bug_found', 'session_started', 'session_completed']
    message: str
    timestamp: datetime
    
class GameBase(BaseModel):
    game_name: str
    package_name: str
    version: str

class GameCreate(GameBase):
    pass

class Game(GameBase):
    game_id: str
    created_at: datetime
    last_tested: Optional[datetime]
    bug_count: int
    test_count: int

class SessionBase(BaseModel):
    game_id: str
    game_name: str
    version: str

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    total_bugs_found: int
    max_level_reached: int
    max_score: int
    total_actions: int

class BugBase(BaseModel):
    session_id: str
    game_id: str
    bug_type: str
    severity: str
    description: str

class BugCreate(BugBase):
    screenshot: Optional[str] = None

class Bug(BugBase):
    bug_id: str
    timestamp: datetime
    resolved_version: Optional[str]
    status: str
    screenshot: Optional[str]

class TelemetryBase(BaseModel):
    session_id: str
    fps: float
    cpu_usage: float
    memory_usage: float
    current_level: int
    score: int
    actions_per_minute: float

class TelemetryCreate(TelemetryBase):
    pass

class Telemetry(TelemetryBase):
    id: str
    timestamp: datetime

class AnalyticsOverview(BaseModel):
    total_games: int
    total_bugs: int
    active_sessions: int
    bug_distribution: List[dict]
    recent_activity: List[dict]
    success_rate: float
    avg_session_duration: float