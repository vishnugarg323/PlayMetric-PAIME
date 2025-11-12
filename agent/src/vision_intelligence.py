"""
Vision Intelligence Module - Advanced Game Understanding
Supports multiple vision models: LLaVA (local), GPT-4V, Gemini Vision
"""

import os
import logging
import base64
import asyncio
from typing import Dict, List, Optional, Tuple
import httpx
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)


class VisionIntelligence:
    """
    Advanced vision AI for deep game understanding
    Supports: LLaVA (local), GPT-4V, Gemini Vision
    """
    
    def __init__(
        self,
        model_type: str = "auto",  # auto, llava, gpt4v, gemini
        llava_url: str = None,
        openai_api_key: str = None,
        gemini_api_key: str = None
    ):
        self.model_type = model_type
        self.llava_url = llava_url or os.getenv("LLAVA_URL", "http://localhost:8080")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        # Auto-detect best available model
        if self.model_type == "auto":
            self.model_type = self._detect_best_model()
        
        logger.info(f"🧠 Vision Intelligence initialized with model: {self.model_type}")
    
    def _detect_best_model(self) -> str:
        """Auto-detect best available vision model"""
        # Try LLaVA (local, free, unlimited) - check if transformers is installed
        try:
            import transformers
            logger.info("✅ LLaVA dependencies detected (transformers available)")
            return "llava"
        except ImportError:
            logger.debug("LLaVA not available (transformers not installed)")
        
        # Try Gemini (cloud, free tier)
        if self.gemini_api_key:
            logger.info("✅ Gemini API key detected")
            return "gemini"
        
        # Try GPT-4V (cloud, paid)
        if self.openai_api_key:
            logger.info("✅ OpenAI API key detected")
            return "gpt4v"
        
        # No vision AI available
        logger.warning("⚠️  No vision AI available - will use basic OCR/CV only")
        return "none"
    
    @property
    def vision_available(self) -> bool:
        """Check if any vision model is available"""
        return self.model_type != "none"
    
    async def analyze_game_screen(
        self,
        screenshot_path: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Analyze game screenshot to understand what's happening
        
        Returns:
        {
            "scene_type": "level_selection|gameplay|menu|dialog|loading",
            "game_context": "description of what's happening",
            "ui_elements": [{"type": "button", "text": "START", "position": [x, y]}],
            "available_actions": ["tap_start", "swipe_left", "go_back"],
            "recommended_action": {"type": "tap", "target": "start_button", "confidence": 0.9},
            "level_info": {"current_level": 5, "progress": "50%"},
            "obstacles": ["moving_enemy", "locked_door"],
            "collectibles": ["coin", "star"],
            "game_state": "active|paused|won|lost"
        }
        """
        if self.model_type == "llava":
            return await self._analyze_with_llava(screenshot_path, context)
        elif self.model_type == "gemini":
            return await self._analyze_with_gemini(screenshot_path, context)
        elif self.model_type == "gpt4v":
            return await self._analyze_with_gpt4v(screenshot_path, context)
        else:
            return self._fallback_analysis(screenshot_path)
    
    async def _analyze_with_llava(self, screenshot_path: str, context: str) -> Dict:
        """Use LLaVA (local model) for vision analysis"""
        try:
            # Import LLaVA dependencies
            from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
            import torch
            from PIL import Image
            
            logger.info("🔮 Loading LLaVA model (first time may take 5-10 min to download ~7GB)...")
            
            # Load model (cached after first download)
            model_id = "llava-hf/llava-v1.6-mistral-7b-hf"
            processor = LlavaNextProcessor.from_pretrained(model_id)
            model = LlavaNextForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else "cpu",
                low_cpu_mem_usage=True
            )
            
            # Load image
            image = Image.open(screenshot_path)
            
            # Build prompt
            prompt = f"""[INST] <image>\nYou are analyzing a mobile game screenshot. {context or ''}

Analyze this game screen and provide:
1. Scene type (menu, gameplay, dialog, loading, game_over)
2. What's happening in the game
3. UI elements visible (buttons, menus, text)
4. Recommended action to progress
5. Game state and level info if visible

Respond in JSON format. [/INST]"""
            
            # Process
            inputs = processor(prompt, image, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=512)
            
            # Decode response
            response_text = processor.decode(output[0], skip_special_tokens=True)
            
            logger.info(f"✅ LLaVA analysis complete")
            
            # Parse response (simplified - should parse JSON)
            return {
                "scene_type": "gameplay",
                "game_context": response_text,
                "recommended_action": {"action": "tap", "confidence": 0.7},
                "raw_response": response_text
            }
            
        except ImportError as e:
            logger.error(f"LLaVA dependencies not available: {e}")
            return self._fallback_analysis(screenshot_path)
        except Exception as e:
            logger.error(f"LLaVA analysis failed: {e}")
            return self._fallback_analysis(screenshot_path)
    
    async def _analyze_with_gemini(self, screenshot_path: str, context: str) -> Dict:
        """Use Gemini Vision API for analysis"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Load image
            image = Image.open(screenshot_path)
            
            prompt = self._build_game_analysis_prompt(context)
            
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, image]
            )
            
            return self._parse_vision_analysis(response.text)
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return self._fallback_analysis(screenshot_path)
    
    async def _analyze_with_gpt4v(self, screenshot_path: str, context: str) -> Dict:
        """Use GPT-4 Vision API for analysis"""
        try:
            # Read and encode image
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            prompt = self._build_game_analysis_prompt(context)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-vision-preview",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                                ]
                            }
                        ],
                        "max_tokens": 1000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis_text = result['choices'][0]['message']['content']
                    return self._parse_vision_analysis(analysis_text)
                else:
                    logger.error(f"GPT-4V error: {response.status_code}")
                    return self._fallback_analysis(screenshot_path)
                    
        except Exception as e:
            logger.error(f"GPT-4V analysis failed: {e}")
            return self._fallback_analysis(screenshot_path)
    
    def _build_game_analysis_prompt(self, context: Optional[str]) -> str:
        """Build prompt for game screen analysis"""
        prompt = """Analyze this mobile game screenshot and provide detailed information in JSON format:

{
  "scene_type": "gameplay|menu|level_selection|dialog|loading|game_over|victory",
  "game_context": "Brief description of what's happening",
  "ui_elements": [
    {"type": "button|slider|text|icon", "text": "visible text", "position": "top-left|center|bottom-right", "purpose": "what it does"}
  ],
  "available_actions": ["tap_button", "swipe_direction", "drag_object"],
  "recommended_action": {
    "type": "tap|swipe|drag",
    "target": "what to interact with",
    "reason": "why this action",
    "confidence": 0.0-1.0
  },
  "level_info": {
    "current_level": "level number if visible",
    "progress": "progress percentage if visible",
    "score": "current score if visible"
  },
  "game_elements": {
    "obstacles": ["list of obstacles visible"],
    "collectibles": ["items to collect"],
    "enemies": ["enemies visible"],
    "player": "player position/state"
  },
  "game_state": "playing|paused|won|lost|idle"
}

"""
        if context:
            prompt += f"\n\nAdditional context: {context}"
        
        prompt += "\n\nProvide ONLY the JSON response, no additional text."
        
        return prompt
    
    def _parse_vision_analysis(self, analysis_text: str) -> Dict:
        """Parse vision model response into structured data"""
        try:
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: create structure from text
                return {
                    "scene_type": "unknown",
                    "game_context": analysis_text[:200],
                    "ui_elements": [],
                    "available_actions": ["tap_screen"],
                    "recommended_action": {"type": "tap", "target": "screen", "confidence": 0.3},
                    "game_state": "unknown"
                }
        except Exception as e:
            logger.error(f"Failed to parse vision analysis: {e}")
            return self._fallback_analysis(None)
    
    def _fallback_analysis(self, screenshot_path: Optional[str]) -> Dict:
        """Fallback analysis when vision AI not available"""
        return {
            "scene_type": "unknown",
            "game_context": "Vision AI not available - using basic analysis",
            "ui_elements": [],
            "available_actions": ["tap_screen", "swipe_up", "swipe_down"],
            "recommended_action": {
                "type": "tap",
                "target": "center",
                "reason": "exploration",
                "confidence": 0.3
            },
            "level_info": {},
            "game_elements": {
                "obstacles": [],
                "collectibles": [],
                "enemies": []
            },
            "game_state": "unknown"
        }
    
    async def compare_screens(
        self,
        before_screenshot: str,
        after_screenshot: str
    ) -> Dict:
        """
        Compare two screenshots to understand what changed
        
        Returns:
        {
            "changed": true,
            "change_type": "level_complete|screen_transition|ui_update|no_change",
            "description": "what changed",
            "progress_made": true/false,
            "new_elements": ["list of new UI elements"],
            "removed_elements": ["list of removed elements"]
        }
        """
        if self.model_type in ["llava", "gemini", "gpt4v"]:
            return await self._ai_compare_screens(before_screenshot, after_screenshot)
        else:
            return self._basic_compare_screens(before_screenshot, after_screenshot)
    
    async def _ai_compare_screens(self, before: str, after: str) -> Dict:
        """Use AI to compare screenshots"""
        prompt = """Compare these two mobile game screenshots (before and after an action).
Analyze what changed and provide JSON:

{
  "changed": true/false,
  "change_type": "level_complete|new_screen|dialog_appeared|progress|no_change",
  "description": "what changed between screens",
  "progress_made": true/false,
  "new_elements": ["new UI elements or game objects"],
  "removed_elements": ["what disappeared"],
  "outcome": "positive|negative|neutral"
}

Provide ONLY JSON, no additional text."""

        # For now, use basic comparison
        # Full implementation would send both images to vision model
        return self._basic_compare_screens(before, after)
    
    def _basic_compare_screens(self, before: str, after: str) -> Dict:
        """Basic pixel-based screen comparison"""
        try:
            import cv2
            
            img1 = cv2.imread(before)
            img2 = cv2.imread(after)
            
            if img1 is None or img2 is None:
                return {"changed": False, "change_type": "error"}
            
            # Resize if needed
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # Calculate difference
            diff = cv2.absdiff(img1, img2)
            diff_percent = (np.count_nonzero(diff) / diff.size) * 100
            
            changed = diff_percent > 5.0  # More than 5% different
            
            return {
                "changed": changed,
                "change_type": "screen_update" if changed else "no_change",
                "description": f"{diff_percent:.1f}% of pixels changed",
                "progress_made": changed,
                "difference_percent": diff_percent
            }
            
        except Exception as e:
            logger.error(f"Screen comparison failed: {e}")
            return {"changed": False, "change_type": "error"}
    
    async def evaluate_action_outcome(
        self,
        before_screenshot: str,
        action: Dict,
        after_screenshot: str
    ) -> Dict:
        """
        Evaluate whether an action had a positive outcome
        
        Returns:
        {
            "success": true/false,
            "outcome_type": "progress|stuck|negative|neutral",
            "reward_score": -100 to 100,
            "explanation": "why this outcome",
            "learned_pattern": "if screen has X, action Y leads to Z"
        }
        """
        comparison = await self.compare_screens(before_screenshot, after_screenshot)
        
        # Basic evaluation
        reward_score = 0
        outcome_type = "neutral"
        explanation = ""
        
        if comparison.get("changed"):
            reward_score += 10
            outcome_type = "progress"
            explanation = "Action caused screen change"
            
            if comparison.get("change_type") == "level_complete":
                reward_score += 50
                outcome_type = "progress"
                explanation = "Level completed!"
        else:
            reward_score -= 5
            outcome_type = "stuck"
            explanation = "No visible change - might be stuck"
        
        return {
            "success": reward_score > 0,
            "outcome_type": outcome_type,
            "reward_score": reward_score,
            "explanation": explanation,
            "learned_pattern": f"Action {action.get('type')} at {action.get('position')} -> {outcome_type}"
        }
