"""
Intelligent Batch Processing for 16 FPS Game Analysis

Strategy:
1. Sample keyframes (not all 16 frames) - detect scene changes
2. Parallel OCR for fast text extraction
3. Use BLIP-2 only when scene changes detected
4. Cache recent analysis to avoid redundant processing
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class FrameAnalysisCache:
    """Cache recent frame analysis to avoid redundant BLIP-2 calls"""
    
    def __init__(self, ttl_seconds: int = 2):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get_frame_hash(self, image: Image.Image) -> str:
        """Quick perceptual hash of image"""
        # Resize to 8x8 and convert to grayscale for fast comparison
        small = image.resize((8, 8), Image.Resampling.LANCZOS).convert('L')
        pixels = np.array(small).flatten()
        avg = pixels.mean()
        bits = ''.join(['1' if p > avg else '0' for p in pixels])
        return hashlib.md5(bits.encode()).hexdigest()
    
    def get(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """Get cached analysis if frame is similar"""
        frame_hash = self.get_frame_hash(image)
        
        if frame_hash in self.cache:
            cached_data, timestamp = self.cache[frame_hash]
            if datetime.now() - timestamp < self.ttl:
                logger.info(f"✅ Cache HIT - reusing analysis (hash: {frame_hash[:8]})")
                return cached_data
            else:
                del self.cache[frame_hash]
        
        return None
    
    def set(self, image: Image.Image, analysis: Dict[str, Any]):
        """Cache analysis result"""
        frame_hash = self.get_frame_hash(image)
        self.cache[frame_hash] = (analysis, datetime.now())
        
        # Clean old entries
        self._cleanup()
    
    def _cleanup(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired = [k for k, (_, ts) in self.cache.items() if now - ts > self.ttl]
        for k in expired:
            del self.cache[k]


class GameplayBatchProcessor:
    """Process 16 FPS gameplay frames intelligently"""
    
    def __init__(self, ocr_reader, blip_model, blip_processor):
        self.ocr_reader = ocr_reader
        self.blip_model = blip_model
        self.blip_processor = blip_processor
        self.cache = FrameAnalysisCache(ttl_seconds=2)
        self.last_scene_type = None
        self.frame_buffer = []
    
    def detect_scene_change(self, images: List[Image.Image]) -> bool:
        """Detect if scene changed between frames (fast check)"""
        if len(images) < 2:
            return True
        
        # Compare first and last frame
        hash1 = self.cache.get_frame_hash(images[0])
        hash2 = self.cache.get_frame_hash(images[-1])
        
        # If hashes differ significantly, scene likely changed
        return hash1 != hash2
    
    async def process_frame_batch(
        self,
        image_paths: List[str],
        use_blip: bool = True,
        detect_clicks: bool = False
    ) -> Dict[str, Any]:
        """
        Process batch of 16 frames intelligently
        
        Args:
            image_paths: List of 16 frame paths captured in 1 second
            use_blip: Whether to use BLIP-2 (slow) or just OCR (fast)
            detect_clicks: Whether to detect user click locations
        
        Returns:
            Aggregated analysis from all frames
        """
        start_time = datetime.now()
        
        # Load all images
        images = [Image.open(path).convert("RGB") for path in image_paths]
        logger.info(f"📦 Processing batch of {len(images)} frames...")
        
        # Strategy 1: Check cache for first frame
        cached_result = self.cache.get(images[0])
        if cached_result and not self.detect_scene_change(images):
            logger.info("⚡ Using cached analysis - scene unchanged")
            return cached_result
        
        # Strategy 2: Fast OCR on all frames in parallel
        ocr_results = await self._batch_ocr(images)
        
        # Strategy 3: Sample keyframes (first, middle, last)
        keyframe_indices = [0, len(images) // 2, -1]
        keyframes = [images[i] for i in keyframe_indices]
        
        # Strategy 4: Use BLIP-2 only on middle keyframe (representative)
        if use_blip:
            blip_result = await self._analyze_with_blip(keyframes[1])
        else:
            blip_result = {
                "scene_type": "gameplay",
                "description": "OCR-only mode",
                "confidence": 0.5
            }
        
        # Strategy 5: Detect UI changes across frames
        ui_changes = self._detect_ui_changes(ocr_results)
        
        # Strategy 6: Detect potential click locations if requested
        click_locations = []
        if detect_clicks:
            click_locations = self._detect_click_candidates(images, ocr_results)
        
        # Aggregate results
        result = {
            "timestamp": start_time.isoformat(),
            "frame_count": len(images),
            "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "scene_type": blip_result.get("scene_type", "unknown"),
            "description": blip_result.get("description", ""),
            "confidence": blip_result.get("confidence", 0.0),
            "ocr_text": self._aggregate_ocr(ocr_results),
            "ui_elements": ui_changes,
            "click_candidates": click_locations,
            "recommended_action": self._determine_action(blip_result, ocr_results, click_locations)
        }
        
        # Cache result
        self.cache.set(images[0], result)
        
        logger.info(f"✅ Batch processed in {result['processing_time_ms']:.0f}ms")
        return result
    
    async def _batch_ocr(self, images: List[Image.Image]) -> List[List[tuple]]:
        """Run OCR on sampled images (not all - too slow)"""
        # Only OCR every 4th frame to save time
        sampled_indices = list(range(0, len(images), 4))
        results = [[] for _ in images]  # Empty results for all frames
        
        for idx in sampled_indices:
            # Downscale for faster OCR
            small_img = images[idx].resize(
                (images[idx].width // 3, images[idx].height // 3), 
                Image.Resampling.LANCZOS
            )
            try:
                ocr_result = await asyncio.to_thread(
                    self.ocr_reader.readtext, 
                    np.array(small_img)
                )
                results[idx] = ocr_result if ocr_result else []
            except Exception as e:
                logger.error(f"OCR failed for frame {idx}: {e}")
                results[idx] = []
        
        return results
    
    async def _analyze_with_blip(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze single frame with BLIP-2"""
        import torch
        
        # Downscale for faster inference
        max_size = 384  # Even smaller than 512 for speed
        if image.width > max_size or image.height > max_size:
            ratio = min(max_size / image.width, max_size / image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        prompt = "Question: What is happening in this mobile game screen? Answer:"
        inputs = self.blip_processor(images=image, text=prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.blip_model.generate(
                **inputs,
                max_new_tokens=100,  # Reduced for speed
                num_beams=1,
                do_sample=False
            )
        
        response_text = self.blip_processor.decode(outputs[0], skip_special_tokens=True)
        
        # Parse scene type
        response_lower = response_text.lower()
        scene_type = "gameplay"
        if "menu" in response_lower:
            scene_type = "menu"
        elif "loading" in response_lower:
            scene_type = "loading"
        elif "reward" in response_lower or "victory" in response_lower:
            scene_type = "reward"
        elif "game over" in response_lower:
            scene_type = "game_over"
        
        return {
            "scene_type": scene_type,
            "description": response_text,
            "confidence": 0.8
        }
    
    def _aggregate_ocr(self, ocr_results: List[List[tuple]]) -> str:
        """Combine OCR text from all frames"""
        all_texts = []
        for frame_ocr in ocr_results:
            for detection in frame_ocr:
                if len(detection) >= 2:
                    text = detection[1]
                    if text.strip():
                        all_texts.append(text)
        
        # Remove duplicates while preserving order
        unique_texts = list(dict.fromkeys(all_texts))
        return " ".join(unique_texts[:20])  # Limit to top 20 texts
    
    def _detect_ui_changes(self, ocr_results: List[List[tuple]]) -> List[str]:
        """Detect UI elements that appeared across frames"""
        # Track which texts appeared in multiple frames (likely UI elements)
        text_frequency = {}
        for frame_ocr in ocr_results:
            frame_texts = set()
            for detection in frame_ocr:
                if len(detection) >= 2:
                    text = detection[1].strip().lower()
                    if text and len(text) > 2:
                        frame_texts.add(text)
            
            for text in frame_texts:
                text_frequency[text] = text_frequency.get(text, 0) + 1
        
        # UI elements appear in most frames (threshold: 50%)
        threshold = len(ocr_results) * 0.5
        ui_elements = [text for text, freq in text_frequency.items() if freq >= threshold]
        
        return sorted(ui_elements)[:10]  # Top 10 UI elements
    
    def _detect_click_candidates(
        self,
        images: List[Image.Image],
        ocr_results: List[List[tuple]]
    ) -> List[Dict[str, Any]]:
        """Detect potential clickable UI elements"""
        candidates = []
        
        # Use OCR bounding boxes from middle frame
        if len(ocr_results) > 8:
            middle_ocr = ocr_results[8]  # Middle of 16 frames
            
            for detection in middle_ocr:
                if len(detection) >= 3:
                    bbox, text, confidence = detection[:3]
                    
                    # Only consider high-confidence detections
                    if confidence > 0.7 and len(text.strip()) > 0:
                        # Calculate center of bounding box
                        x_coords = [p[0] for p in bbox]
                        y_coords = [p[1] for p in bbox]
                        center_x = int(sum(x_coords) / len(x_coords))
                        center_y = int(sum(y_coords) / len(y_coords))
                        
                        candidates.append({
                            "text": text,
                            "x": center_x,
                            "y": center_y,
                            "confidence": confidence,
                            "type": self._classify_ui_element(text)
                        })
        
        return candidates[:5]  # Top 5 candidates
    
    def _classify_ui_element(self, text: str) -> str:
        """Classify UI element type"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['play', 'start', 'continue', 'next']):
            return 'action_button'
        elif any(word in text_lower for word in ['close', 'back', 'exit']):
            return 'navigation'
        elif any(word in text_lower for word in ['settings', 'menu', 'options']):
            return 'menu'
        else:
            return 'label'
    
    def _determine_action(
        self,
        blip_result: Dict[str, Any],
        ocr_results: List[List[tuple]],
        click_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine recommended action based on analysis"""
        scene_type = blip_result.get("scene_type", "gameplay")
        
        # If we have clickable buttons, prioritize action buttons
        if click_candidates:
            action_buttons = [c for c in click_candidates if c['type'] == 'action_button']
            if action_buttons:
                btn = action_buttons[0]
                return {
                    "action": "tap",
                    "x": btn['x'],
                    "y": btn['y'],
                    "reason": f"Click '{btn['text']}' button",
                    "confidence": btn['confidence']
                }
        
        # Scene-specific actions
        if scene_type == "menu":
            return {"action": "tap", "x": 540, "y": 960, "reason": "Tap center to continue"}
        elif scene_type == "loading":
            return {"action": "wait", "reason": "Wait for loading to complete"}
        elif scene_type == "reward":
            return {"action": "tap", "x": 540, "y": 1200, "reason": "Collect reward"}
        elif scene_type == "game_over":
            return {"action": "tap", "x": 540, "y": 960, "reason": "Restart game"}
        else:
            return {"action": "observe", "reason": "Continue observing gameplay"}
