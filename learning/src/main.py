"""
Learning Service - Offline Video Analysis & Knowledge Extraction

This service handles:
1. Video upload and frame extraction
2. Multi-tool analysis (OCR, BLIP-2, CV, Template Matching)
3. Knowledge base building
4. Real-time progress dashboard
5. Learning visualization
"""
import os
import logging
import asyncio
import json
import time
import httpx
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
import cv2
import numpy as np
from PIL import Image
import aiofiles

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sys
sys.path.append('/app')
from shared import DatabaseManager
from src.video_analyzer import VideoAnalyzer, analyze_video_with_progress
from src.knowledge_builder import KnowledgeBuilder

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
db_manager: Optional[DatabaseManager] = None
learning_state = {
    "status": "idle",  # idle, processing, complete, error
    "video_path": None,
    "total_frames": 0,
    "processed_frames": 0,
    "current_frame_path": None,
    "current_analysis": {},
    "knowledge_base": {},
    "start_time": None,
    "elapsed_time": 0,
    "progress_percent": 0,
    "insights": []
}

connected_clients = set()


class VideoUploadRequest(BaseModel):
    game_name: str
    description: Optional[str] = None


class KnowledgeBase:
    """Stores extracted knowledge from gameplay videos"""
    
    def __init__(self, knowledge_path: str = "/data/knowledge"):
        self.knowledge_path = Path(knowledge_path)
        self.knowledge_path.mkdir(parents=True, exist_ok=True)
        self.current_kb = {
            "game_name": "",
            "learned_at": None,
            "ui_elements": {},
            "button_locations": {},
            "text_patterns": {},
            "scene_types": {},
            "strategies": [],
            "statistics": {
                "total_frames_analyzed": 0,
                "unique_scenes": 0,
                "buttons_found": 0,
                "patterns_identified": 0
            }
        }
    
    def add_ui_element(self, element_type: str, location: Dict[str, int], confidence: float):
        """Record UI element location"""
        if element_type not in self.current_kb["ui_elements"]:
            self.current_kb["ui_elements"][element_type] = []
        
        self.current_kb["ui_elements"][element_type].append({
            "location": location,
            "confidence": confidence,
            "seen_count": 1
        })
    
    def add_button(self, text: str, location: Dict[str, int], scene_type: str):
        """Record button with its location"""
        if text not in self.current_kb["button_locations"]:
            self.current_kb["button_locations"][text] = []
        
        self.current_kb["button_locations"][text].append({
            "x": location["x"],
            "y": location["y"],
            "scene": scene_type,
            "count": 1
        })
        self.current_kb["statistics"]["buttons_found"] += 1
    
    def add_text_pattern(self, pattern: str, location: Dict[str, int], context: str):
        """Record recurring text patterns (Score, HP, etc.)"""
        if pattern not in self.current_kb["text_patterns"]:
            self.current_kb["text_patterns"][pattern] = {
                "locations": [],
                "contexts": [],
                "frequency": 0
            }
        
        self.current_kb["text_patterns"][pattern]["locations"].append(location)
        self.current_kb["text_patterns"][pattern]["contexts"].append(context)
        self.current_kb["text_patterns"][pattern]["frequency"] += 1
    
    def add_scene(self, scene_type: str, description: str, frame_index: int):
        """Record scene type and description"""
        if scene_type not in self.current_kb["scene_types"]:
            self.current_kb["scene_types"][scene_type] = {
                "count": 0,
                "descriptions": [],
                "frame_indices": []
            }
        
        self.current_kb["scene_types"][scene_type]["count"] += 1
        self.current_kb["scene_types"][scene_type]["descriptions"].append(description)
        self.current_kb["scene_types"][scene_type]["frame_indices"].append(frame_index)
        self.current_kb["statistics"]["unique_scenes"] = len(self.current_kb["scene_types"])
    
    def add_strategy(self, strategy: str, context: str, outcome: str):
        """Record gameplay strategies"""
        self.current_kb["strategies"].append({
            "action": strategy,
            "context": context,
            "outcome": outcome,
            "learned_at": datetime.now().isoformat()
        })
    
    def save(self, game_name: str):
        """Save knowledge base to file"""
        self.current_kb["game_name"] = game_name
        self.current_kb["learned_at"] = datetime.now().isoformat()
        
        kb_file = self.knowledge_path / f"{game_name}_knowledge.json"
        with open(kb_file, 'w') as f:
            json.dump(self.current_kb, f, indent=2)
        
        logger.info(f"💾 Knowledge base saved: {kb_file}")
        return kb_file
    
    def load(self, game_name: str) -> Dict[str, Any]:
        """Load existing knowledge base"""
        kb_file = self.knowledge_path / f"{game_name}_knowledge.json"
        if kb_file.exists():
            with open(kb_file, 'r') as f:
                self.current_kb = json.load(f)
            logger.info(f"📖 Knowledge base loaded: {kb_file}")
            return self.current_kb
        return None


knowledge_base = KnowledgeBase()


async def analyze_video_task(video_id: str, video_path: str, game_id: str):
    """Background task to analyze video and build knowledge"""
    global learning_state
    
    try:
        learning_state["status"] = "processing"
        learning_state["video_path"] = video_path
        learning_state["start_time"] = time.time()
        
        # Step 1: Analyze video with progress updates
        summary = await analyze_video_with_progress(
            db_manager=db_manager,
            video_id=video_id,
            video_path=video_path,
            game_id=game_id,
            websocket_broadcast=broadcast_update
        )
        
        logger.info(f"✅ Video analysis complete: {summary}")
        
        # Step 2: Build knowledge from analyzed frames
        await broadcast_update({
            'type': 'status',
            'status': 'building_knowledge',
            'message': 'Building game knowledge from patterns...'
        })
        
        kb_builder = KnowledgeBuilder(db_manager)
        kb_stats = await kb_builder.build_knowledge_from_video(video_id, game_id)
        
        logger.info(f"🧠 Knowledge built: {kb_stats}")
        
        learning_state["status"] = "complete"
        learning_state["elapsed_time"] = time.time() - learning_state["start_time"]
        
        await broadcast_update({
            'type': 'complete',
            'status': 'complete',
            'message': 'Video learning complete!',
            'summary': summary,
            'knowledge_stats': kb_stats,
            'total_time': learning_state["elapsed_time"]
        })
        
    except Exception as e:
        logger.error(f"Video analysis task failed: {e}")
        learning_state["status"] = "error"
        learning_state["error"] = str(e)
        
        await broadcast_update({
            'type': 'error',
            'status': 'error',
            'message': f"Analysis failed: {str(e)}"
        })


async def broadcast_update(update: Dict[str, Any]):
    """Broadcast learning progress to all connected dashboard clients"""
    if connected_clients:
        message = json.dumps(update)
        disconnected = set()
        
        for client in connected_clients:
            try:
                await client.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send update to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        connected_clients.difference_update(disconnected)


async def extract_frames_from_video(video_path: str, output_dir: str, fps: float = 1.0) -> List[str]:
    """Extract frames from video at specified FPS"""
    logger.info(f"🎬 Extracting frames from video: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps
    
    logger.info(f"📊 Video: {video_fps} FPS, {total_frames} frames, {duration:.1f}s duration")
    
    # Calculate frame interval for desired FPS
    frame_interval = int(video_fps / fps)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    frame_paths = []
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Extract every Nth frame
        if frame_count % frame_interval == 0:
            frame_path = output_path / f"frame_{extracted_count:06d}.png"
            cv2.imwrite(str(frame_path), frame)
            frame_paths.append(str(frame_path))
            extracted_count += 1
        
        frame_count += 1
    
    cap.release()
    
    logger.info(f"✅ Extracted {extracted_count} frames from {total_frames} total frames")
    return frame_paths


async def analyze_frame_multi_tool(frame_path: str, frame_index: int, vision_url: str) -> Dict[str, Any]:
    """Analyze single frame using multiple tools"""
    import aiohttp
    
    analysis = {
        "frame_index": frame_index,
        "frame_path": frame_path,
        "timestamp": datetime.now().isoformat(),
        "ocr": {},
        "vision": {},
        "ui_elements": [],
        "insights": []
    }
    
    try:
        # Call Vision Service for multi-tool analysis
        async with aiohttp.ClientSession() as session:
            # Prepare request
            with open(frame_path, 'rb') as f:
                files = {'file': f}
                
                # OCR Analysis
                try:
                    async with session.post(
                        f"{vision_url}/analyze/ocr",
                        json={"screenshot_path": frame_path},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            analysis["ocr"] = await resp.json()
                except Exception as e:
                    logger.warning(f"OCR failed for frame {frame_index}: {e}")
                
                # Vision AI Analysis (BLIP-2 or Gemini)
                try:
                    async with session.post(
                        f"{vision_url}/analyze",
                        json={"screenshot_path": frame_path},
                        timeout=aiohttp.ClientTimeout(total=240)  # BLIP-2 on CPU can take up to 120s
                    ) as resp:
                        if resp.status == 200:
                            analysis["vision"] = await resp.json()
                except Exception as e:
                    logger.warning(f"Vision AI failed for frame {frame_index}: {e}")
        
        # Extract insights
        if analysis["ocr"].get("text"):
            analysis["insights"].append(f"Detected text: {analysis['ocr']['text'][:100]}")
        
        if analysis["vision"].get("scene_type"):
            analysis["insights"].append(f"Scene: {analysis['vision']['scene_type']}")
        
        if analysis["vision"].get("buttons_detected"):
            buttons = analysis["vision"]["buttons_detected"]
            analysis["insights"].append(f"Found {len(buttons)} buttons")
            analysis["ui_elements"] = buttons
        
    except Exception as e:
        logger.error(f"Frame analysis failed: {e}")
        analysis["error"] = str(e)
    
    return analysis


async def process_video_learning(video_path: str, game_name: str):
    """Main learning pipeline - analyze video and build knowledge base"""
    global learning_state
    
    try:
        learning_state["status"] = "processing"
        learning_state["start_time"] = time.time()
        learning_state["video_path"] = video_path
        
        await broadcast_update({
            "type": "status",
            "status": "extracting_frames",
            "message": "Extracting frames from video..."
        })
        
        # Step 1: Extract frames (1 FPS for learning)
        frames_dir = "/data/screenshots/learning"
        frame_paths = await extract_frames_from_video(video_path, frames_dir, fps=1.0)
        
        learning_state["total_frames"] = len(frame_paths)
        learning_state["processed_frames"] = 0
        
        await broadcast_update({
            "type": "status",
            "status": "analyzing",
            "message": f"Analyzing {len(frame_paths)} frames...",
            "total_frames": len(frame_paths)
        })
        
        # Step 2: Analyze each frame
        vision_url = os.getenv("VISION_SERVICE_URL", "http://vision:8006")
        
        for idx, frame_path in enumerate(frame_paths):
            # Update state
            learning_state["current_frame_path"] = frame_path
            learning_state["processed_frames"] = idx + 1
            learning_state["progress_percent"] = int((idx + 1) / len(frame_paths) * 100)
            learning_state["elapsed_time"] = time.time() - learning_state["start_time"]
            
            # Analyze frame
            logger.info(f"🔍 Analyzing frame {idx + 1}/{len(frame_paths)}")
            analysis = await analyze_frame_multi_tool(frame_path, idx, vision_url)
            
            learning_state["current_analysis"] = analysis
            
            # Store frame analysis in database
            try:
                await db_manager.execute_write(
                    """
                    INSERT INTO learning_actions (
                        game_id, timestamp, action_type, action_params,
                        screenshot_before, detected_text, ui_elements,
                        reward, success, led_to_progress, metadata
                    ) VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    game_name,
                    analysis.get("action_type", "observation"),
                    json.dumps(analysis.get("vision", {})),
                    frame_path,
                    analysis.get("ocr", {}).get("full_text", ""),
                    json.dumps(analysis.get("ocr", {}).get("buttons", [])),
                    1.0 if analysis.get("insights") else 0.5,  # reward based on insights
                    True,
                    bool(analysis.get("insights")),
                    json.dumps({
                        "frame_index": idx,
                        "total_frames": len(frame_paths),
                        "scene_type": analysis.get("vision", {}).get("scene_type"),
                        "insights": analysis.get("insights", [])
                    })
                )
                logger.debug(f"💾 Stored frame {idx} analysis in database")
            except Exception as e:
                logger.error(f"Failed to store frame analysis: {e}")
            
            # Extract knowledge
            if analysis.get("ocr", {}).get("buttons"):
                for button in analysis["ocr"]["buttons"]:
                    knowledge_base.add_button(
                        button["text"],
                        {"x": button["x"], "y": button["y"]},
                        analysis.get("vision", {}).get("scene_type", "unknown")
                    )
            
            if analysis.get("vision", {}).get("scene_type"):
                knowledge_base.add_scene(
                    analysis["vision"]["scene_type"],
                    analysis["vision"].get("description", ""),
                    idx
                )
            
            if analysis.get("insights"):
                learning_state["insights"].extend(analysis["insights"])
            
            # Broadcast progress
            await broadcast_update({
                "type": "progress",
                "frame_index": idx + 1,
                "total_frames": len(frame_paths),
                "progress_percent": learning_state["progress_percent"],
                "elapsed_time": learning_state["elapsed_time"],
                "current_frame": frame_path,
                "analysis": analysis,
                "insights": analysis.get("insights", [])
            })
            
            # Small delay to prevent overwhelming clients
            await asyncio.sleep(0.1)
        
        # Step 3: Save knowledge base
        kb_file = knowledge_base.save(game_name)
        learning_state["knowledge_base"] = knowledge_base.current_kb
        learning_state["status"] = "complete"
        logger.info(f"✅ Knowledge base saved to {kb_file}")
        
        await broadcast_update({
            "type": "complete",
            "status": "complete",
            "message": f"Learning complete! Knowledge saved to {kb_file}",
            "knowledge_base": knowledge_base.current_kb,
            "total_time": time.time() - learning_state["start_time"]
        })
        
        logger.info(f"✅ Learning complete for {game_name}")
        
    except Exception as e:
        logger.error(f"Learning failed: {e}")
        learning_state["status"] = "error"
        learning_state["error"] = str(e)
        
        await broadcast_update({
            "type": "error",
            "status": "error",
            "message": f"Learning failed: {str(e)}"
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_manager
    
    logger.info("🚀 Learning Service starting...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.connect()
    logger.info("✅ Database connected")
    
    yield
    
    # Cleanup
    if db_manager:
        await db_manager.disconnect()
    logger.info("👋 Learning Service shutting down...")


app = FastAPI(title="Learning Service", lifespan=lifespan)

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "learning",
        "learning_status": learning_state["status"]
    }


@app.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...), 
    game_id: str = Form(...),
    display_name: str = Form(None),
    package_name: str = Form(None)
):
    """
    Upload gameplay video for learning (NEW VERSION - uses video_demonstrations table)
    
    Args:
        file: Video file (MP4, AVI, etc.)
        game_id: Game UUID from games table
        display_name: Human-readable name (optional)
        package_name: Android package name (optional)
    """
    if learning_state["status"] == "processing":
        raise HTTPException(status_code=409, detail="Already processing a video")
    
    try:
        # Save uploaded video
        video_dir = Path("/data/videos")
        video_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_path = video_dir / f"{game_id}_{timestamp}.mp4"
        
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"📹 Video uploaded: {video_path} ({len(content)} bytes)")
        
        # Create video_demonstrations record
        video_record = await db_manager.execute_one(
            """
            INSERT INTO video_demonstrations (
                game_id, video_path, processing_status, metadata
            ) VALUES ($1, $2, 'pending', $3)
            RETURNING id
            """,
            game_id,
            str(video_path),
            json.dumps({
                'uploaded_by': 'user',
                'file_size_bytes': len(content),
                'original_filename': file.filename
            })
        )
        
        video_id = str(video_record['id'])
        
        logger.info(f"📝 Created video_demonstrations record: {video_id}")
        
        # Start analysis in background
        asyncio.create_task(analyze_video_task(video_id, str(video_path), game_id))
        
        return {
            "message": "Video uploaded successfully, analysis started",
            "video_id": video_id,
            "video_path": str(video_path),
            "game_id": game_id,
            "status": "processing_started"
        }
        
    except Exception as e:
        logger.error(f"Video upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/learning-status")
async def get_learning_status():
    """Get current learning status"""
    return learning_state


@app.get("/knowledge-base/{game_name}")
async def get_knowledge_base(game_name: str):
    """Get knowledge base for a game"""
    kb = knowledge_base.load(game_name)
    if kb:
        return kb
    raise HTTPException(status_code=404, detail=f"No knowledge base found for {game_name}")


# Old registry-based endpoints removed - using new video learning endpoints instead


@app.post("/videos/analyze")
async def analyze_session_video(request: Dict[str, Any]):
    """
    Analyze video for a learning session (called by orchestrator for session_type='learning')
    
    Expects:
        session_id: Session UUID
        game_id: Game UUID  
        package_name: Game package name
        video_path: Absolute path to training video
    """
    session_id = request.get('session_id')
    game_id = request.get('game_id')
    package_name = request.get('package_name')
    video_path = request.get('video_path')
    
    if not all([session_id, game_id, video_path]):
        raise HTTPException(status_code=400, detail="Missing required fields: session_id, game_id, video_path")
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
    
    if learning_state["status"] == "processing":
        raise HTTPException(status_code=409, detail="Already processing a video")
    
    # Update existing video demonstration record to processing status
    video_id_from_request = request.get('video_id')
    if video_id_from_request:
        await db_manager.execute_write(
            """UPDATE video_demonstrations 
               SET processing_status = 'processing'
               WHERE id = $1""",
            video_id_from_request
        )
        video_id = video_id_from_request
    else:
        # Fallback: find video by path
        video_record = await db_manager.execute_one(
            "SELECT id FROM video_demonstrations WHERE video_path = $1",
            video_path
        )
        if video_record:
            video_id = str(video_record['id'])
            await db_manager.execute_write(
                "UPDATE video_demonstrations SET processing_status = 'processing' WHERE id = $1",
                video_id
            )
        else:
            raise HTTPException(status_code=404, detail="Video not found")
    
    logger.info(f"🎥 Starting video analysis for learning session {session_id}, video: {video_path}")
    
    # Start analysis in background
    asyncio.create_task(analyze_video_task(str(video_id), video_path, game_id))
    
    return {
        "message": "Video analysis started for learning session",
        "session_id": session_id,
        "video_id": str(video_id),
        "game_id": game_id,
        "status": "processing"
    }


@app.post("/videos/{video_id}/analyze")
async def trigger_video_analysis(video_id: str):
    """
    Manually trigger video analysis for an uploaded video
    (Usually starts automatically on upload)
    """
    if learning_state["status"] == "processing":
        raise HTTPException(status_code=409, detail="Already processing a video")
    
    # Get video record
    video_record = await db_manager.execute_read(
        "SELECT id, game_id, video_path, processing_status FROM video_demonstrations WHERE id = $1",
        video_id
    )
    
    if not video_record:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video = video_record[0]
    
    if video['processing_status'] == 'processing':
        raise HTTPException(status_code=409, detail="Video is already being processed")
    
    # Start analysis
    asyncio.create_task(analyze_video_task(video_id, video['video_path'], video['game_id']))
    
    return {
        "message": "Video analysis started",
        "video_id": video_id,
        "status": "processing"
    }


@app.get("/games/{game_id}/knowledge")
async def get_game_knowledge(
    game_id: str,
    pattern_type: Optional[str] = None,
    min_confidence: float = 0.0
):
    """
    Get all knowledge patterns for a game
    
    Args:
        game_id: Game UUID
        pattern_type: Filter by type (tap_button, ui_interaction, sequence, recovery)
        min_confidence: Minimum confidence score (0.0-1.0)
    """
    query = """
        SELECT 
            id, pattern_type, pattern_name, pattern_data,
            screen_conditions, ui_signature, action_template,
            times_seen, times_successful, times_failed,
            confidence_score, avg_reward,
            learned_from_video, learned_from_play,
            created_at, updated_at, last_used_at
        FROM game_knowledge
        WHERE game_id = $1
        AND confidence_score >= $2
    """
    params = [game_id, min_confidence]
    
    if pattern_type:
        query += " AND pattern_type = $3"
        params.append(pattern_type)
    
    query += " ORDER BY confidence_score DESC, times_successful DESC LIMIT 100"
    
    results = await db_manager.execute_read(query, *params)
    
    patterns = []
    for row in results:
        patterns.append({
            'id': row['id'],
            'pattern_type': row['pattern_type'],
            'pattern_name': row['pattern_name'],
            'action_template': json.loads(row['action_template']) if isinstance(row['action_template'], str) else row['action_template'],
            'confidence_score': row['confidence_score'],
            'success_rate': row['times_successful'] / max(row['times_successful'] + row['times_failed'], 1),
            'times_used': row['times_seen'],
            'avg_reward': row['avg_reward'],
            'last_used_at': row['last_used_at'].isoformat() if row['last_used_at'] else None
        })
    
    return {
        'game_id': game_id,
        'total_patterns': len(patterns),
        'patterns': patterns
    }


@app.post("/games/{game_id}/knowledge/query")
async def query_game_knowledge(
    game_id: str,
    current_scene: str = Form(...),
    detected_text: Optional[str] = Form(None),
    pattern_types: Optional[str] = Form(None)  # Comma-separated
):
    """
    Query knowledge base for matching patterns
    Used by AI-player to get learned actions
    
    Args:
        game_id: Game UUID
        current_scene: Current scene type (menu, gameplay, dialog, etc.)
        detected_text: OCR text from current screen
        pattern_types: Comma-separated pattern types to filter
    """
    kb_builder = KnowledgeBuilder(db_manager)
    
    pattern_type_list = None
    if pattern_types:
        pattern_type_list = [t.strip() for t in pattern_types.split(',')]
    
    matches = await kb_builder.query_knowledge(
        game_id=game_id,
        current_scene=current_scene,
        detected_text=detected_text,
        pattern_types=pattern_type_list
    )
    
    return {
        'game_id': game_id,
        'current_scene': current_scene,
        'total_matches': len(matches),
        'matches': matches
    }


@app.get("/games/{game_id}/learning-status")
async def get_game_learning_status(game_id: str):
    """Get learning status and statistics for a game"""
    
    # Get video demonstrations
    videos = await db_manager.execute_read(
        """
        SELECT id, video_path, uploaded_at, processing_status,
               total_frames_analyzed, total_actions_extracted
        FROM video_demonstrations
        WHERE game_id = $1
        ORDER BY uploaded_at DESC
        """,
        game_id
    )
    
    # Get knowledge statistics
    kb_stats = await db_manager.execute_read(
        """
        SELECT 
            pattern_type,
            COUNT(*) as count,
            AVG(confidence_score) as avg_confidence,
            SUM(times_successful) as total_successes,
            SUM(times_failed) as total_failures
        FROM game_knowledge
        WHERE game_id = $1
        GROUP BY pattern_type
        """,
        game_id
    )
    
    return {
        'game_id': game_id,
        'videos': [
            {
                'id': v['id'],
                'status': v['processing_status'],
                'frames_analyzed': v['total_frames_analyzed'],
                'actions_extracted': v['total_actions_extracted'],
                'uploaded_at': v['uploaded_at'].isoformat()
            }
            for v in videos
        ],
        'knowledge_stats': [
            {
                'pattern_type': s['pattern_type'],
                'count': s['count'],
                'avg_confidence': round(s['avg_confidence'], 2),
                'success_rate': s['total_successes'] / max(s['total_successes'] + s['total_failures'], 1)
            }
            for s in kb_stats
        ]
    }


@app.get("/current-frame")
async def get_current_frame():
    """Stream current frame being analyzed"""
    if not learning_state.get("current_frame_path"):
        raise HTTPException(status_code=404, detail="No frame being analyzed")
    
    frame_path = learning_state["current_frame_path"]
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail="Frame file not found")
    
    async def iterfile():
        async with aiofiles.open(frame_path, 'rb') as f:
            chunk = await f.read(8192)
            while chunk:
                yield chunk
                chunk = await f.read(8192)
    
    return StreamingResponse(iterfile(), media_type="image/png")


@app.websocket("/ws/learning-progress")
async def websocket_learning_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time learning progress"""
    await websocket.accept()
    connected_clients.add(websocket)
    
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "initial",
            "state": learning_state
        }))
        
        # Keep connection alive
        while True:
            # Wait for messages (ping/pong)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("Dashboard disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


@app.get("/frames/{video_id}/{frame_filename}")
async def get_frame_image(video_id: str, frame_filename: str):
    """Serve frame images for streaming to dashboard"""
    try:
        frame_path = f"/data/video_frames/{video_id}/{frame_filename}"
        
        if not os.path.exists(frame_path):
            raise HTTPException(status_code=404, detail="Frame not found")
        
        from fastapi.responses import FileResponse
        return FileResponse(frame_path, media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error serving frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REAL-TIME LEARNING SESSION WITH LIVE UPDATES
# ============================================================================

class LearningSessionRequest(BaseModel):
    session_id: str
    game_id: str
    batch_size: int = 3  # Number of frames to analyze in parallel


@app.post("/api/learning/request-next-batch")
async def request_next_learning_batch(request: LearningSessionRequest):
    """
    Request next batch of frames for learning session
    This will:
    1. Get next N frames from video
    2. Send to vision workers for parallel analysis
    3. Stream progress via WebSocket
    4. Store results automatically
    5. Return completion status
    """
    try:
        import httpx
        
        # TODO: Get next frames from video analysis queue
        # For now, using placeholder frame paths
        frame_paths = [
            f"/data/video_frames/{request.session_id}/frame_{i:04d}.jpg"
            for i in range(request.batch_size)
        ]
        
        # Broadcast batch start
        await broadcast_to_clients({
            "type": "batch_analysis_start",
            "session_id": request.session_id,
            "frame_paths": frame_paths,
            "batch_size": request.batch_size
        })
        
        # Analyze each frame with method-level progress streaming
        vision_url = os.getenv("VISION_SERVICE_URL", "http://nginx:8006")
        async with httpx.AsyncClient(timeout=120.0) as client:
            tasks = []
            for idx, frame_path in enumerate(frame_paths):
                # Read frame
                try:
                    async with aiofiles.open(frame_path, 'rb') as f:
                        frame_data = await f.read()
                except FileNotFoundError:
                    logger.warning(f"Frame not found: {frame_path}")
                    continue
                
                # Create analysis task with progress callbacks
                task = analyze_frame_with_progress(
                    client=client,
                    vision_url=vision_url,
                    session_id=request.session_id,
                    frame_index=idx,
                    frame_path=frame_path,
                    frame_data=frame_data
                )
                tasks.append(task)
            
            # Execute all frames in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Broadcast batch complete
        await broadcast_to_clients({
            "type": "batch_analysis_complete",
            "session_id": request.session_id,
            "results": [r for r in results if not isinstance(r, Exception)]
        })
        
        # Auto-store results
        store_batch = LearningDataBatch(
            session_id=request.session_id,
            game_id=request.game_id,
            frame_analyses=[
                {
                    "frame_path": results[i]["frame_path"],
                    "screen_width": results[i].get("screen_width", 1080),
                    "screen_height": results[i].get("screen_height", 2400),
                    "analysis": results[i].get("analysis", {})
                }
                for i in range(len(results))
                if not isinstance(results[i], Exception)
            ]
        )
        storage_result = await store_learning_batch(store_batch)
        
        # Broadcast storage complete
        await broadcast_to_clients({
            "type": "storage_complete",
            "session_id": request.session_id,
            "stored_count": storage_result["stored_count"],
            "patterns_extracted": storage_result["patterns_extracted"]
        })
        
        return {
            "success": True,
            "session_id": request.session_id,
            "frames_analyzed": len(results),
            "storage": storage_result
        }
        
    except Exception as e:
        logger.error(f"Learning batch failed: {e}", exc_info=True)
        await broadcast_to_clients({
            "type": "error",
            "session_id": request.session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_frame_with_progress(
    client: httpx.AsyncClient,
    vision_url: str,
    session_id: str,
    frame_index: int,
    frame_path: str,
    frame_data: bytes
):
    """
    Analyze a frame and stream method-level progress
    This is a wrapper around vision API that intercepts results
    """
    try:
        # Send frame to vision service
        response = await client.post(
            f"{vision_url}/analyze-frame",
            files={"file": (f"frame_{frame_index}.jpg", frame_data, "image/jpeg")},
            data={"session_id": session_id}
        )
        
        result = response.json()
        
        # Extract and broadcast individual method results
        methods = ['ocr', 'blip', 'gemini', 'grok', 'opencv', 'template_matching']
        for method in methods:
            if method in result:
                await broadcast_to_clients({
                    "type": "method_complete",
                    "session_id": session_id,
                    "frame_index": frame_index,
                    "method": method,
                    "result": result[method],
                    "duration_ms": result.get(f"{method}_time_ms", 0)
                })
        
        # Broadcast frame complete
        await broadcast_to_clients({
            "type": "frame_complete",
            "session_id": session_id,
            "frame_index": frame_index,
            "frame_path": frame_path,
            "worker_id": result.get("worker_id", "unknown"),
            "summary": result.get("summary", {})
        })
        
        return {
            "frame_path": frame_path,
            "frame_index": frame_index,
            "screen_width": result.get("screen_width", 1080),
            "screen_height": result.get("screen_height", 2400),
            "analysis": result
        }
        
    except Exception as e:
        logger.error(f"Frame {frame_index} analysis failed: {e}")
        await broadcast_to_clients({
            "type": "method_error",
            "session_id": session_id,
            "frame_index": frame_index,
            "error": str(e)
        })
        raise


@app.post("/games/{game_id}/build-patterns")
async def build_patterns_from_learning_data(
    game_id: str,
    min_occurrences: int = 3,
    min_success_rate: float = 0.7
):
    """
    Analyze learning_data and build game_knowledge patterns
    
    Extracts:
    - UI element patterns
    - Scene transition patterns
    - Text trigger patterns
    - Position cluster patterns
    """
    try:
        from src.pattern_recognition import PatternRecognitionEngine
        
        logger.info(f"Building patterns for game: {game_id}")
        
        engine = PatternRecognitionEngine(db_manager)
        results = await engine.analyze_and_build_patterns(
            game_id=game_id,
            min_occurrences=min_occurrences,
            min_success_rate=min_success_rate
        )
        
        # Get updated knowledge stats
        stats = await engine.get_pattern_analysis_status(game_id)
        
        return {
            'success': True,
            'game_id': game_id,
            'patterns_created': results,
            'current_stats': stats
        }
        
    except Exception as e:
        logger.error(f"Failed to build patterns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}/pattern-analysis-status")
async def get_pattern_analysis_status(game_id: str):
    """Get status of pattern analysis for a game"""
    try:
        from src.pattern_recognition import PatternRecognitionEngine
        
        engine = PatternRecognitionEngine(db_manager)
        status = await engine.get_pattern_analysis_status(game_id)
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get pattern status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BATCH FRAME ANALYSIS - 3 Frames in Parallel Across 3 Workers
# ============================================================================

class BatchFrameAnalysisRequest(BaseModel):
    session_id: str
    frame_paths: List[str]  # Up to 3 frames
    game_id: Optional[str] = None


@app.post("/api/analyze-batch-frames")
async def analyze_batch_frames(request: BatchFrameAnalysisRequest):
    """
    Analyze multiple frames in parallel using vision workers
    
    Args:
        request: Contains session_id, frame_paths (list of up to 3 frame paths), game_id
    
    Returns:
        List of analysis results with worker assignments
    """
    if not request.frame_paths or len(request.frame_paths) == 0:
        raise HTTPException(status_code=400, detail="No frame paths provided")
    
    if len(request.frame_paths) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 frames allowed for parallel analysis")
    
    import httpx
    
    # Vision service base URL (nginx load balancer will distribute to workers)
    vision_url = os.getenv("VISION_SERVICE_URL", "http://nginx:8006")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create tasks for parallel analysis
            tasks = []
            for idx, frame_path in enumerate(request.frame_paths):
                # Read frame file
                try:
                    async with aiofiles.open(frame_path, 'rb') as f:
                        frame_data = await f.read()
                except FileNotFoundError:
                    logger.error(f"Frame not found: {frame_path}")
                    continue
                
                # Send to vision service (load balancer distributes)
                task = client.post(
                    f"{vision_url}/analyze-frame",
                    files={"file": (f"frame_{idx}.jpg", frame_data, "image/jpeg")},
                    data={"session_id": request.session_id}
                )
                tasks.append(task)
            
            # Execute all requests in parallel
            logger.info(f"🚀 Sending {len(tasks)} frames for parallel analysis")
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            results = []
            for idx, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.error(f"Frame {idx} analysis failed: {response}")
                    results.append({
                        "frame_index": idx,
                        "frame_path": request.frame_paths[idx],
                        "worker_id": "unknown",
                        "status": "error",
                        "error": str(response)
                    })
                else:
                    result_data = response.json()
                    results.append({
                        "frame_index": idx,
                        "frame_path": request.frame_paths[idx],
                        "worker_id": result_data.get("worker_id", "unknown"),
                        "status": "success",
                        "analysis": result_data
                    })
            
            # Broadcast to connected WebSocket clients
            broadcast_message = {
                "type": "batch_analysis_complete",
                "session_id": request.session_id,
                "timestamp": datetime.now().isoformat(),
                "frames_analyzed": len(results),
                "results": results
            }
            await broadcast_to_clients(broadcast_message)
            
            return {
                "success": True,
                "session_id": request.session_id,
                "frames_analyzed": len(results),
                "results": results
            }
    
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


# ============================================================================
# LEARNING DATA STORAGE - Store Multi-Model Insights
# ============================================================================

class LearningDataBatch(BaseModel):
    session_id: str
    game_id: str
    frame_analyses: List[Dict[str, Any]]  # Each contains: frame_path, screen_width, screen_height, analysis result


@app.post("/api/store-learning-batch")
async def store_learning_batch(batch: LearningDataBatch):
    """
    Store batch of learning data from analyzed frames
    
    Args:
        batch: Contains session_id, game_id, and list of frame analyses
    
    Returns:
        Stored record IDs and pattern extraction count
    """
    try:
        stored_ids = []
        patterns_extracted = 0
        
        for frame_data in batch.frame_analyses:
            frame_path = frame_data.get("frame_path")
            analysis = frame_data.get("analysis", {})
            screen_width = frame_data.get("screen_width", 1080)
            screen_height = frame_data.get("screen_height", 2400)
            
            # Extract per-model insights
            ocr_insights = analysis.get("ocr", {})
            blip_insights = analysis.get("blip", {})
            gemini_insights = analysis.get("gemini", {})
            grok_insights = analysis.get("grok", {})
            opencv_insights = analysis.get("opencv", {})
            pattern_insights = analysis.get("template_matching", {})
            
            # Extract touch coordinates if available (already in percentage format)
            touch_x_percent = None
            touch_y_percent = None
            action_suggestion = (
                gemini_insights.get("action_suggestion", "") if gemini_insights.get("used")
                else grok_insights.get("action_suggestion", "") if grok_insights.get("used")
                else ""
            )
            if action_suggestion and ":" in action_suggestion:
                try:
                    coords = action_suggestion.split(":")
                    touch_x_percent = float(coords[0].strip().replace("%", ""))
                    touch_y_percent = float(coords[1].strip().replace("%", ""))
                except:
                    pass
            
            # Store to learning_data table
            result = await db_manager.execute_one(
                """
                INSERT INTO learning_data (
                    session_id, game_id, frame_path, screen_width, screen_height,
                    ocr_insights, blip_insights, gemini_insights, grok_insights,
                    opencv_insights, pattern_insights, 
                    touch_x_percent, touch_y_percent, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
                """,
                batch.session_id, batch.game_id, frame_path, screen_width, screen_height,
                json.dumps(ocr_insights), json.dumps(blip_insights), 
                json.dumps(gemini_insights), json.dumps(grok_insights),
                json.dumps(opencv_insights), json.dumps(pattern_insights),
                touch_x_percent, touch_y_percent,
                json.dumps({
                    "summary": analysis.get("summary", {}),
                    "methods_used": analysis.get("methods_used", []),
                    "timestamp": datetime.now().isoformat()
                })
            )
            
            stored_ids.append(result["id"])
            
            # Extract patterns for game_knowledge
            # 1. Scene transitions
            scene_type = analysis.get("summary", {}).get("scene_type", "unknown")
            if scene_type != "unknown":
                await db_manager.execute(
                    """
                    INSERT INTO game_knowledge (
                        game_id, pattern_type, pattern_name, pattern_data, confidence
                    ) VALUES ($1, 'scene_type', $2, $3, $4)
                    ON CONFLICT (game_id, pattern_type, pattern_name) 
                    DO UPDATE SET 
                        pattern_data = game_knowledge.pattern_data || $3,
                        times_seen = game_knowledge.times_seen + 1,
                        last_seen_at = CURRENT_TIMESTAMP
                    """,
                    batch.game_id, scene_type,
                    json.dumps({"frames": [frame_path]}),
                    analysis.get("summary", {}).get("overall_confidence", 0.5)
                )
                patterns_extracted += 1
            
            # 2. UI patterns from OpenCV
            if opencv_insights.get("total_detected", 0) > 0:
                for element in opencv_insights.get("ui_elements", []):
                    await db_manager.execute(
                        """
                        INSERT INTO game_knowledge (
                            game_id, pattern_type, pattern_name, pattern_data, confidence
                        ) VALUES ($1, 'ui_pattern', $2, $3, $4)
                        ON CONFLICT (game_id, pattern_type, pattern_name)
                        DO UPDATE SET
                            pattern_data = game_knowledge.pattern_data || $3,
                            times_seen = game_knowledge.times_seen + 1,
                            last_seen_at = CURRENT_TIMESTAMP
                        """,
                        batch.game_id, element.get("type", "unknown"),
                        json.dumps(element),
                        element.get("confidence", 0.5)
                    )
                patterns_extracted += 1
        
        logger.info(f"✅ Stored {len(stored_ids)} learning records, extracted {patterns_extracted} patterns")
        
        return {
            "success": True,
            "stored_count": len(stored_ids),
            "stored_ids": stored_ids,
            "patterns_extracted": patterns_extracted
        }
    
    except Exception as e:
        logger.error(f"Failed to store learning batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage failed: {str(e)}")


# ============================================================================
# PLAYING MODE - Query Learned Patterns for Gameplay
# ============================================================================

class PlayingModeQuery(BaseModel):
    game_id: str
    current_screen_analysis: Dict[str, Any]  # Current frame analysis
    context: Optional[Dict[str, Any]] = None  # Additional context (previous actions, etc.)


@app.post("/api/query-learned-patterns")
async def query_learned_patterns(query: PlayingModeQuery):
    """
    Query learned patterns to make gameplay decisions
    
    Args:
        query: Contains game_id, current screen analysis, and optional context
    
    Returns:
        Best action with confidence and reasoning
    """
    try:
        current_scene = query.current_screen_analysis.get("summary", {}).get("scene_type", "unknown")
        
        # 1. Query similar frames from learning_data
        similar_frames = await db_manager.execute_many(
            """
            SELECT 
                frame_path, 
                gemini_insights, 
                grok_insights,
                touch_x_percent, 
                touch_y_percent,
                metadata
            FROM learning_data
            WHERE game_id = $1
            AND metadata->>'summary'->>'scene_type' = $2
            ORDER BY created_at DESC
            LIMIT 10
            """,
            query.game_id, current_scene
        )
        
        # 2. Query best patterns from game_knowledge
        best_patterns = await db_manager.execute_many(
            """
            SELECT * FROM v_best_patterns
            WHERE game_id = $1
            AND pattern_type IN ('scene_type', 'action_sequence', 'ui_pattern')
            AND times_seen >= 3
            ORDER BY success_rate DESC, confidence DESC
            LIMIT 5
            """,
            query.game_id
        )
        
        # 3. Determine best action
        recommended_action = None
        action_confidence = 0.0
        reasoning = []
        
        # Prefer patterns with high success rate
        if best_patterns:
            top_pattern = best_patterns[0]
            pattern_data = json.loads(top_pattern["pattern_data"]) if isinstance(top_pattern["pattern_data"], str) else top_pattern["pattern_data"]
            
            recommended_action = pattern_data.get("action")
            action_confidence = top_pattern["success_rate"]
            reasoning.append(f"Pattern '{top_pattern['pattern_name']}' seen {top_pattern['times_seen']} times with {top_pattern['success_rate']:.0%} success")
        
        # Fallback to current AI suggestion
        if not recommended_action:
            current_action = query.current_screen_analysis.get("summary", {}).get("gameplay_mode", {}).get("action_coordinates")
            if current_action and current_action != "No action available":
                recommended_action = current_action
                action_confidence = query.current_screen_analysis.get("summary", {}).get("gameplay_mode", {}).get("decision_confidence", 0.5)
                reasoning.append("Using current AI analysis (no learned pattern found)")
        
        return {
            "success": True,
            "can_play": recommended_action is not None,
            "recommended_action": recommended_action,
            "action_confidence": action_confidence,
            "reasoning": reasoning,
            "similar_frames_found": len(similar_frames),
            "patterns_matched": len(best_patterns),
            "fallback_available": query.current_screen_analysis.get("summary", {}).get("gameplay_mode", {}).get("fallback_available", False)
        }
    
    except Exception as e:
        logger.error(f"Playing mode query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ============================================================================
# Learning Mode Session Management
# ============================================================================

class CreateLearningSessionRequest(BaseModel):
    video_id: str
    game_id: str
    batch_size: int = 3


class StartAnalysisRequest(BaseModel):
    session_id: str


@app.post("/api/learning/sessions/create")
async def create_learning_session(request: CreateLearningSessionRequest):
    """
    Create a new learning mode session for a video
    Returns session_id and initial status
    """
    try:
        import uuid
        
        session_id = str(uuid.uuid4())
        
        # Get video info
        video = await db_manager.fetch_one(
            "SELECT * FROM video_demonstrations WHERE id = $1",
            request.video_id
        )
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create learning session record
        await db_manager.execute_write(
            """
            INSERT INTO learning_sessions (
                id, video_id, game_id, status, batch_size, config
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            session_id,
            request.video_id,
            request.game_id,
            'pending',
            request.batch_size,
            json.dumps({"created_via": "api"})
        )
        
        logger.info(f"Created learning session {session_id} for video {request.video_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "video_id": request.video_id,
            "game_id": request.game_id,
            "batch_size": request.batch_size,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create learning session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learning/sessions/{session_id}/start-analysis")
async def start_session_analysis(session_id: str):
    """
    Start frame extraction and analysis for a learning session
    Uses round-robin worker assignment: Frame 1→W1, Frame 2→W2, Frame 3→W3
    Processes in 3-frame batches with real-time WebSocket updates
    """
    try:
        # Get session
        session = await db_manager.fetch_one(
            "SELECT * FROM learning_sessions WHERE id = $1",
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get video
        video = await db_manager.fetch_one(
            "SELECT * FROM video_demonstrations WHERE id = $1",
            session["video_id"]
        )
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Update session status
        await db_manager.execute_write(
            "UPDATE learning_sessions SET status = $1 WHERE id = $2",
            'extracting',
            session_id
        )
        
        # Start async frame extraction and analysis
        asyncio.create_task(process_learning_session(session_id, video["file_path"], session["batch_size"]))
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "extracting",
            "message": "Frame extraction started. Connect to WebSocket for real-time updates."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current status of learning session"""
    try:
        session = await db_manager.execute_one(
            "SELECT * FROM learning_sessions WHERE id = $1",
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get frame count
        frame_result = await db_manager.execute_one(
            "SELECT COUNT(*) as count FROM video_frames WHERE learning_session_id = $1",
            session_id
        )
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "total_frames": session["total_frames"],
            "frames_analyzed": session["frames_analyzed"],
            "current_batch_number": session["current_batch_number"],
            "batch_size": session["batch_size"],
            "progress_percent": (session["frames_analyzed"] / session["total_frames"] * 100) if session["total_frames"] > 0 else 0,
            "frames_stored": frame_result["count"] if frame_result else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/frames/{session_id}/{frame_number}")
async def get_frame_analysis(session_id: str, frame_number: int):
    """Get analysis data for a specific frame"""
    try:
        frame = await db_manager.fetch_one(
            """SELECT frame_number, frame_path, worker_id, 
                      ocr_result, blip_result, gemini_result, grok_result, 
                      opencv_result, template_result,
                      combined_summary, learning_insights, scene_type,
                      analysis_status, analyzed_at
               FROM video_frames 
               WHERE learning_session_id = $1 AND frame_number = $2""",
            session_id, frame_number
        )
        
        if not frame:
            # Return pending frame if not analyzed yet
            return {
                "frame_number": frame_number,
                "analysis_status": "pending",
                "frame_path": f"/data/learning_sessions/{session_id}/frames/frame_{frame_number:06d}.jpg"
            }
        
        return dict(frame)
        
    except Exception as e:
        logger.error(f"Failed to get frame analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/sessions/{session_id}/frames/latest")
async def get_latest_frame(session_id: str):
    """Get the latest analyzed frame with screenshot"""
    import base64
    import os
    
    try:
        # Get session info
        session = await db_manager.execute_one(
            "SELECT frames_analyzed, total_frames FROM learning_sessions WHERE id = $1",
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get latest frame with analysis
        frame = await db_manager.execute_one(
            """SELECT frame_number, frame_path, timestamp_ms,
                      combined_summary, learning_insights, scene_type,
                      analysis_status, analyzed_at
               FROM video_frames
               WHERE learning_session_id = $1 AND analysis_status = 'completed'
               ORDER BY frame_number DESC
               LIMIT 1""",
            session_id
        )
        
        if not frame:
            # No frames analyzed yet
            return {
                "frames_analyzed": session["frames_analyzed"],
                "total_frames": session["total_frames"],
                "screenshot_base64": None,
                "analysis": None
            }
        
        # Read screenshot file and convert to base64
        screenshot_base64 = None
        if frame["frame_path"] and os.path.exists(frame["frame_path"]):
            with open(frame["frame_path"], "rb") as f:
                screenshot_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Parse combined_summary JSON for analysis data
        analysis = None
        if frame["combined_summary"]:
            try:
                import json
                summary = json.loads(frame["combined_summary"])
                analysis = {
                    "scene_type": frame["scene_type"] or summary.get("scene_type"),
                    "scene_description": summary.get("scene_description"),
                    "ocr_text": summary.get("ocr_text"),
                    "touch_detected": summary.get("touch_detected", False),
                    "touch_point": summary.get("touch_point"),
                    "ui_elements": summary.get("ui_elements", []),
                }
            except:
                pass
        
        # Count total touches
        touch_result = await db_manager.execute_one(
            """SELECT COUNT(*) as count FROM video_frames 
               WHERE learning_session_id = $1 
               AND combined_summary::text LIKE '%\"touch_detected\": true%'""",
            session_id
        )
        
        return {
            "frame_number": frame["frame_number"],
            "timestamp_ms": frame["timestamp_ms"],
            "frames_analyzed": session["frames_analyzed"],
            "total_frames": session["total_frames"],
            "touches_detected": touch_result["count"] if touch_result else 0,
            "screenshot_base64": screenshot_base64,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest frame: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/comparisons/{session_id}/{from_frame}/{to_frame}")
async def get_frame_comparison(session_id: str, from_frame: int, to_frame: int):
    """Get comparison between two frames"""
    try:
        comparison = await db_manager.fetch_one(
            """SELECT from_frame_number as from_frame, to_frame_number as to_frame,
                      scene_changed, ui_elements_changed, action_detected, change_summary
               FROM frame_comparisons 
               WHERE session_id = $1 AND from_frame_number = $2 AND to_frame_number = $3""",
            session_id, from_frame, to_frame
        )
        
        if not comparison:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        return dict(comparison)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get frame comparison: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/learning/sessions/{session_id}/stream")
async def websocket_learning_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time learning session updates
    Streams 3-frame batch progress with per-model analysis results
    """
    await websocket.accept()
    connected_clients.add(websocket)
    
    try:
        # Send initial session status
        session = await db_manager.fetch_one(
            "SELECT * FROM learning_sessions WHERE id = $1",
            session_id
        )
        
        if session:
            await websocket.send_json({
                "type": "session_connected",
                "session_id": session_id,
                "status": session["status"],
                "batch_size": session["batch_size"]
            })
        
        # Keep connection alive and wait for messages
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back or handle client messages if needed
                await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)


async def process_learning_session(session_id: str, video_path: str, batch_size: int):
    """
    Background task to process learning session
    1. Extract frames from video
    2. Process in 3-frame batches with round-robin workers
    3. Generate frame comparisons
    4. Generate batch summaries
    """
    try:
        # Extract frames
        await broadcast_to_clients({
            "type": "extraction_started",
            "session_id": session_id
        })
        
        import cv2
        output_dir = f"/data/learning_sessions/{session_id}/frames"
        os.makedirs(output_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Update total frames
        await db_manager.execute_write(
            "UPDATE learning_sessions SET total_frames = $1 WHERE id = $2",
            total_frames,
            session_id
        )
        
        frame_paths = []
        frame_num = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_path = f"{output_dir}/frame_{frame_num:04d}.jpg"
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
            
            frame_num += 1
            
            if frame_num % 10 == 0:
                await broadcast_to_clients({
                    "type": "extraction_progress",
                    "session_id": session_id,
                    "extracted": frame_num,
                    "total": total_frames
                })
        
        cap.release()
        
        await broadcast_to_clients({
            "type": "extraction_complete",
            "session_id": session_id,
            "total_frames": len(frame_paths)
        })
        
        # Update status
        await db_manager.execute_write(
            "UPDATE learning_sessions SET status = $1 WHERE id = $2",
            'analyzing',
            session_id
        )
        
        # Process in batches with round-robin workers
        vision_workers = [
            "http://vision-worker-1:8009",
            "http://vision-worker-2:8010",
            "http://vision-worker-3:8011"
        ]
        
        batch_num = 0
        for i in range(0, len(frame_paths), batch_size):
            batch_frames = frame_paths[i:i+batch_size]
            batch_num += 1
            
            await broadcast_to_clients({
                "type": "batch_started",
                "session_id": session_id,
                "batch_number": batch_num,
                "frame_count": len(batch_frames)
            })
            
            # Round-robin worker assignment
            frame_results = []
            async with httpx.AsyncClient(timeout=120.0) as client:
                tasks = []
                for idx, frame_path in enumerate(batch_frames):
                    worker_idx = idx % len(vision_workers)
                    worker_url = vision_workers[worker_idx]
                    
                    # Read frame
                    with open(frame_path, 'rb') as f:
                        frame_data = f.read()
                    
                    task = analyze_frame_for_learning(
                        client=client,
                        worker_url=worker_url,
                        worker_id=f"worker-{worker_idx+1}",
                        session_id=session_id,
                        frame_index=i+idx,
                        frame_path=frame_path,
                        frame_data=frame_data
                    )
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                frame_results = [r for r in results if not isinstance(r, Exception)]
            
            # Store frame results
            await store_learning_frames(session_id, frame_results)
            
            # Generate frame comparisons
            if len(frame_results) >= 2:
                await generate_frame_comparisons(session_id, frame_results)
            
            # Generate batch summary
            await generate_batch_summary(session_id, batch_num, frame_results)
            
            # Update progress
            frames_analyzed = min(i + batch_size, len(frame_paths))
            await db_manager.execute_write(
                """
                UPDATE learning_sessions 
                SET frames_analyzed = $1, current_batch_number = $2
                WHERE id = $3
                """,
                frames_analyzed,
                batch_num,
                session_id
            )
            
            await broadcast_to_clients({
                "type": "batch_complete",
                "session_id": session_id,
                "batch_number": batch_num,
                "frames_analyzed": frames_analyzed,
                "total_frames": len(frame_paths)
            })
        
        # Mark complete
        await db_manager.execute_write(
            """
            UPDATE learning_sessions 
            SET status = $1, completed_at = NOW()
            WHERE id = $2
            """,
            'completed',
            session_id
        )
        
        await broadcast_to_clients({
            "type": "session_complete",
            "session_id": session_id,
            "total_frames": len(frame_paths),
            "total_batches": batch_num
        })
        
    except Exception as e:
        logger.error(f"Learning session processing failed: {e}", exc_info=True)
        await db_manager.execute_write(
            "UPDATE learning_sessions SET status = $1 WHERE id = $2",
            'failed',
            session_id
        )
        await broadcast_to_clients({
            "type": "session_error",
            "session_id": session_id,
            "error": str(e)
        })


async def analyze_frame_for_learning(
    client: httpx.AsyncClient,
    worker_url: str,
    worker_id: str,
    session_id: str,
    frame_index: int,
    frame_path: str,
    frame_data: bytes
):
    """Analyze single frame using specific vision worker"""
    try:
        start_time = time.time()
        
        # Call worker's /analyze/parallel endpoint
        response = await client.post(
            f"{worker_url}/analyze/parallel",
            files={"file": (f"frame_{frame_index}.jpg", frame_data, "image/jpeg")}
        )
        
        result = response.json()
        analysis_time_ms = int((time.time() - start_time) * 1000)
        
        # Broadcast per-method results
        for method in ['ocr', 'blip', 'gemini', 'grok', 'opencv', 'template']:
            if method in result:
                await broadcast_to_clients({
                    "type": "method_result",
                    "session_id": session_id,
                    "frame_index": frame_index,
                    "worker_id": worker_id,
                    "method": method,
                    "result": result[method]
                })
        
        return {
            "frame_index": frame_index,
            "frame_path": frame_path,
            "worker_id": worker_id,
            "analysis_time_ms": analysis_time_ms,
            "screen_width": result.get("screen_width", 1080),
            "screen_height": result.get("screen_height", 2400),
            "ocr_analysis": result.get("ocr"),
            "blip_analysis": result.get("blip"),
            "gemini_analysis": result.get("gemini"),
            "grok_analysis": result.get("grok"),
            "opencv_analysis": result.get("opencv"),
            "template_analysis": result.get("template"),
            "combined_summary": result.get("summary"),
            "methods_used": list(result.keys())
        }
        
    except Exception as e:
        logger.error(f"Frame {frame_index} analysis failed on {worker_id}: {e}")
        raise


async def store_learning_frames(session_id: str, frame_results: List[Dict]):
    """Store analyzed frames to database"""
    for frame in frame_results:
        await db_manager.execute_write(
            """
            INSERT INTO video_frames (
                learning_session_id, frame_path, frame_number, screen_width, screen_height,
                ocr_analysis, blip_analysis, gemini_analysis, grok_analysis, 
                opencv_analysis, template_analysis, combined_summary,
                worker_id, analysis_time_ms, methods_used
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
            session_id,
            frame["frame_path"],
            frame["frame_index"],
            frame["screen_width"],
            frame["screen_height"],
            json.dumps(frame["ocr_analysis"]) if frame["ocr_analysis"] else None,
            json.dumps(frame["blip_analysis"]) if frame["blip_analysis"] else None,
            json.dumps(frame["gemini_analysis"]) if frame["gemini_analysis"] else None,
            json.dumps(frame["grok_analysis"]) if frame["grok_analysis"] else None,
            json.dumps(frame["opencv_analysis"]) if frame["opencv_analysis"] else None,
            json.dumps(frame["template_analysis"]) if frame["template_analysis"] else None,
            json.dumps(frame["combined_summary"]) if frame["combined_summary"] else None,
            frame["worker_id"],
            frame["analysis_time_ms"],
            frame["methods_used"]
        )


async def generate_frame_comparisons(session_id: str, frame_results: List[Dict]):
    """Generate sequential frame comparisons"""
    for i in range(len(frame_results) - 1):
        frame_a = frame_results[i]
        frame_b = frame_results[i + 1]
        
        # Simple comparison logic (can be enhanced)
        scene_changed = False
        ui_changes = {}
        text_changes = {}
        
        # Check if scenes are different (basic heuristic)
        if frame_a.get("combined_summary") and frame_b.get("combined_summary"):
            summary_a = frame_a["combined_summary"]
            summary_b = frame_b["combined_summary"]
            
            # Scene changed if main description differs significantly
            scene_changed = summary_a.get("scene_type") != summary_b.get("scene_type")
        
        # Get frame IDs
        frame_a_id = await db_manager.fetch_val(
            "SELECT id FROM video_frames WHERE learning_session_id = $1 AND frame_number = $2",
            session_id, frame_a["frame_index"]
        )
        frame_b_id = await db_manager.fetch_val(
            "SELECT id FROM video_frames WHERE learning_session_id = $1 AND frame_number = $2",
            session_id, frame_b["frame_index"]
        )
        
        if frame_a_id and frame_b_id:
            await db_manager.execute_write(
                """
                INSERT INTO frame_comparisons (
                    learning_session_id, frame_a_id, frame_b_id,
                    scene_changed, ui_elements_changed, text_changed,
                    change_summary
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                session_id,
                frame_a_id,
                frame_b_id,
                scene_changed,
                json.dumps(ui_changes),
                json.dumps(text_changes),
                f"Frame {frame_a['frame_index']} → {frame_b['frame_index']}: {'Scene changed' if scene_changed else 'Same scene'}"
            )


async def generate_batch_summary(session_id: str, batch_number: int, frame_results: List[Dict]):
    """Generate summary for 3-frame batch"""
    frame_ids = []
    scene_types = []
    
    for frame in frame_results:
        # Get frame ID
        frame_id = await db_manager.fetch_val(
            "SELECT id FROM video_frames WHERE learning_session_id = $1 AND frame_number = $2",
            session_id, frame["frame_index"]
        )
        if frame_id:
            frame_ids.append(frame_id)
        
        # Collect scene types
        if frame.get("combined_summary"):
            scene_type = frame["combined_summary"].get("scene_type", "unknown")
            scene_types.append(scene_type)
    
    # Determine dominant scene
    dominant_scene = max(set(scene_types), key=scene_types.count) if scene_types else "unknown"
    
    # Create batch summary
    await db_manager.execute_write(
        """
        INSERT INTO batch_summaries (
            learning_session_id, batch_number, frame_ids,
            dominant_scene_type, batch_insights, progression_summary
        ) VALUES ($1, $2, $3, $4, $5, $6)
        """,
        session_id,
        batch_number,
        frame_ids,
        dominant_scene,
        json.dumps({"frame_count": len(frame_results), "scene_types": scene_types}),
        f"Batch {batch_number}: {len(frame_results)} frames analyzed, dominant scene: {dominant_scene}"
    )


# ============================================================================
# Helper: Broadcast to WebSocket Clients
# ============================================================================

async def broadcast_to_clients(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    if connected_clients:
        disconnected = set()
        for websocket in connected_clients:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        connected_clients.difference_update(disconnected)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8007"))
    uvicorn.run(app, host="0.0.0.0", port=port)
