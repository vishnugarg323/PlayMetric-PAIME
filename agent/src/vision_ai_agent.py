"""
Vision AI Agent - Phase 2 Implementation
Integration with Vision-Language Models (Gemini + LLaVA) for intelligent gameplay
Supports both cloud (Gemini - free tier) and local (LLaVA - unlimited free)
"""
import logging
from typing import Dict, Optional, List, Tuple
import base64
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import google.generativeai for Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Run: pip install google-generativeai")

# Try to import transformers for LLaVA (free local alternative)
try:
    from transformers import AutoProcessor, LlavaForConditionalGeneration
    from PIL import Image
    import torch
    LLAVA_AVAILABLE = True
except ImportError:
    LLAVA_AVAILABLE = False
    logger.warning("LLaVA not available. Run: pip install transformers torch pillow")


class VisionAIAgent:
    """
    Vision-Language Model integration for intelligent gameplay analysis.
    
    Supports:
    - Google Gemini Flash (1500 free/day, fast, cloud)
    """
    
    def __init__(self, api_key: Optional[str] = None, model_type: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_type = model_type
        self.enabled = False
        self.model = None
        self.call_count = 0
        self.max_calls_per_session = 1000  # Reasonable limit for free tier
        
        # Try LLaVA as fallback if Gemini not available
        self.llava_agent = None
        use_llava_fallback = os.getenv("USE_LLAVA_FALLBACK", "false").lower() == "true"
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.enabled = True
                logger.info(f"🤖 Vision AI Agent initialized with {model_type}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("🤖 Vision AI disabled: google-generativeai not installed")
            else:
                logger.info("🤖 Vision AI disabled: no API key provided")
        
        # Initialize LLaVA as fallback if enabled
        if (not self.enabled or use_llava_fallback) and LLAVA_AVAILABLE:
            logger.info("🤖 Attempting to initialize LLaVA fallback...")
            try:
                self.llava_agent = LLaVAAgent()
                if self.llava_agent.enabled:
                    logger.info("✅ LLaVA fallback available")
                    if not self.enabled:
                        self.enabled = True  # Enable vision AI via LLaVA
            except Exception as e:
                logger.error(f"Failed to initialize LLaVA: {e}")
    
    def analyze_game_screenshot(
        self,
        screenshot_path: str,
        context: Dict,
        history: List[Dict] = None,
        screen_dimensions: Tuple[int, int] = (1080, 1920)
    ) -> Dict:
        """
        Analyze game screenshot using vision-language model.
        
        Args:
            screenshot_path: Path to screenshot file
            context: Current game context (OCR, UI elements, etc.)
            history: Recent action history
            screen_dimensions: (width, height) of screen
            
        Returns:
            Dict with analysis:
            - screen_type: menu/gameplay/completion/failure
            - screen_understanding: What's on screen
            - objective: Current game objective
            - action: tap/swipe/back
            - coordinates: (x, y) for action
            - confidence: AI confidence (0-1)
            - reasoning: Why this action
        """
        
        if not self.enabled:
            logger.debug("Vision AI not enabled, returning placeholder")
            return self._placeholder_response(context)
        
        if self.call_count >= self.max_calls_per_session:
            logger.warning(f"Vision AI call limit reached ({self.max_calls_per_session})")
            return self._placeholder_response(context)
        
        try:
            # Try Gemini first if available
            if self.model is not None:
                response = self._call_gemini_api(screenshot_path, context, history, screen_dimensions)
                self.call_count += 1
                logger.info(f"🤖 Gemini Vision AI analysis complete (call #{self.call_count})")
                return response
            # Fall back to LLaVA if Gemini not available
            elif self.llava_agent and self.llava_agent.enabled:
                logger.info("🤖 Using LLaVA fallback for vision analysis...")
                response = self.llava_agent.analyze_game_screenshot(
                    screenshot_path, context, history or [], screen_dimensions
                )
                self.call_count += 1
                logger.info(f"🤖 LLaVA analysis complete (call #{self.call_count})")
                return response
            else:
                return self._placeholder_response(context)
        except Exception as e:
            logger.error(f"Vision AI analysis failed: {e}")
            # Try LLaVA fallback on Gemini error
            if self.llava_agent and self.llava_agent.enabled:
                try:
                    logger.info("🔄 Falling back to LLaVA after Gemini error...")
                    return self.llava_agent.analyze_game_screenshot(
                        screenshot_path, context, history or [], screen_dimensions
                    )
                except Exception as e2:
                    logger.error(f"LLaVA fallback also failed: {e2}")
            return self._placeholder_response(context)
    
    def _placeholder_response(self, context: Dict) -> Dict:
        """Placeholder response when Vision AI is not enabled"""
        return {
            "screen_understanding": "Vision AI not configured",
            "objective": "Unknown",
            "recommended_action": None,
            "confidence": 0.0,
            "reasoning": "Vision AI requires API key configuration",
            "vision_ai_enabled": False
        }
    
    def _call_gemini_api(
        self, 
        screenshot_path: str, 
        context: Dict, 
        history: List[Dict],
        screen_dimensions: Tuple[int, int]
    ) -> Dict:
        """
        Call Google Gemini Vision API for intelligent gameplay analysis
        """
        # Load and encode image
        with open(screenshot_path, 'rb') as f:
            image_data = f.read()
        
        width, height = screen_dimensions
        
        # Build context summary
        ocr_text = context.get('ocr_text', [])
        ui_elements = context.get('ui_elements', [])
        recent_actions = history[-5:] if history else []
        
        # Create comprehensive prompt
        prompt = f"""You are an expert AI agent playing a mobile puzzle game. Analyze this screenshot and provide intelligent gameplay decisions.

SCREEN DIMENSIONS: {width}x{height} pixels

CONTEXT:
- Detected Text (OCR): {', '.join([t.get('text', '') for t in ocr_text]) if ocr_text else 'None'}
- UI Elements: {len(ui_elements)} visual elements detected
- Recent Actions: {len(recent_actions)} actions taken

YOUR TASK:
1. Identify the screen type: "menu", "gameplay", "completion", or "failure"
2. Understand what's visible: game objects, buttons, objectives
3. Determine the current objective
4. Decide the BEST action to progress in the game
5. Provide precise coordinates for the action

GAME TYPES THIS SYSTEM HANDLES:
- Puzzle games: Screw Pull, Bottle Sort, Color Match
- Simple games with tap/swipe mechanics
- Menu navigation and level selection

CRITICAL RULES:
- For gameplay screens: Look for interactive game objects (screws, bottles, pieces, vehicles)
- Tap on game objects to interact, not decorative elements
- For menu screens: Find "Play", "Start", "Continue", level buttons
- For completion screens: Look for "Next", "Continue", "Claim" buttons
- Avoid tapping ads, close buttons unless stuck
- Coordinates MUST be within screen bounds (0-{width}, 0-{height})

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "screen_type": "menu|gameplay|completion|failure",
  "screen_understanding": "Brief description of what's visible on screen",
  "objective": "What needs to be done right now",
  "action": "tap|swipe|back",
  "coordinates": [x, y],
  "swipe_end": [x2, y2] (only if action is swipe),
  "confidence": 0.0-1.0,
  "reasoning": "Detailed explanation of why this action will help progress"
}}

EXAMPLES:

Example 1 - Gameplay (Screw Pull):
{{
  "screen_type": "gameplay",
  "screen_understanding": "Game board with multiple screws attached to colored plates. Some screws are accessible, others are blocked.",
  "objective": "Remove screws strategically to release plates without blocking the path",
  "action": "tap",
  "coordinates": [540, 880],
  "confidence": 0.85,
  "reasoning": "Tapping the top-most accessible screw will allow it to drop down and potentially unblock other screws. This screw appears to be free (not blocked by plates)."
}}

Example 2 - Menu:
{{
  "screen_type": "menu",
  "screen_understanding": "Main menu with Play button, settings icon, and level indicators",
  "objective": "Start or continue playing the game",
  "action": "tap",
  "coordinates": [540, 1200],
  "confidence": 0.95,
  "reasoning": "Large Play/Start button centered in lower third of screen will begin gameplay"
}}

Example 3 - Level Complete:
{{
  "screen_type": "completion",
  "screen_understanding": "Victory screen showing stars, score, and next level button",
  "objective": "Progress to next level",
  "action": "tap",
  "coordinates": [540, 1400],
  "confidence": 0.90,
  "reasoning": "Tapping the prominent 'Next' or 'Continue' button will advance to the next level"
}}

Now analyze the provided screenshot and respond ONLY with valid JSON (no other text):"""

        # Call Gemini API
        response = self.model.generate_content([prompt, {"mime_type": "image/png", "data": image_data}])
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Clean up response (remove markdown code blocks if present)
        if response_text.startswith('```'):
            # Remove ```json and ``` markers
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        result = json.loads(response_text)
        
        # Validate and normalize response
        result['vision_ai_enabled'] = True
        result['confidence'] = float(result.get('confidence', 0.5))
        
        # Ensure coordinates are within bounds
        if 'coordinates' in result:
            x, y = result['coordinates']
            result['coordinates'] = (
                max(0, min(width, int(x))),
                max(0, min(height, int(y)))
            )
        
        logger.info(f"🎯 Vision AI: {result.get('screen_type')} | {result.get('objective')} | Confidence: {result['confidence']:.2f}")
        
        return result
    
    def _call_llava_local(self, screenshot_path: str, context: Dict, history: List[Dict]) -> Dict:
        """
        Future: Call local LLaVA model
        
        For unlimited usage without API costs.
        Requires: pip install llava
        """
        # Implementation placeholder
        pass
    
    def set_api_key(self, api_key: str):
        """Enable Vision AI by setting API key"""
        self.api_key = api_key
        self.enabled = True
        logger.info(f"✅ Vision AI enabled with {self.model_type}")
    
    def disable(self):
        """Disable Vision AI"""
        self.enabled = False
        logger.info("❌ Vision AI disabled")


class HybridGameIntelligence:
    """
    Phase 2: Hybrid approach combining CV + Vision AI
    
    Strategy:
    - Use fast CV/OCR for quick decisions (< 100ms)
    - Use Vision AI for complex situations (2-3 seconds)
    - Cache Vision AI results to save API calls
    """
    
    def __init__(self, vision_agent: VisionAIAgent, cv_agent):
        self.vision_agent = vision_agent
        self.cv_agent = cv_agent
        self.vision_cache = {}  # Cache recent Vision AI responses
        self.call_count = 0
        self.max_calls_per_session = 100  # Rate limit
        
    def analyze_and_decide(
        self,
        screenshot_path: str,
        ocr_data: Dict,
        ui_elements: List[Dict],
        stuck_count: int = 0
    ) -> Dict:
        """
        Decide whether to use CV or Vision AI
        
        Rules:
        1. Always try CV first (fast)
        2. Use Vision AI if:
           - CV confidence < 0.5
           - Stuck for 3+ actions
           - New screen type detected
        3. Cache Vision AI results
        """
        
        # Quick CV analysis first
        cv_decision = self.cv_agent.analyze_and_decide(
            screenshot_path, ocr_data, ui_elements
        )
        
        # Check if we need Vision AI
        needs_vision_ai = (
            cv_decision.get('confidence', 0) < 0.5 or
            stuck_count >= 3 or
            self._is_new_screen_type(screenshot_path)
        )
        
        if needs_vision_ai and self.vision_agent.enabled and self.call_count < self.max_calls_per_session:
            logger.info("🔍 Using Vision AI for complex decision")
            vision_decision = self.vision_agent.analyze_game_screenshot(
                screenshot_path,
                context={'ocr': ocr_data, 'ui': ui_elements},
                history=self._get_recent_history()
            )
            self.call_count += 1
            return self._merge_decisions(cv_decision, vision_decision)
        
        return cv_decision
    
    def _is_new_screen_type(self, screenshot_path: str) -> bool:
        """Check if this is a new type of screen"""
        # Simple perceptual hash comparison
        return False  # Placeholder
    
    def _get_recent_history(self) -> List[Dict]:
        """Get recent action history"""
        return []  # Placeholder
    
    def _merge_decisions(self, cv_decision: Dict, vision_decision: Dict) -> Dict:
        """Merge CV and Vision AI decisions, preferring Vision AI"""
        merged = cv_decision.copy()
        merged.update({
            'vision_enhanced': True,
            'vision_confidence': vision_decision.get('confidence', 0),
            'vision_reasoning': vision_decision.get('reasoning', ''),
        })
        
        # Prefer Vision AI action if confidence is higher
        if vision_decision.get('confidence', 0) > cv_decision.get('confidence', 0):
            merged['action'] = vision_decision.get('recommended_action', cv_decision['action'])
            merged['reasoning'] = f"Vision AI: {vision_decision.get('reasoning', '')}"
            merged['confidence'] = vision_decision['confidence']
        
        return merged


class LLaVAAgent:
    """
    Local LLaVA Vision-Language Model - FREE unlimited usage
    Runs on your hardware (GPU recommended but CPU works)
    
    Advantages:
    - Completely free, no API limits
    - Runs offline
    - Privacy (no data sent to cloud)
    
    Disadvantages:
    - Slower than cloud APIs (3-10 seconds per inference on CPU)
    - Requires ~10GB RAM
    - First load downloads ~7GB model
    """
    
    def __init__(self, model_name: str = "llava-hf/llava-1.5-7b-hf"):
        self.model_name = model_name
        self.enabled = False
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if not LLAVA_AVAILABLE:
            logger.warning("LLaVA dependencies not installed")
            return
        
        try:
            logger.info(f"🤖 Loading LLaVA model (this may take a few minutes first time)...")
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = LlavaForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            ).to(self.device)
            self.enabled = True
            logger.info(f"✅ LLaVA initialized on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load LLaVA: {e}")
            self.enabled = False
    
    def analyze_game_screenshot(
        self,
        screenshot_path: str,
        context: Dict,
        history: List[Dict],
        screen_dimensions: Tuple[int, int]
    ) -> Dict:
        """
        Analyze game screenshot using local LLaVA model
        """
        if not self.enabled:
            return self._fallback_response()
        
        try:
            # Load image
            image = Image.open(screenshot_path).convert('RGB')
            
            # Create prompt (simpler than Gemini since LLaVA has smaller context window)
            prompt = """USER: <image>
You are playing a mobile game. Describe what you see and suggest the best action.

What do you see on screen?
What should the player do next?
Where should they tap? Give coordinates.

ASSISTANT:"""
            
            # Process inputs
            inputs = self.processor(prompt, image, return_tensors='pt').to(self.device)
            
            # Generate response
            logger.info("🤖 LLaVA analyzing...")
            output = self.model.generate(**inputs, max_new_tokens=200, do_sample=False)
            response = self.processor.decode(output[0], skip_special_tokens=True)
            
            logger.info(f"LLaVA response: {response[:200]}")
            
            # Parse response (LLaVA responses are more freeform, need simple parsing)
            return self._parse_llava_response(response, screen_dimensions)
            
        except Exception as e:
            logger.error(f"LLaVA inference error: {e}")
            return self._fallback_response()
    
    def _parse_llava_response(self, response: str, screen_dimensions: Tuple[int, int]) -> Dict:
        """Parse LLaVA's natural language response into action dict"""
        width, height = screen_dimensions
        response_lower = response.lower()
        
        # Detect screen type
        screen_type = "gameplay"
        if any(word in response_lower for word in ["menu", "start", "play button"]):
            screen_type = "menu"
        elif any(word in response_lower for word in ["complete", "victory", "next level"]):
            screen_type = "completion"
        
        # Extract action (LLaVA might say "tap", "click", "press", etc.)
        action = "tap"
        if "swipe" in response_lower or "drag" in response_lower:
            action = "swipe"
        
        # Try to extract coordinates from response
        # LLaVA might say things like "tap at center" or "click the button in bottom right"
        coordinates = self._extract_coordinates(response_lower, width, height)
        
        return {
            "screen_type": screen_type,
            "screen_understanding": response[:200],
            "objective": "Progress in game",
            "action": action,
            "coordinates": coordinates,
            "confidence": 0.6,  # LLaVA is good but not as game-specific as Gemini with our prompt
            "reasoning": response,
            "vision_ai_enabled": True
        }
    
    def _extract_coordinates(self, text: str, width: int, height: int) -> List[int]:
        """Extract coordinates from natural language description"""
        # Simple heuristic-based coordinate extraction
        if "center" in text or "middle" in text:
            return [width // 2, height // 2]
        elif "bottom" in text:
            if "right" in text:
                return [3 * width // 4, 3 * height // 4]
            elif "left" in text:
                return [width // 4, 3 * height // 4]
            else:
                return [width // 2, 3 * height // 4]
        elif "top" in text:
            if "right" in text:
                return [3 * width // 4, height // 4]
            elif "left" in text:
                return [width // 4, height // 4]
            else:
                return [width // 2, height // 4]
        elif "right" in text:
            return [3 * width // 4, height // 2]
        elif "left" in text:
            return [width // 4, height // 2]
        
        # Default to center
        return [width // 2, height // 2]
    
    def _fallback_response(self) -> Dict:
        """Fallback response when LLaVA is not available"""
        return {
            "screen_understanding": "LLaVA not available",
            "objective": "Unknown",
            "recommended_action": None,
            "confidence": 0.0,
            "reasoning": "LLaVA model not loaded",
            "vision_ai_enabled": False
        }
