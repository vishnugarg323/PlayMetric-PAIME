"""
Analytics Service - Main API for game analytics
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from .difficulty import DifficultyAnalyzer
from .retention import RetentionEstimator

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
difficulty_analyzer: Optional[DifficultyAnalyzer] = None
retention_estimator: Optional[RetentionEstimator] = None
analysis_task: Optional[asyncio.Task] = None
is_analyzing = False


# Pydantic models
class SessionData(BaseModel):
    session_id: str
    duration: float
    crashes: int = 0
    levels_completed: int = 0
    actions_performed: int = 0


class LevelAttempt(BaseModel):
    level: str
    success: bool
    time_spent: float


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global difficulty_analyzer, retention_estimator
    
    # Startup
    logger.info("Starting Analytics Service...")
    
    difficulty_analyzer = DifficultyAnalyzer()
    retention_estimator = RetentionEstimator()
    
    logger.info("Analytics Service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analytics Service...")
    if is_analyzing and analysis_task:
        analysis_task.cancel()


app = FastAPI(
    title="PlayMetric Analytics Engine",
    description="Analyzes gameplay for difficulty and retention metrics",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "analyzing": is_analyzing,
        "levels_tracked": len(difficulty_analyzer.level_data) if difficulty_analyzer else 0
    }


@app.post("/session/add")
async def add_session(session: SessionData):
    """Add session data for retention analysis"""
    if not retention_estimator:
        raise HTTPException(status_code=500, detail="Retention estimator not initialized")
    
    retention_estimator.add_session(session.dict())
    
    return {
        "message": "Session data added",
        "session_id": session.session_id
    }


@app.post("/level/attempt")
async def track_level_attempt(attempt: LevelAttempt):
    """Track a level attempt"""
    if not difficulty_analyzer:
        raise HTTPException(status_code=500, detail="Difficulty analyzer not initialized")
    
    difficulty_analyzer.track_level_attempt(
        attempt.level,
        attempt.success,
        attempt.time_spent
    )
    
    return {
        "message": "Level attempt tracked",
        "level": attempt.level,
        "success": attempt.success
    }


@app.get("/difficulty/report")
async def get_difficulty_report():
    """Get difficulty analysis report"""
    if not difficulty_analyzer:
        raise HTTPException(status_code=500, detail="Difficulty analyzer not initialized")
    
    return difficulty_analyzer.get_difficulty_report()


@app.get("/difficulty/level/{level}")
async def get_level_difficulty(level: str):
    """Get difficulty score for specific level"""
    if not difficulty_analyzer:
        raise HTTPException(status_code=500, detail="Difficulty analyzer not initialized")
    
    if level not in difficulty_analyzer.level_data:
        raise HTTPException(status_code=404, detail=f"Level {level} not found")
    
    score = difficulty_analyzer.calculate_difficulty_score(level)
    data = difficulty_analyzer.level_data[level]
    
    return {
        "level": level,
        "difficulty_score": score,
        "attempts": data['attempts'],
        "failures": data['failures'],
        "time_spent": data['time_spent']
    }


@app.get("/retention/estimate")
async def get_retention_estimate():
    """Get retention estimates"""
    if not retention_estimator:
        raise HTTPException(status_code=500, detail="Retention estimator not initialized")
    
    return retention_estimator.get_retention_estimate()


@app.get("/retention/engagement")
async def get_engagement_score():
    """Get engagement score"""
    if not retention_estimator:
        raise HTTPException(status_code=500, detail="Retention estimator not initialized")
    
    score = retention_estimator.calculate_engagement_score()
    
    return {
        "engagement_score": score,
        "metrics": retention_estimator.engagement_metrics
    }


@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get comprehensive analytics summary"""
    if not difficulty_analyzer or not retention_estimator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    difficulty_report = difficulty_analyzer.get_difficulty_report()
    retention_estimate = retention_estimator.get_retention_estimate()
    
    return {
        "difficulty": difficulty_report,
        "retention": retention_estimate,
        "generated_at": difficulty_report['generated_at']
    }


@app.post("/analytics/save")
async def save_analytics_reports(session_id: str = "default"):
    """Save all analytics reports to files"""
    if not difficulty_analyzer or not retention_estimator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    output_dir = f"/data/analytics/{session_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        difficulty_analyzer.save_report(f"{output_dir}/difficulty_analysis.json")
        retention_estimator.save_report(f"{output_dir}/retention_estimate.json")
        
        return {
            "message": "Analytics reports saved",
            "output_dir": output_dir
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving reports: {str(e)}")


@app.post("/analytics/reset")
async def reset_analytics():
    """Reset all analytics data"""
    global difficulty_analyzer, retention_estimator
    
    difficulty_analyzer = DifficultyAnalyzer()
    retention_estimator = RetentionEstimator()
    
    return {"message": "Analytics reset successfully"}


if __name__ == "__main__":
    port = int(os.getenv("ANALYTICS_PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
