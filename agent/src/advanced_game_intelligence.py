"""
Advanced Game Intelligence Module
Adds game-specific knowledge, state tracking, and smarter decision making
on top of existing OCR + UI detection system.
"""
import logging
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import time
# from .color_detector import ColorBasedObjectDetector  # TODO: Fix import issue

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Represents the current game state"""
    screen_type: str  # menu, gameplay, level_complete, game_over
    level_number: Optional[int] = None
    objectives_visible: List[str] = None
    interactive_elements: List[Dict] = None
    difficulty_score: float = 0.0
    confidence: float = 0.0
    

class GameKnowledgeBase:
    """Stores generic mobile game patterns - works across puzzle, casual, and simple games"""
    
    def __init__(self):
        self.patterns = self._init_generic_patterns()
        
    def _init_generic_patterns(self) -> Dict:
        """Initialize universal game patterns that work across any mobile game"""
        return {
            "generic": {
                # Common menu/navigation keywords
                "menu_keywords": [
                    "tap", "start", "play", "begin", "go", "level", "continue", 
                    "resume", "new", "menu", "home", "ok", "yes"
                ],
                # Universal gameplay action words
                "gameplay_keywords": [
                    "tap", "click", "touch", "drag", "swipe", "move", "select",
                    "pull", "push", "rotate", "sort", "match", "collect", "place"
                ],
                # Success/completion indicators
                "completion_keywords": [
                    "complete", "completed", "done", "finish", "finished", "next", 
                    "success", "win", "won", "victory", "perfect", "excellent",
                    "great", "awesome", "level", "cleared"
                ],
                # Failure/retry indicators
                "failure_keywords": [
                    "failed", "fail", "retry", "try again", "restart", "game over",
                    "lose", "lost", "defeat", "defeated", "quit", "exit"
                ],
                # Interactive screen zones (where tappable elements usually are)
                "interactive_zones": {
                    "center": (0.2, 0.8, 0.3, 0.7),      # Main gameplay area
                    "bottom": (0.2, 0.8, 0.7, 0.95),     # Buttons, controls
                    "top": (0.2, 0.8, 0.05, 0.2),        # Status, info
                    "left": (0.05, 0.3, 0.3, 0.7),       # Side panels
                    "right": (0.7, 0.95, 0.3, 0.7)       # Side panels
                }
            }
        }
    
    def get_screen_type_keywords(self, screen_type: str) -> List[str]:
        """Get keywords for a specific screen type"""
        return self.patterns.get("generic", {}).get(f"{screen_type}_keywords", [])
    
    def get_interactive_zones(self) -> Dict:
        """Get zones where interactive elements are likely"""
        return self.patterns.get("generic", {}).get("interactive_zones", {})


class VisualStateTracker:
    """Tracks visual changes and game state across frames"""
    
    def __init__(self, history_size: int = 10):
        self.history_size = history_size
        self.screen_history = deque(maxlen=history_size)
        self.action_history = deque(maxlen=history_size)
        self.state_history = deque(maxlen=history_size)
        
    def add_frame(self, screenshot_path: str, action_taken: Dict, game_state: GameState):
        """Add a new frame to history"""
        self.screen_history.append(screenshot_path)
        self.action_history.append(action_taken)
        self.state_history.append(game_state)
        
    def detect_progress(self) -> Dict:
        """Detect if game is making progress"""
        if len(self.state_history) < 3:
            return {"progress": "unknown", "reason": "insufficient_history"}
        
        recent_states = list(self.state_history)[-5:]
        
        # Check if screen type is changing (good sign)
        screen_types = [s.screen_type for s in recent_states]
        unique_screens = len(set(screen_types))
        
        # Check if level numbers are increasing
        levels = [s.level_number for s in recent_states if s.level_number]
        level_progress = len(levels) > 1 and levels[-1] > levels[0] if levels else False
        
        # Check if stuck on same screen
        if unique_screens == 1 and len(recent_states) >= 5:
            return {
                "progress": "stuck",
                "reason": "same_screen_repeated",
                "screen_type": screen_types[0]
            }
        
        if level_progress:
            return {
                "progress": "advancing",
                "reason": "level_progression",
                "level_change": f"{levels[0]} -> {levels[-1]}"
            }
        
        if unique_screens > 2:
            return {
                "progress": "active",
                "reason": "screen_variation",
                "unique_screens": unique_screens
            }
        
        return {
            "progress": "slow",
            "reason": "minimal_change",
            "unique_screens": unique_screens
        }


class SmartActionDecider:
    """Makes intelligent action decisions based on game state"""
    
    def __init__(self, knowledge_base: GameKnowledgeBase):
        self.kb = knowledge_base
        self.consecutive_failures = 0
        self.last_successful_action = None
        
    def decide_action(
        self,
        game_state: GameState,
        ocr_buttons: List[Dict],
        ui_elements: List[Dict],
        progress_info: Dict,
        screen_dimensions: Tuple[int, int]
    ) -> Dict:
        """
        Decide the best action based on comprehensive game understanding
        
        Returns:
            Dict with 'action', 'coordinates', 'reasoning', 'confidence'
        """
        width, height = screen_dimensions
        
        # DISABLED: Let Phase 1 filtering handle gameplay instead of stuck recovery
        # # 1. Handle stuck situations with recovery strategies
        # if progress_info.get("progress") == "stuck":
        #     return self._handle_stuck_situation(
        #         game_state, ocr_buttons, ui_elements, width, height
        #     )
        
        # 1. Screen-type specific logic (Phase 1 prioritized)
        if game_state.screen_type == "menu":
            return self._handle_menu_screen(ocr_buttons, ui_elements, width, height)
        
        elif game_state.screen_type == "gameplay":
            return self._handle_gameplay_screen(
                game_state, ocr_buttons, ui_elements, width, height
            )
        
        elif game_state.screen_type == "level_complete":
            return self._handle_completion_screen(ocr_buttons, ui_elements, width, height)
        
        # 3. Fallback: Use existing correlation logic but with smarter targeting
        return self._smart_fallback(ocr_buttons, ui_elements, width, height)
    
    def _handle_stuck_situation(
        self, game_state: GameState, ocr_buttons: List[Dict],
        ui_elements: List[Dict], width: int, height: int
    ) -> Dict:
        """Handle when AI is stuck - try alternative strategies"""
        self.consecutive_failures += 1
        
        # Strategy 1: Try BACK button if stuck for long
        if self.consecutive_failures > 10:
            logger.info("🚨 Stuck for 10+ actions, trying BACK button")
            return {
                "action": "back",
                "coordinates": None,
                "reasoning": "Stuck recovery: Navigate back to try different path",
                "confidence": 0.6
            }
        
        # Strategy 2: Try random exploration in different zones (increased threshold to 15)
        if self.consecutive_failures > 15:
            zones = self.kb.get_interactive_zones()
            zone_name = ["center", "bottom", "top"][self.consecutive_failures % 3]
            zone = zones.get(zone_name, (0.3, 0.7, 0.3, 0.7))
            
            x = int(width * (zone[0] + zone[1]) / 2)
            y = int(height * (zone[2] + zone[3]) / 2)
            
            logger.info(f"🎲 Exploration tap in {zone_name} zone")
            return {
                "action": "tap",
                "coordinates": (x, y),
                "reasoning": f"Exploratory tap in {zone_name} zone to escape stuck state",
                "confidence": 0.5
            }
        
        # Strategy 3: Try alternative UI elements
        if ui_elements and len(ui_elements) > 3:
            # Try a different UI element than usual
            element = ui_elements[self.consecutive_failures % len(ui_elements)]
            return {
                "action": "tap",
                "coordinates": element["center"],
                "reasoning": "Trying alternative UI element to break stuck loop",
                "confidence": 0.5
            }
        
        return self._smart_fallback(ocr_buttons, ui_elements, width, height)
    
    def _handle_menu_screen(
        self, ocr_buttons: List[Dict], ui_elements: List[Dict],
        width: int, height: int
    ) -> Dict:
        """Handle menu screens - look for play/start/continue buttons"""
        menu_keywords = self.kb.get_screen_type_keywords("menu")
        
        # Prioritize menu keywords
        for button in ocr_buttons:
            text_lower = button.get("text", "").lower()
            for keyword in menu_keywords:
                if keyword in text_lower:
                    # Find nearby UI element
                    nearby_ui = self._find_nearby_ui_element(
                        button["center"], ui_elements, max_distance=200
                    )
                    
                    target = nearby_ui["center"] if nearby_ui else button["center"]
                    
                    logger.info(f"🎮 Menu: Clicking '{button['text']}' button")
                    return {
                        "action": "tap",
                        "coordinates": target,
                        "reasoning": f"Menu navigation: Clicking '{button['text']}' to start game",
                        "confidence": 0.9
                    }
        
        # Fallback: Click largest UI element in bottom half (likely play button)
        bottom_elements = [
            el for el in ui_elements
            if el["center"][1] > height * 0.5
        ]
        
        if bottom_elements:
            largest = max(bottom_elements, key=lambda e: e.get("area", 0))
            logger.info(f"🎮 Menu: Clicking largest bottom element")
            return {
                "action": "tap",
                "coordinates": largest["center"],
                "reasoning": "Menu: Clicking largest button in bottom half",
                "confidence": 0.7
            }
        
        return self._smart_fallback(ocr_buttons, ui_elements, width, height)
    
    def _handle_gameplay_screen(
        self, game_state: GameState, ocr_buttons: List[Dict],
        ui_elements: List[Dict], width: int, height: int
    ) -> Dict:
        """Handle active gameplay - focus on tapping visual game objects"""
        gameplay_keywords = self.kb.get_screen_type_keywords("gameplay")
        
        # PHASE 1 FIX: Filter out text/instruction areas
        # Remove UI elements in text instruction areas (typically top/bottom)
        # Use RELATIVE positioning based on screen height for universal compatibility
        gameplay_elements = []
        
        # Calculate dynamic Y-coordinate ranges based on screen height
        # Top 20% (y < height*0.2) = Status bar, top UI
        # Middle 20-35% (y = height*0.2 to height*0.35) = Gameplay area for most puzzle games
        # Bottom 35%+ (y > height*0.35) = Text instructions, buttons
        gameplay_min_y = height * 0.15  # Start after status bar (15% down)
        gameplay_max_y = height * 0.35  # End before instruction text (35% down)
        
        for element in ui_elements:
            ey = element.get("center_y", 0)
            # Keep only elements in gameplay area (relative to screen height)
            # This filters out "Tap to Unscrew" text (usually >35% down) and bottom buttons
            if gameplay_min_y < ey < gameplay_max_y:  # Focus on actual game object area
                gameplay_elements.append(element)
        
        logger.info(f"📊 Filtered {len(ui_elements)} UI elements → {len(gameplay_elements)} gameplay elements (y={int(gameplay_min_y)}-{int(gameplay_max_y)}, screen={width}x{height})")
        
        # PRIORITY 1: Find and tap small/medium game objects (screws, bottles, pieces)
        # These are typically 500-15000 pixels, scattered in the center play area
        play_area_objects = []
        center_x, center_y = width // 2, height // 2
        
        for element in gameplay_elements:  # Use filtered elements
            ex, ey = element.get("center_x", 0), element.get("center_y", 0)
            area = element.get("area", 0)
            
            # Find game objects in the ACTUAL game area (using filtered elements already)
            # Prioritize small/medium objects (screws, bottles, pieces)
            if (abs(ex - center_x) < width * 0.4 and 
                1000 < area < 15000):  # Medium-sized objects (not tiny UI elements)
                play_area_objects.append(element)
        
        # Tap game objects randomly to interact with them
        if play_area_objects and len(play_area_objects) >= 3:
            import random
            target = random.choice(play_area_objects)
            logger.info(f"🎯 Tapping game object ({target['center_x']}, {target['center_y']}) area={target.get('area', 0)}")
            return {
                "action": "tap",
                "coordinates": (target["center_x"], target["center_y"]),
                "reasoning": f"Tapping detected game object (screw/bottle/piece) - {len(play_area_objects)} found",
                "confidence": 0.85
            }
        
        # PRIORITY 2: Look for gameplay text instructions ("tap to...", "drag...", etc)
        # BUT ONLY if they're in the gameplay area (not instruction text at bottom)
        for button in ocr_buttons:
            text_lower = button.get("text", "").lower()
            button_y = button.get("center", (0, 0))[1]
            
            # CRITICAL: Skip text in instruction area (relative to screen height)
            # Instruction text is typically in bottom 65% of screen
            if button_y > gameplay_max_y:
                logger.debug(f"⏭️ Skipping instruction text '{button['text']}' at y={button_y} (>{int(gameplay_max_y)}, outside gameplay area)")
                continue
            
            for keyword in gameplay_keywords:
                if keyword in text_lower:
                    # Find visual element near the instruction
                    nearby_ui = self._find_nearby_ui_element(
                        button["center"], gameplay_elements, max_distance=300  # Use filtered elements
                    )
                    
                    if nearby_ui:
                        target = nearby_ui["center"]
                        reasoning = f"Clicking visual element near '{button['text']}'"
                        confidence = 0.75
                    else:
                        target = (width // 2, height // 2)
                        reasoning = f"Clicking center for '{button['text']}' action"
                        confidence = 0.6
                    
                    logger.info(f"🎯 {reasoning}")
                    return {
                        "action": "tap",
                        "coordinates": target,
                        "reasoning": reasoning,
                        "confidence": confidence
                    }
        
        # PRIORITY 3: No game objects found - try center elements
        center_elements = self._get_center_elements(ui_elements, width, height)
        if center_elements:
            target_element = max(center_elements, key=lambda e: e.get("area", 0))
            logger.info(f"🎯 Clicking central game area")
            return {
                "action": "tap",
                "coordinates": target_element["center"],
                "reasoning": "Clicking main game area",
                "confidence": 0.65
            }
        
        return self._smart_fallback(ocr_buttons, ui_elements, width, height)
    
    def _handle_completion_screen(
        self, ocr_buttons: List[Dict], ui_elements: List[Dict],
        width: int, height: int
    ) -> Dict:
        """Handle level completion screens - continue to next level"""
        completion_keywords = self.kb.get_screen_type_keywords("completion")
        
        # Look for next/continue buttons
        for button in ocr_buttons:
            text_lower = button.get("text", "").lower()
            for keyword in completion_keywords:
                if keyword in text_lower:
                    nearby_ui = self._find_nearby_ui_element(
                        button["center"], ui_elements, max_distance=200
                    )
                    target = nearby_ui["center"] if nearby_ui else button["center"]
                    
                    logger.info(f"✅ Completion: Clicking '{button['text']}' to continue")
                    self.consecutive_failures = 0  # Reset on success
                    return {
                        "action": "tap",
                        "coordinates": target,
                        "reasoning": f"Level complete: Clicking '{button['text']}' to proceed",
                        "confidence": 0.95
                    }
        
        # Fallback: Click bottom center (where next buttons usually are)
        target = (width // 2, int(height * 0.8))
        logger.info("✅ Completion: Clicking bottom-center for next level")
        return {
            "action": "tap",
            "coordinates": target,
            "reasoning": "Level complete: Clicking likely 'next' button location",
            "confidence": 0.7
        }
    
    def _smart_fallback(
        self, ocr_buttons: List[Dict], ui_elements: List[Dict],
        width: int, height: int
    ) -> Dict:
        """Fallback to existing correlation logic with improvements"""
        # Use existing correlation but prioritize by spatial location
        if ocr_buttons and ui_elements:
            button = ocr_buttons[0]
            nearby_ui = self._find_nearby_ui_element(
                button["center"], ui_elements, max_distance=200
            )
            
            if nearby_ui:
                return {
                    "action": "tap",
                    "coordinates": nearby_ui["center"],
                    "reasoning": f"Correlated: '{button['text']}' text → visual element",
                    "confidence": 0.7
                }
        
        # Last resort: Click center
        if ui_elements:
            center_el = min(
                ui_elements,
                key=lambda e: abs(e["center"][0] - width/2) + abs(e["center"][1] - height/2)
            )
            return {
                "action": "tap",
                "coordinates": center_el["center"],
                "reasoning": "Fallback: Clicking most central UI element",
                "confidence": 0.5
            }
        
        return {
            "action": "tap",
            "coordinates": (width // 2, height // 2),
            "reasoning": "Last resort: Clicking screen center",
            "confidence": 0.3
        }
    
    def _find_nearby_ui_element(
        self, text_pos: Tuple[int, int], ui_elements: List[Dict],
        max_distance: int = 200
    ) -> Optional[Dict]:
        """Find UI element near OCR text position"""
        closest = None
        min_dist = max_distance
        
        for element in ui_elements:
            el_pos = element["center"]
            distance = ((text_pos[0] - el_pos[0])**2 + (text_pos[1] - el_pos[1])**2)**0.5
            
            if distance < min_dist:
                min_dist = distance
                closest = element
        
        return closest
    
    def _get_center_elements(
        self, ui_elements: List[Dict], width: int, height: int
    ) -> List[Dict]:
        """Get UI elements in the center region of screen (gameplay area)"""
        center_x = width / 2
        center_y = height * 0.4  # PHASE 1 FIX: Focus on upper-center where game objects are
        radius_x = width * 0.4
        radius_y = height * 0.3
        
        center_elements = []
        for element in ui_elements:
            x, y = element["center"]
            # PHASE 1 FIX: Also filter by Y position (avoid text areas)
            if (abs(x - center_x) < radius_x and 
                abs(y - center_y) < radius_y and
                300 < y < 900):  # Keep only elements in gameplay area
                center_elements.append(element)
        
        return center_elements


class ScreenClassifier:
    """Classifies what type of screen is being displayed"""
    
    def __init__(self, knowledge_base: GameKnowledgeBase):
        self.kb = knowledge_base
        
    def classify_screen(
        self, ocr_text: str, ocr_words: List[Dict], ui_element_count: int
    ) -> GameState:
        """
        Classify the current screen type based on OCR and UI analysis
        
        Returns:
            GameState object with classification
        """
        text_lower = ocr_text.lower()
        
        # Extract level number if present
        level_number = self._extract_level_number(text_lower)
        
        # Check for different screen types
        menu_score = self._calculate_keyword_score(
            text_lower, self.kb.get_screen_type_keywords("menu")
        )
        gameplay_score = self._calculate_keyword_score(
            text_lower, self.kb.get_screen_type_keywords("gameplay")
        )
        completion_score = self._calculate_keyword_score(
            text_lower, self.kb.get_screen_type_keywords("completion")
        )
        failure_score = self._calculate_keyword_score(
            text_lower, self.kb.get_screen_type_keywords("failure")
        )
        
        # Determine screen type
        scores = {
            "menu": menu_score,
            "gameplay": gameplay_score,
            "level_complete": completion_score,
            "game_over": failure_score
        }
        
        screen_type = max(scores, key=scores.get)
        confidence = scores[screen_type]
        
        # Adjust based on UI element count
        if ui_element_count > 15 and screen_type == "menu":
            # Many UI elements suggest gameplay rather than menu
            screen_type = "gameplay"
            confidence = 0.7
        
        logger.info(f"📺 Screen classified as: {screen_type} (confidence: {confidence:.2f})")
        
        return GameState(
            screen_type=screen_type,
            level_number=level_number,
            objectives_visible=[],
            interactive_elements=[],
            difficulty_score=0.5,
            confidence=confidence
        )
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate how many keywords are present in text"""
        if not keywords:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches / len(keywords)
    
    def _extract_level_number(self, text: str) -> Optional[int]:
        """Extract level number from text"""
        import re
        
        # Look for patterns like "Level 4", "Level 7", etc.
        level_match = re.search(r'level\s*(\d+)', text, re.IGNORECASE)
        if level_match:
            return int(level_match.group(1))
        
        return None


class ColorBasedObjectDetector:
    """Fast color-based detection for puzzle game objects (screws, bottles, etc.)"""
    
    def __init__(self):
        # Define color ranges in HSV for common game objects
        self.color_ranges = {
            'red': ([0, 100, 100], [10, 255, 255]),
            'red2': ([170, 100, 100], [180, 255, 255]),  # Red wraps around
            'blue': ([100, 100, 100], [130, 255, 255]),
            'green': ([40, 100, 100], [80, 255, 255]),
            'yellow': ([20, 100, 100], [40, 255, 255]),
            'purple': ([130, 100, 100], [160, 255, 255]),
            'orange': ([10, 100, 100], [20, 255, 255]),
            'cyan': ([80, 100, 100], [100, 255, 255])
        }
    
    def detect_objects(self, screenshot_path: str) -> List[Dict]:
        """
        Fast color-based object detection (<50ms vs 200ms for edge detection)
        Returns list of game objects with color, position, size
        """
        try:
            img = cv2.imread(screenshot_path)
            if img is None:
                return []
            
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            objects = []
            
            for color_name, (lower, upper) in self.color_ranges.items():
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    # Filter for game object size range (not too small, not too large)
                    if 500 < area < 15000:
                        x, y, w, h = cv2.boundingRect(contour)
                        objects.append({
                            'center_x': x + w//2,
                            'center_y': y + h//2,
                            'center': (x + w//2, y + h//2),
                            'area': area,
                            'width': w,
                            'height': h,
                            'color': color_name.replace('2', ''),  # Remove '2' suffix
                            'type': 'colored_object',
                            'aspect_ratio': w / max(h, 1)
                        })
            
            logger.debug(f"🎨 Color detection found {len(objects)} objects")
            return objects
            
        except Exception as e:
            logger.error(f"Color detection failed: {e}")
            return []


class AdvancedGameIntelligence:
    """
    Main class that orchestrates all advanced game intelligence features.
    Works universally across puzzle, casual, and simple mobile games.
    """
    
    def __init__(self, screen_dimensions: Tuple[int, int] = (1080, 1920)):
        """
        Initialize Advanced Game Intelligence
        
        Args:
            screen_dimensions: (width, height) - Detected at runtime from device
        """
        self.screen_dimensions = screen_dimensions
        self.knowledge_base = GameKnowledgeBase()
        self.state_tracker = VisualStateTracker()
        self.action_decider = SmartActionDecider(self.knowledge_base)
        self.screen_classifier = ScreenClassifier(self.knowledge_base)
        self.color_detector = ColorBasedObjectDetector()  # NEW: Fast color detection
        
        logger.info(f"🧠 Advanced Game Intelligence initialized (Universal)")
        logger.info(f"📐 Screen dimensions: {screen_dimensions}")
    
    def analyze_and_decide(
        self,
        screenshot_path: str,
        ocr_data: Dict,
        ui_elements: List[Dict]
    ) -> Dict:
        """
        Main entry point: Analyze screenshot and decide best action
        
        Args:
            screenshot_path: Path to current screenshot
            ocr_data: OCR analysis from existing system
            ui_elements: UI elements from existing CV detection
            
        Returns:
            Action decision with reasoning
        """
        # 1. FAST: Color-based object detection (add to UI elements)
        colored_objects = self.color_detector.detect_objects(screenshot_path)
        if colored_objects:
            # Merge with existing UI elements for richer detection
            ui_elements = ui_elements + colored_objects
            logger.debug(f"🎨 Added {len(colored_objects)} color-detected objects")
        
        # 2. Classify screen type
        game_state = self.screen_classifier.classify_screen(
            ocr_data.get("text", ""),
            ocr_data.get("words", []),
            len(ui_elements)
        )
        
        # 3. Check progress
        progress_info = self.state_tracker.detect_progress()
        
        # 4. Decide action using smart logic (with colored objects)
        action_decision = self.action_decider.decide_action(
            game_state,
            ocr_data.get("buttons_detected", []),
            ui_elements,
            progress_info,
            self.screen_dimensions
        )
        
        # 4. Track this frame
        self.state_tracker.add_frame(screenshot_path, action_decision, game_state)
        
        # 5. Add metadata
        action_decision.update({
            "screen_type": game_state.screen_type,
            "level": game_state.level_number,
            "progress": progress_info.get("progress"),
            "advanced_ai": True
        })
        
        logger.info(f"🎯 Decision: {action_decision['reasoning']} (confidence: {action_decision['confidence']:.2f})")
        
        return action_decision
