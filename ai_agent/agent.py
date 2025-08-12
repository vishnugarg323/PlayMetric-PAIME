
import os
import redis
import json
import uuid
import time
import numpy as np
import cv2
import base64
import random
import logging
import psycopg2
import traceback
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any
import torch
import torch.nn as nn
import torch.optim as optim
from environment import GameEnvironment

class SimpleDQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim)
        )
    def forward(self, x):
        return self.fc(x)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Category:
    """Game category with serialization support"""
    primary: str
    secondary: str = "unknown"
    confidence: float = 0.0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'primary': self.primary,
            'secondary': self.secondary,
            'confidence': self.confidence
        }

def serialize_category(category):
    """Helper function to serialize Category objects"""
    if isinstance(category, Category):
        return category.to_dict()
    return category

class DQN(nn.Module):
    """Deep Q-Network for action selection"""
    def __init__(self, input_size=100, hidden_size=64, output_size=6):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class GameAnalyzer:
    """FREE Computer Vision Game Analysis using OpenCV"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_game_understanding(self, screenshot_data: bytes) -> Dict[str, Any]:
        """
        Enhanced Computer Vision Analysis using OpenCV and OCR
        """
        try:
            import pytesseract
            # Decode screenshot
            nparr = np.frombuffer(screenshot_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                self.logger.warning("Could not decode image")
                return self._create_default_analysis()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            # 1. GAME TYPE DETECTION
            game_type = self._detect_game_type(img, gray, hsv)
            # 2. UI ANALYSIS
            ui_elements = self._analyze_ui_elements(gray)
            # 3. VISUAL COMPLEXITY
            visual_complexity = self._assess_visual_complexity(gray)
            # 4. COLOR ANALYSIS
            color_analysis = self._analyze_colors(hsv)
            # 5. MECHANICS DETECTION
            mechanics_count = self._detect_game_mechanics(img, gray)
            # 6. OBJECTIVES DETECTION (Enhanced with OCR)
            objectives_count = self._detect_objectives(gray, ui_elements)
            ocr_text = pytesseract.image_to_string(img)
            # Try to extract score, level, objectives from OCR text
            score = self._extract_score_from_text(ocr_text)
            level = self._extract_level_from_text(ocr_text)
            objectives = self._extract_objectives_from_text(ocr_text)
            analysis = {
                'category': Category(primary=game_type, secondary="detected", confidence=0.8),
                'ui_analysis': ui_elements,
                'visual_complexity': visual_complexity,
                'color_analysis': color_analysis,
                'mechanics_count': mechanics_count,
                'objectives_count': objectives_count,
                'ocr_text': ocr_text,
                'score': score,
                'level': level,
                'objectives': objectives,
                'analysis_timestamp': datetime.now().isoformat()
            }
            self.logger.info(f"CV+OCR analysis complete: {game_type}, Score: {score}, Level: {level}, Objectives: {objectives}")
            return analysis
        except Exception as e:
            self.logger.error(f"Game analysis failed: {e}")
            return self._create_default_analysis()

    def _extract_score_from_text(self, text):
        import re
        match = re.search(r"score[:\s]+(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _extract_level_from_text(self, text):
        import re
        match = re.search(r"level[:\s]+(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _extract_objectives_from_text(self, text):
        # Example: look for 'collect', 'reach', 'defeat', etc.
        import re
        objectives = re.findall(r"(collect|reach|defeat|find|win|clear)[^\n]*", text, re.IGNORECASE)
        return objectives
    
    def _detect_game_type(self, img, gray, hsv) -> str:
        """Detect game type using computer vision patterns"""
        height, width = gray.shape
        
        # Edge detection for complexity
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (height * width)
        
        # Contour analysis
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        num_objects = len(contours)
        
        # Color variance analysis
        color_std = np.std(hsv[:,:,1])  # Saturation variance
        
        # Decision logic based on visual features
        if edge_density > 0.15 and num_objects > 50:
            return "action"
        elif edge_density < 0.05 and color_std < 30:
            return "casual"
        elif 20 < num_objects < 50 and 0.05 < edge_density < 0.15:
            return "puzzle"
        elif num_objects > 100:
            return "arcade"
        else:
            return "puzzle"  # Default based on common mobile games
    
    def _analyze_ui_elements(self, gray) -> Dict[str, int]:
        """Analyze UI elements using computer vision"""
        # Template matching would go here in a real implementation
        # For now, use contour detection as proxy
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size to find potential UI elements
        ui_elements = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 5000:  # Typical UI button size range
                ui_elements.append(contour)
        
        return {
            'total_elements': len(ui_elements),
            'large_elements': len([c for c in ui_elements if cv2.contourArea(c) > 1000]),
            'small_elements': len([c for c in ui_elements if cv2.contourArea(c) < 500])
        }
    
    def _assess_visual_complexity(self, gray) -> float:
        """Assess visual complexity using computer vision metrics"""
        # Calculate image entropy as complexity measure
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        hist = hist[hist > 0]  # Remove zero values
        
        if len(hist) == 0:
            return 0.0
            
        # Normalize histogram
        hist = hist / np.sum(hist)
        
        # Calculate entropy
        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        
        # Normalize to 0-1 range
        max_entropy = np.log2(256)
        complexity = entropy / max_entropy
        
        return float(complexity)
    
    def _analyze_colors(self, hsv) -> Dict[str, Any]:
        """Analyze color distribution"""
        # Calculate dominant colors
        hue_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        dominant_hue = int(np.argmax(hue_hist))
        
        # Calculate color variety
        sat_mean = float(np.mean(hsv[:,:,1]))
        val_mean = float(np.mean(hsv[:,:,2]))
        
        return {
            'dominant_hue': dominant_hue,
            'saturation_mean': sat_mean,
            'brightness_mean': val_mean,
            'color_variety': float(np.std(hsv[:,:,0]))
        }
    
    def _detect_game_mechanics(self, img, gray) -> int:
        """Detect game mechanics using computer vision"""
        # Look for repeating patterns (indicating game mechanics)
        # This is a simplified version - real implementation would be more sophisticated
        
        # Template matching for common game elements
        mechanics = 0
        
        self.environment = GameEnvironment()
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        if lines is not None and len(lines) > 10:
            mechanics += 1
        
        # Check for circular objects (collection games)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=10, maxRadius=100)
        if circles is not None:
            mechanics += 1
        
        return mechanics
    
    def _detect_objectives(self, gray, ui_elements) -> int:
        """Detect game objectives using UI analysis"""
        # In a real implementation, this would use OCR to read text
        # For now, estimate based on UI elements
        
        total_elements = ui_elements.get('total_elements', 0)
        
        # Estimate objectives based on UI complexity
        if total_elements > 20:
            return 3
        elif total_elements > 10:
            return 2
        elif total_elements > 5:
            return 1
        else:
            return 0
    
    def _create_default_analysis(self) -> Dict[str, Any]:
        """Create default analysis when computer vision fails"""
        return {
            'category': Category(primary="unknown", secondary="default", confidence=0.1),
            'ui_analysis': {'total_elements': 0, 'large_elements': 0, 'small_elements': 0},
            'visual_complexity': 0.0,
            'color_analysis': {'dominant_hue': 0, 'saturation_mean': 0.0, 'brightness_mean': 0.0, 'color_variety': 0.0},
            'mechanics_count': 0,
            'objectives_count': 0,
            'analysis_timestamp': datetime.now().isoformat()
        }

class GameTestingAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.game_analyzer = GameAnalyzer()
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'paime'),
            'user': os.getenv('DB_USER', 'paime'),
            'password': os.getenv('DB_PASSWORD', 'paime123')
        }
        self.environment = GameEnvironment()
        self.dqn = SimpleDQN(input_dim=10, output_dim=1)
        self.optimizer = optim.Adam(self.dqn.parameters())
        self.current_session = None
        self.current_game_state = None
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    async def run(self):
        """Main agent loop (async)"""
        self.logger.info("AI Agent running and waiting for testing requests...")
        while True:
            try:
                self.logger.info("Waiting for APK in queue...")
                queue_length = self.redis_client.llen('session_creation_queue')
                self.logger.info(f"Current queue length: {queue_length}")
                result = self.redis_client.blpop(['session_creation_queue'], timeout=10)
                if result:
                    queue_name, message_data = result
                    self.logger.info(f"Received data from queue: {message_data}")
                    try:
                        message = json.loads(message_data)
                        self.logger.info(f"Received message: {message}")
                        if message.get('type') == 'start_session':
                            await self.start_testing_session(message)
                        elif message.get('type') == 'stop_session':
                            self.logger.info(f"Received stop_session for session {message.get('session_id')}")
                            # Set a flag or break the testing loop to halt immediately
                            if self.current_session and self.current_session['session_id'] == message.get('session_id'):
                                self.logger.info(f"Halting current session: {message.get('session_id')}")
                                # You may need to set a flag checked in your testing loop, or forcibly break/return
                                self.current_session['halt'] = True
                        else:
                            self.logger.warning(f"Unknown message type: {message.get('type')}")
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse message: {e}")
                else:
                    self.logger.info("Redis timeout waiting for queue items, retrying...")
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)

    async def start_testing_session(self, message):
        session_id = message['session_id']
        game_id = message['game_id']
        game_name = message['game_name']
        package_name = message['package_name']
        apk_path = message['apk_path']
        version_id = message.get('version_id')

        self.logger.info(f"Starting session: {session_id} for game {game_id}")

        try:
            # Check if session exists and update status
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT session_id FROM sessions 
                        WHERE session_id = %s
                    """, (session_id,))
                    if cursor.fetchone():
                        self.logger.info(f"Found existing active session: {session_id}")
                        cursor.execute("""
                            UPDATE sessions 
                            SET status = 'running', start_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                            WHERE session_id = %s
                        """, (session_id,))
                        conn.commit()
                    else:
                        self.logger.error(f"Session {session_id} not found in database")
                        return

            # Install and launch the APK using emulator API
            self.logger.info(f"Installing APK for {game_name} ({package_name})")
            install_result = await self.environment.install_apk(package_name, game_name, apk_path)
            self.logger.info(f"Installed APK: {install_result}")
            launch_result = await self.environment.launch_game(package_name)
            self.logger.info(f"Launched game: {launch_result}")

            # Start emulator session
            import aiohttp
            async with aiohttp.ClientSession() as session:
                start_resp = await session.post(f"http://emulator:5555/api/sessions/{game_id}/start")
                start_data = await start_resp.json()
                emulator_session_id = start_data.get('session_id')
                self.logger.info(f"Emulator session started: {emulator_session_id}")

            # Update session status to running
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE sessions 
                        SET status = 'running', updated_at = CURRENT_TIMESTAMP
                        WHERE session_id = %s
                    """, (session_id,))
                    conn.commit()
            self.logger.info(f"Started testing session {session_id} for game {game_id}")

            # Run the actual testing
            await self.run_comprehensive_testing(session_id, game_id, package_name, version_id, emulator_session_id)
        except Exception as e:
            self.logger.error(f"Testing error: {e}")
            await self.report_bug(session_id, game_id, version_id, 'crash', 'critical', f"Testing failed: {e}")
        finally:
            self.logger.info("Closing game environment")

    async def run_comprehensive_testing(self, session_id: str, game_id: str, package_name: str, version_id: str, emulator_session_id: str):
        try:
            self.logger.info("Starting comprehensive game analysis...")
            import aiohttp
            async with aiohttp.ClientSession() as session:
                screenshot_resp = await session.get(f"http://emulator:5555/api/sessions/{emulator_session_id}/screenshot")
                screenshot_json = await screenshot_resp.json()
                screenshot_b64 = screenshot_json.get('screenshot')
                screenshot_data = base64.b64decode(screenshot_b64) if screenshot_b64 else None
            if screenshot_data is None:
                raise Exception("Failed to capture screenshot from emulator")
            analysis = self.game_analyzer.analyze_game_understanding(screenshot_data)
            
            # Store enhanced game analysis in database (with safe JSON serialization)
            try:
                analysis_json = {
                    'category': serialize_category(analysis['category']),
                    'ui_analysis': analysis['ui_analysis'],
                    'visual_complexity': float(analysis['visual_complexity']),
                    'color_analysis': analysis['color_analysis'],
                    'mechanics_count': int(analysis['mechanics_count']),
                    'objectives_count': int(analysis['objectives_count']),
                    'analysis_timestamp': analysis['analysis_timestamp']
                }
                # Store in ai_analysis_summary column in games table
                with self.get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE games 
                            SET ai_analysis_summary = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE game_id = %s
                        """, (json.dumps(analysis_json), game_id))
                        conn.commit()
            except Exception as e:
                self.logger.error(f"Failed to store enhanced game analysis: {e}")
            
            # Extract category for display
            category = analysis['category']
            if isinstance(category, Category):
                category_name = category.primary
            else:
                category_name = category.get('primary', 'unknown')
            
            mechanics_count = analysis.get('mechanics_count', 0)
            objectives_count = analysis.get('objectives_count', 0)
            
            self.logger.info(f"Enhanced game analysis complete - Category: {category_name}, Objectives: {objectives_count}, Mechanics: {mechanics_count}")
            
            # Run extended testing loop with computer vision guidance
            await self.run_extended_testing_loop(session_id, game_id, version_id, analysis, emulator_session_id)
            
        except Exception as e:
            self.logger.error(f"Game analysis failed: {e}")
            # Continue with basic testing even if analysis fails
            basic_analysis = {
                'category': Category(primary="unknown", confidence=0.0),
                'ui_analysis': {},
                'visual_complexity': 0.0,
                'mechanics_count': 0
            }
            await self.run_extended_testing_loop(session_id, game_id, version_id, basic_analysis, emulator_session_id)

    async def run_extended_testing_loop(self, session_id: str, game_id: str, version_id: str, game_analysis: Dict, emulator_session_id: str):
        import os, aiohttp, json, random, asyncio
        import numpy as np
        test_duration = 300
        start_time = time.time()
        action_count = 0
        step = 0
        try:
            while time.time() - start_time < test_duration:
                async with aiohttp.ClientSession() as session:
                    # ...existing code...
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    step += 1
        except Exception as e:
            self.logger.error(f"Testing loop error: {e}")
        finally:
            async with aiohttp.ClientSession() as session:
                analysis_payload = {
                    "session_id": session_id,
                    "game_id": game_id,
                    "analysis_type": "summary",
                    "analysis_data": game_analysis,
                    "confidence_score": 1.0,
                    "api_used": "agent",
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
                try:
                    await session.post("http://backend:8000/api/ai/analysis", json=analysis_payload)
                except Exception as e:
                    self.logger.error(f"Failed to post analysis: {e}")

    def _extract_state_features(self, img, screenshot_json, game_analysis):
        # Extract features for RL state representation (score, level, objectives, etc.)
        score = game_analysis.get('score', 0)
        level = game_analysis.get('level', 1)
        objectives = len(game_analysis.get('objectives', []))
        return [score, level, objectives]

    def get_intelligent_action(self, screenshot_data: bytes, game_analysis: Dict) -> Dict:
        """Get intelligent action based on computer vision analysis"""
        try:
            # Decode screenshot for analysis
            nparr = np.frombuffer(screenshot_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {'type': 'tap', 'params': {'x': 400, 'y': 600}}
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Get visual complexity from current analysis or compute it
            if isinstance(game_analysis.get('visual_complexity'), (int, float)):
                visual_complexity = float(game_analysis['visual_complexity'])
            elif isinstance(game_analysis.get('visual_complexity'), dict):
                visual_complexity = 0.5  # Default medium complexity
            else:
                visual_complexity = 0.5
            # Find interactive areas using contour detection
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            interactive_areas = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if 500 < area < 5000:  # Button-sized areas
                    x, y, w, h = cv2.boundingRect(contour)
                    interactive_areas.append((x + w//2, y + h//2))  # Center point
            # Smart gameplay logic
            actions = []
            # If there are interactive areas, tap them in sequence, not just randomly
            if interactive_areas:
                for target in interactive_areas:
                    actions.append({'type': 'tap', 'params': {'x': int(target[0]), 'y': int(target[1])}})
            # If visual complexity is high, try swipes and drags
            if visual_complexity > 0.7:
                actions.append({'type': 'swipe', 'params': {'start_x': random.randint(100, 500), 'start_y': random.randint(200, 800), 'end_x': random.randint(500, 900), 'end_y': random.randint(200, 800)}})
                actions.append({'type': 'drag', 'params': {'start_x': random.randint(100, 500), 'start_y': random.randint(200, 800), 'end_x': random.randint(500, 900), 'end_y': random.randint(200, 800)}})
            # If visual complexity is low, try basic taps and back
            if visual_complexity < 0.3:
                actions.append({'type': 'tap', 'params': {'x': random.randint(100, 900), 'y': random.randint(200, 1600)}})
                actions.append({'type': 'back'})
            # Always add a random explore action
            actions.append({'type': 'tap', 'params': {'x': random.randint(100, 900), 'y': random.randint(200, 1600)}})
            # Choose the next action in a smart sequence
            if actions:
                return random.choice(actions)
            # Fallback to basic tap
            return {'type': 'tap', 'params': {'x': random.randint(100, 900), 'y': random.randint(200, 1600)}}
        except Exception as e:
            self.logger.error(f"Error in intelligent action selection: {e}")
            # Fallback to basic action
            return {'type': 'tap', 'params': {'x': 400, 'y': 600}}

    def detect_and_report_issues(self, session_id: str, game_id: str, version_id: str, screenshot_data: bytes):
        """Detect potential issues using computer vision"""
        try:
            nparr = np.frombuffer(screenshot_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            pixel_variance = np.var(gray)
            if pixel_variance < 100:
                return {
                    "type": "freeze",
                    "severity": "high",
                    "description": "Potential frozen screen detected",
                    "confidence": 0.9,
                    "ai_analysis": {"pixel_variance": float(pixel_variance)}
                }
            mean_brightness = np.mean(gray)
            if mean_brightness < 10:
                return {
                    "type": "display",
                    "severity": "medium",
                    "description": "Very dark screen detected",
                    "confidence": 0.8,
                    "ai_analysis": {"mean_brightness": float(mean_brightness)}
                }
            elif mean_brightness > 245:
                return {
                    "type": "display",
                    "severity": "medium",
                    "description": "Very bright screen detected",
                    "confidence": 0.8,
                    "ai_analysis": {"mean_brightness": float(mean_brightness)}
                }
            return None
        except Exception as e:
            self.logger.error(f"Error in issue detection: {e}")
            return None

    def record_ai_thought(self, session_id: str, thought: str, game_id: str = None, thought_type: str = "info", confidence: float = 1.0):
        """Record AI thought process"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO ai_thoughts (session_id, game_id, thought_type, thought_content, confidence, timestamp)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (session_id, game_id, thought_type, thought, confidence))
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to record AI thought: {e}")

    async def report_bug(self, session_id: str, game_id: str, version_id: str, bug_type: str, severity: str, description: str):
        """Report a detected bug"""
        try:
            bug_data = {
                'session_id': session_id,
                'game_id': game_id,
                'version_id': version_id,
                'type': bug_type,
                'severity': severity,
                'description': description,
                'timestamp': datetime.now().isoformat()
            }
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO bugs (session_id, game_id, version_id, bug_type, severity, description, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (session_id, game_id, version_id, bug_type, severity, description) DO NOTHING
                    """, (session_id, game_id, version_id, bug_type, severity, description))
                    conn.commit()
            self.logger.info(f"Bug reported: {bug_data}")
        except Exception as e:
            self.logger.error(f"Failed to report bug: {e}")

if __name__ == "__main__":
    import asyncio
    logger.info("Connecting to Redis at redis://redis:6379")
    try:
        redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        exit(1)
    logger.info("Connecting to database at postgresql://paime:paime123@db:5432/paime")
    try:
        db_config = {
            'host': 'db',
            'port': 5432,
            'database': 'paime',
            'user': 'paime',
            'password': 'paime123'
        }
        conn = psycopg2.connect(**db_config)
        conn.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        exit(1)
    agent = GameTestingAgent()
    logger.info("Agent initialization complete")
    asyncio.run(agent.run())
