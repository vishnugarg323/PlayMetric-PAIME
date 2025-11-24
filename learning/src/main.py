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
from shared.game_registry import get_registry
from shared.database import DatabaseManager

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
                        timeout=aiohttp.ClientTimeout(total=120)
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
        
        # Step 4: Register knowledge base in game registry
        try:
            registry = get_registry()
            stats = {
                "scenes": len(knowledge_base.current_kb.get("scene_types", {})),
                "buttons": len(knowledge_base.current_kb.get("button_locations", {})),
                "strategies": len(knowledge_base.current_kb.get("strategies", []))
            }
            registry.link_video_learning(
                game_id=game_name,
                video_path=video_path,
                knowledge_base_path=str(kb_file),
                stats=stats
            )
            logger.info(f"🔗 Linked knowledge base to game registry: {game_name}")
        except Exception as e:
            logger.warning(f"Failed to link to game registry: {e}")
        
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
    Upload gameplay video for learning
    
    Args:
        file: Video file (MP4, AVI, etc.)
        game_id: Unique game identifier (e.g., "subway_surfers")
        display_name: Human-readable name (e.g., "Subway Surfers")
        package_name: Android package name (optional, can link later)
    """
    if learning_state["status"] == "processing":
        raise HTTPException(status_code=409, detail="Already processing a video")
    
    try:
        registry = get_registry()
        
        # Register or get existing game
        game = registry.get_game(game_id)
        if not game:
            registry.register_game(
                game_id=game_id,
                display_name=display_name or game_id,
                package_name=package_name,
                metadata={"source": "video_upload"}
            )
        
        # Save uploaded video
        video_dir = Path("/data/videos")
        video_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = video_dir / f"{game_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"📹 Video uploaded for {game_id}: {video_path} ({len(content)} bytes)")
        
        # Start learning process in background
        asyncio.create_task(process_video_learning(str(video_path), game_id))
        
        return {
            "message": "Video uploaded successfully",
            "video_path": str(video_path),
            "game_id": game_id,
            "game_status": registry.get_game(game_id)["status"],
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


@app.get("/games")
async def list_games():
    """List all registered games"""
    registry = get_registry()
    return {
        "games": registry.list_games(),
        "total": len(registry.games)
    }


@app.get("/games/{game_id}")
async def get_game(game_id: str):
    """Get game details"""
    registry = get_registry()
    game = registry.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    return game


@app.post("/games/{game_id}/link-apk")
async def link_apk_to_game(
    game_id: str,
    package_name: str = Form(...),
    apk_path: str = Form(None),
    version: str = Form(None)
):
    """Link an installed APK to a game"""
    registry = get_registry()
    
    game = registry.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found. Upload video first to register game.")
    
    try:
        registry.link_apk(game_id, apk_path or "", package_name, version)
        updated_game = registry.get_game(game_id)
        
        return {
            "message": "APK linked successfully",
            "game": updated_game,
            "ready_to_play": registry.is_ready_to_play(game_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8007"))
    uvicorn.run(app, host="0.0.0.0", port=port)
