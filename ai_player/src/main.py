"""
AI Player Service - Decision Engine with Multi-Tool Analysis

This service handles:
1. Event-driven gameplay (screenshot → analyze → decide → act)
2. Multi-tool analysis ensemble
3. Knowledge-based decision making
4. Detailed reasoning logging
5. Real-time decision visualization
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
import aiohttp
from PIL import Image

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
player_state = {
    "status": "idle",  # idle, playing, paused, error
    "game_name": None,
    "knowledge_loaded": False,
    "current_screenshot": None,
    "current_analysis": {},
    "current_decision": {},
    "decision_history": [],
    "actions_taken": 0,
    "start_time": None,
    "elapsed_time": 0,
    "cycle_count": 0,
    "last_cycle_duration": 0
}

connected_dashboards = set()


class PlayRequest(BaseModel):
    game_name: str
    use_gemini: bool = True  # Use fast Gemini API by default
    max_cycles: Optional[int] = None  # Stop after N cycles
    cycle_delay: float = 1.0  # Delay after action (game response time)


class DecisionEngine:
    """Multi-tool decision engine with reasoning"""
    
    def __init__(self, knowledge_base: Dict[str, Any]):
        self.kb = knowledge_base
        self.vision_url = os.getenv("VISION_SERVICE_URL", "http://vision:8006")
        self.observation_url = os.getenv("OBSERVATION_SERVICE_URL", "http://observation:8003")
        
    async def capture_screenshot(self) -> str:
        """Capture current game screen"""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.observation_url}/capture") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["screenshot_path"]
                raise Exception(f"Screenshot capture failed: {resp.status}")
    
    async def analyze_multi_tool(self, screenshot_path: str, use_gemini: bool = True) -> Dict[str, Any]:
        """Analyze screenshot using multiple tools in parallel"""
        analysis = {
            "screenshot_path": screenshot_path,
            "timestamp": datetime.now().isoformat(),
            "tools_used": [],
            "ocr": {},
            "vision": {},
            "cv_detections": {},
            "template_matches": [],
            "analysis_time": 0
        }
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # 1. OCR Analysis (fast - 1-2s)
            async def ocr_analysis():
                try:
                    async with session.post(
                        f"{self.vision_url}/analyze/ocr",
                        json={"screenshot_path": screenshot_path},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            analysis["ocr"] = await resp.json()
                            analysis["tools_used"].append("OCR")
                except Exception as e:
                    logger.warning(f"OCR failed: {e}")
            
            tasks.append(ocr_analysis())
            
            # 2. Vision AI Analysis (Gemini fast or BLIP-2 slow)
            async def vision_analysis():
                try:
                    endpoint = "/analyze/gemini" if use_gemini else "/analyze"
                    timeout = 30 if use_gemini else 120
                    
                    async with session.post(
                        f"{self.vision_url}{endpoint}",
                        json={"screenshot_path": screenshot_path},
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        if resp.status == 200:
                            analysis["vision"] = await resp.json()
                            analysis["tools_used"].append("Gemini" if use_gemini else "BLIP-2")
                except Exception as e:
                    logger.warning(f"Vision AI failed: {e}")
            
            tasks.append(vision_analysis())
            
            # 3. Template Matching (if knowledge base has templates)
            if self.kb.get("ui_elements"):
                async def template_matching():
                    try:
                        # TODO: Implement template matching with known UI patterns
                        analysis["template_matches"] = []
                        analysis["tools_used"].append("TemplateMatching")
                    except Exception as e:
                        logger.warning(f"Template matching failed: {e}")
                
                tasks.append(template_matching())
            
            # Run all analysis tools in parallel
            await asyncio.gather(*tasks, return_exceptions=True)
        
        analysis["analysis_time"] = time.time() - start_time
        return analysis
    
    def think(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Reasoning process - think through the situation"""
        reasoning = {
            "timestamp": datetime.now().isoformat(),
            "observations": [],
            "thoughts": [],
            "options": [],
            "decision": {},
            "confidence": 0.0,
            "reasoning_process": []
        }
        
        # Step 1: What do I see?
        scene_type = analysis.get("vision", {}).get("scene_type", "unknown")
        description = analysis.get("vision", {}).get("description", "")
        ocr_text = analysis.get("ocr", {}).get("text", "")
        
        reasoning["observations"].append(f"Scene type: {scene_type}")
        reasoning["observations"].append(f"Description: {description}")
        if ocr_text:
            reasoning["observations"].append(f"Text detected: {ocr_text[:100]}")
        
        reasoning["reasoning_process"].append({
            "step": 1,
            "action": "Observe",
            "result": f"I see a {scene_type} screen"
        })
        
        # Step 2: What do I know about this situation?
        if scene_type in self.kb.get("scene_types", {}):
            scene_knowledge = self.kb["scene_types"][scene_type]
            reasoning["thoughts"].append(
                f"I've seen this {scene_type} scene {scene_knowledge['count']} times before"
            )
            reasoning["reasoning_process"].append({
                "step": 2,
                "action": "Recall",
                "result": f"Knowledge base has {scene_knowledge['count']} examples of {scene_type}"
            })
        else:
            reasoning["thoughts"].append(f"This {scene_type} scene is new to me")
            reasoning["reasoning_process"].append({
                "step": 2,
                "action": "Recall",
                "result": "No prior knowledge of this scene type"
            })
        
        # Step 3: What are my options?
        buttons = analysis.get("ocr", {}).get("buttons", [])
        if buttons:
            for button in buttons:
                reasoning["options"].append({
                    "type": "tap",
                    "target": button["text"],
                    "x": button["x"],
                    "y": button["y"],
                    "confidence": button.get("confidence", 0.8)
                })
            
            reasoning["reasoning_process"].append({
                "step": 3,
                "action": "Identify Options",
                "result": f"Found {len(buttons)} clickable buttons"
            })
        
        # Check knowledge base for known buttons
        for button_text, button_data in self.kb.get("button_locations", {}).items():
            if button_text.lower() in ocr_text.lower():
                # We know this button
                avg_location = {
                    "x": int(sum(b["x"] for b in button_data) / len(button_data)),
                    "y": int(sum(b["y"] for b in button_data) / len(button_data))
                }
                reasoning["options"].append({
                    "type": "tap",
                    "target": button_text,
                    "x": avg_location["x"],
                    "y": avg_location["y"],
                    "confidence": 0.9,
                    "source": "knowledge_base"
                })
        
        # Step 4: What should I do?
        decision = self._select_best_action(scene_type, reasoning["options"], analysis)
        reasoning["decision"] = decision
        reasoning["confidence"] = decision.get("confidence", 0.0)
        
        reasoning["reasoning_process"].append({
            "step": 4,
            "action": "Decide",
            "result": f"Chose to {decision.get('action', 'wait')}: {decision.get('reason', 'no reason')}"
        })
        
        # Step 5: Why this action?
        reasoning["thoughts"].append(f"Decision: {decision.get('reason', 'Exploring')}")
        
        return reasoning
    
    def _select_best_action(
        self, 
        scene_type: str, 
        options: List[Dict], 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Select the best action from available options"""
        
        # Priority rules based on scene type
        if scene_type == "menu":
            # Look for PLAY, START, CONTINUE buttons
            for opt in options:
                target = opt.get("target", "").lower()
                if any(word in target for word in ["play", "start", "continue", "next"]):
                    return {
                        "action": "tap",
                        "x": opt["x"],
                        "y": opt["y"],
                        "reason": f"Tap '{opt['target']}' to proceed",
                        "confidence": opt["confidence"]
                    }
        
        elif scene_type == "loading":
            return {
                "action": "wait",
                "duration": 3.0,
                "reason": "Wait for loading to complete",
                "confidence": 0.9
            }
        
        elif scene_type == "reward":
            # Tap to collect reward
            return {
                "action": "tap",
                "x": 540,  # Center of typical 1080x1920 screen
                "y": 1200,
                "reason": "Tap to collect reward",
                "confidence": 0.8
            }
        
        elif scene_type == "game_over":
            # Look for restart/retry button
            for opt in options:
                target = opt.get("target", "").lower()
                if any(word in target for word in ["restart", "retry", "again"]):
                    return {
                        "action": "tap",
                        "x": opt["x"],
                        "y": opt["y"],
                        "reason": f"Tap '{opt['target']}' to retry",
                        "confidence": opt["confidence"]
                    }
        
        elif scene_type == "gameplay":
            # Use learned strategies if available
            strategies = self.kb.get("strategies", [])
            if strategies:
                # TODO: Apply learned strategies
                pass
            
            # Exploration: tap detected buttons
            if options:
                opt = options[0]
                return {
                    "action": "tap",
                    "x": opt["x"],
                    "y": opt["y"],
                    "reason": f"Explore by tapping '{opt.get('target', 'detected element')}'",
                    "confidence": opt["confidence"]
                }
        
        # Default: observe more
        return {
            "action": "wait",
            "duration": 2.0,
            "reason": "Observing to gather more information",
            "confidence": 0.5
        }
    
    async def execute_action(self, decision: Dict[str, Any]):
        """Execute the decided action"""
        action = decision.get("action", "wait")
        
        async with aiohttp.ClientSession() as session:
            if action == "tap":
                x, y = decision["x"], decision["y"]
                logger.info(f"👆 Tapping at ({x}, {y})")
                
                async with session.post(
                    f"{self.observation_url}/tap",
                    json={"x": x, "y": y}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    raise Exception(f"Tap failed: {resp.status}")
            
            elif action == "swipe":
                # TODO: Implement swipe
                pass
            
            elif action == "wait":
                duration = decision.get("duration", 1.0)
                logger.info(f"⏳ Waiting {duration}s")
                await asyncio.sleep(duration)
                return {"status": "waited", "duration": duration}
        
        return {"status": "no_action"}


async def broadcast_decision(update: Dict[str, Any]):
    """Broadcast decision to all connected dashboards"""
    if connected_dashboards:
        message = json.dumps(update)
        disconnected = set()
        
        for client in connected_dashboards:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)
        
        connected_dashboards.difference_update(disconnected)


async def play_game_loop(game_name: str, use_gemini: bool = True, max_cycles: Optional[int] = None, cycle_delay: float = 1.0):
    """Main AI gameplay loop"""
    global player_state
    
    try:
        # Load knowledge base
        kb_path = Path(f"/data/knowledge/{game_name}_knowledge.json")
        if not kb_path.exists():
            raise Exception(f"No knowledge base found for {game_name}")
        
        with open(kb_path) as f:
            knowledge_base = json.load(f)
        
        player_state["knowledge_loaded"] = True
        player_state["game_name"] = game_name
        player_state["status"] = "playing"
        player_state["start_time"] = time.time()
        
        decision_engine = DecisionEngine(knowledge_base)
        
        await broadcast_decision({
            "type": "status",
            "status": "playing",
            "game_name": game_name,
            "message": "AI started playing"
        })
        
        cycle = 0
        while player_state["status"] == "playing":
            if max_cycles and cycle >= max_cycles:
                logger.info(f"Reached max cycles ({max_cycles})")
                break
            
            cycle_start = time.time()
            cycle += 1
            player_state["cycle_count"] = cycle
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🎮 CYCLE {cycle}")
            logger.info(f"{'='*60}")
            
            # Step 1: Capture screenshot
            logger.info("📸 Capturing screenshot...")
            screenshot_path = await decision_engine.capture_screenshot()
            player_state["current_screenshot"] = screenshot_path
            
            await broadcast_decision({
                "type": "screenshot",
                "cycle": cycle,
                "screenshot_path": screenshot_path
            })
            
            # Step 2: Multi-tool analysis
            logger.info("🔍 Analyzing with multiple tools...")
            analysis = await decision_engine.analyze_multi_tool(screenshot_path, use_gemini)
            player_state["current_analysis"] = analysis
            
            logger.info(f"   Tools used: {', '.join(analysis['tools_used'])}")
            logger.info(f"   Analysis time: {analysis['analysis_time']:.2f}s")
            
            await broadcast_decision({
                "type": "analysis",
                "cycle": cycle,
                "analysis": analysis
            })
            
            # Step 3: Think and decide
            logger.info("🤔 Thinking...")
            reasoning = decision_engine.think(analysis)
            player_state["current_decision"] = reasoning
            
            logger.info("\n📋 REASONING PROCESS:")
            for step in reasoning["reasoning_process"]:
                logger.info(f"   Step {step['step']}: {step['action']} → {step['result']}")
            
            logger.info(f"\n💭 THOUGHTS:")
            for thought in reasoning["thoughts"]:
                logger.info(f"   • {thought}")
            
            logger.info(f"\n🎯 DECISION:")
            decision = reasoning["decision"]
            logger.info(f"   Action: {decision.get('action', 'none')}")
            logger.info(f"   Reason: {decision.get('reason', 'no reason')}")
            logger.info(f"   Confidence: {decision.get('confidence', 0):.2%}")
            
            await broadcast_decision({
                "type": "decision",
                "cycle": cycle,
                "reasoning": reasoning
            })
            
            # Step 4: Execute action
            logger.info(f"\n⚡ Executing action...")
            action_result = await decision_engine.execute_action(decision)
            player_state["actions_taken"] += 1
            
            # Save decision to history
            decision_record = {
                "cycle": cycle,
                "timestamp": datetime.now().isoformat(),
                "screenshot": screenshot_path,
                "analysis": analysis,
                "reasoning": reasoning,
                "action_result": action_result,
                "cycle_duration": time.time() - cycle_start
            }
            player_state["decision_history"].append(decision_record)
            
            # Save to file
            decisions_dir = Path("/data/decisions")
            decisions_dir.mkdir(parents=True, exist_ok=True)
            with open(decisions_dir / f"{game_name}_cycle_{cycle:04d}.json", 'w') as f:
                json.dump(decision_record, f, indent=2)
            
            cycle_duration = time.time() - cycle_start
            player_state["last_cycle_duration"] = cycle_duration
            player_state["elapsed_time"] = time.time() - player_state["start_time"]
            
            logger.info(f"\n⏱️  Cycle {cycle} completed in {cycle_duration:.1f}s")
            logger.info(f"{'='*60}\n")
            
            await broadcast_decision({
                "type": "cycle_complete",
                "cycle": cycle,
                "duration": cycle_duration,
                "total_time": player_state["elapsed_time"]
            })
            
            # Wait for game to respond
            await asyncio.sleep(cycle_delay)
        
        player_state["status"] = "idle"
        await broadcast_decision({
            "type": "status",
            "status": "idle",
            "message": "AI stopped playing"
        })
        
    except Exception as e:
        logger.error(f"Gameplay loop failed: {e}")
        player_state["status"] = "error"
        player_state["error"] = str(e)
        
        await broadcast_decision({
            "type": "error",
            "message": str(e)
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    logger.info("🚀 AI Player Service starting...")
    yield
    logger.info("👋 AI Player Service shutting down...")


app = FastAPI(title="AI Player Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ai_player",
        "player_status": player_state["status"]
    }


@app.post("/play")
async def start_playing(request: PlayRequest):
    """Start AI gameplay"""
    if player_state["status"] == "playing":
        raise HTTPException(status_code=409, detail="Already playing")
    
    # Start playing in background
    asyncio.create_task(
        play_game_loop(
            request.game_name,
            request.use_gemini,
            request.max_cycles,
            request.cycle_delay
        )
    )
    
    return {
        "message": "AI started playing",
        "game_name": request.game_name,
        "use_gemini": request.use_gemini
    }


@app.post("/stop")
async def stop_playing():
    """Stop AI gameplay"""
    if player_state["status"] != "playing":
        raise HTTPException(status_code=400, detail="Not playing")
    
    player_state["status"] = "idle"
    return {"message": "AI stopped playing"}


@app.get("/player-status")
async def get_player_status():
    """Get current player status"""
    return player_state


@app.get("/current-screenshot")
async def get_current_screenshot():
    """Stream current screenshot being analyzed"""
    if not player_state.get("current_screenshot"):
        raise HTTPException(status_code=404, detail="No screenshot available")
    
    screenshot_path = player_state["current_screenshot"]
    if not os.path.exists(screenshot_path):
        raise HTTPException(status_code=404, detail="Screenshot file not found")
    
    async def iterfile():
        import aiofiles
        async with aiofiles.open(screenshot_path, 'rb') as f:
            chunk = await f.read(8192)
            while chunk:
                yield chunk
                chunk = await f.read(8192)
    
    return StreamingResponse(iterfile(), media_type="image/png")


@app.websocket("/ws/player-updates")
async def websocket_player_updates(websocket: WebSocket):
    """WebSocket for real-time player updates"""
    await websocket.accept()
    connected_dashboards.add(websocket)
    
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "initial",
            "state": player_state
        }))
        
        while True:
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        connected_dashboards.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8008"))
    uvicorn.run(app, host="0.0.0.0", port=port)
