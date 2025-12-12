"""
Video Analysis Pipeline - Extract frames, detect touches, analyze gameplay

This module processes uploaded gameplay videos to extract learning data:
1. Frame extraction at configurable FPS
2. Touch point detection (from touch visualization overlay)
3. Screen analysis (OCR, UI elements, scene classification)
4. Action-outcome mapping
5. Database storage (video_demonstrations, video_frames, learning_data)
"""
import os
import logging
import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class TouchDetector:
    """Detect touch points from visual overlay in gameplay videos"""
    
    def __init__(self):
        # Touch visualization typically uses bright colors (white, yellow, red)
        # We look for circular bright spots that appear briefly
        self.touch_color_ranges = [
            # White/bright touches
            (np.array([0, 0, 200]), np.array([180, 50, 255])),  # HSV
            # Yellow touches
            (np.array([20, 100, 200]), np.array([35, 255, 255])),
            # Red touches
            (np.array([0, 100, 200]), np.array([10, 255, 255]))
        ]
        self.min_radius = 10
        self.max_radius = 100
    
    def detect_touch(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Detect touch point in frame
        
        Returns:
            {
                'x': int,
                'y': int,
                'type': 'tap' | 'swipe_start' | 'swipe_end' | 'hold',
                'radius': int,
                'confidence': float
            }
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = frame.shape[:2]
        
        # Create combined mask for all touch colors
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        for lower, upper in self.touch_color_ranges:
            mask = cv2.inRange(hsv, lower, upper)
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # Find circles (touch points)
        circles = cv2.HoughCircles(
            combined_mask,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=15,
            minRadius=self.min_radius,
            maxRadius=self.max_radius
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            # Get the brightest/largest circle
            best_circle = circles[0][0]  # First detected circle
            x, y, r = best_circle
            
            # Determine touch type (simplified - could be enhanced with temporal analysis)
            touch_type = 'tap'
            confidence = 0.8
            
            return {
                'x': int(x),
                'y': int(y),
                'type': touch_type,
                'radius': int(r),
                'confidence': confidence
            }
        
        return None


class VideoAnalyzer:
    """Main video analysis pipeline"""
    
    def __init__(self, db_manager, vision_service_url: str = "http://vision:8006"):
        self.db_manager = db_manager
        self.vision_service_url = vision_service_url
        self.touch_detector = TouchDetector()
        self.frame_analysis_cache = {}
    
    async def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract video metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return {}
            
            data = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            if not video_stream:
                return {}
            
            duration = float(data['format'].get('duration', 0))
            fps = eval(video_stream.get('r_frame_rate', '30/1'))  # e.g., "30/1" -> 30.0
            frame_count = int(video_stream.get('nb_frames', 0))
            
            # If frame_count not available, calculate it
            if frame_count == 0 and duration > 0:
                frame_count = int(duration * fps)
            
            return {
                'duration_seconds': duration,
                'fps': fps,
                'frame_count': frame_count,
                'resolution': f"{video_stream.get('width')}x{video_stream.get('height')}",
                'codec': video_stream.get('codec_name'),
                'bitrate': int(data['format'].get('bit_rate', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get video metadata: {e}")
            return {}
    
    async def extract_frames(
        self, 
        video_path: str, 
        output_dir: str, 
        fps: float = 2.0,
        max_frames: Optional[int] = None
    ) -> List[str]:
        """
        Extract frames from video using ffmpeg
        
        Args:
            video_path: Path to video file
            output_dir: Directory to save frames
            fps: Target frames per second to extract (default 2 FPS = 1 frame every 0.5s)
            max_frames: Optional limit on total frames
            
        Returns:
            List of frame file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Use ffmpeg for fast frame extraction
        frame_pattern = str(output_path / "frame_%06d.png")
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'fps={fps}',
            '-vsync', 'vfr',  # Variable frame rate
            '-frame_pts', '1',
            frame_pattern
        ]
        
        if max_frames:
            cmd.extend(['-vframes', str(max_frames)])
        
        logger.info(f"🎬 Extracting frames: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            
            if result.returncode != 0:
                logger.error(f"ffmpeg failed: {result.stderr}")
                return []
            
            # Get list of extracted frames
            frame_paths = sorted(output_path.glob("frame_*.png"))
            logger.info(f"✅ Extracted {len(frame_paths)} frames")
            
            return [str(p) for p in frame_paths]
            
        except subprocess.TimeoutExpired:
            logger.error("Frame extraction timed out")
            return []
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return []
    
    async def analyze_frame_with_vision(self, frame_path: str) -> Dict[str, Any]:
        """Call vision service to analyze frame using parallel multi-method analysis"""
        try:
            async with aiohttp.ClientSession() as session:
                # Parallel analysis endpoint (OCR + BLIP-2 + OpenCV + Template Matching)
                async with session.post(
                    f"{self.vision_service_url}/analyze/parallel",
                    json={
                        "screenshot_path": frame_path
                    },
                    timeout=aiohttp.ClientTimeout(total=240)  # Increased for BLIP-2 on CPU (can take 60-120s per frame)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        
                        # Log worker info for load balancing verification
                        worker_id = result.get('worker_id', 'unknown')
                        analysis_time = result.get('analysis_time', 0)
                        methods = result.get('methods_used', [])
                        logger.info(f"Frame analyzed by worker {worker_id} in {analysis_time:.2f}s using {', '.join(methods)}")
                        
                        return result
                    else:
                        error_text = await resp.text()
                        logger.warning(f"Vision service returned {resp.status}: {error_text}")
                        return {}
        except asyncio.TimeoutError as e:
            logger.error(f"Vision analysis timed out after 120s for {frame_path}")
            return {}
        except Exception as e:
            logger.error(f"Vision analysis failed for {frame_path}: {type(e).__name__} - {str(e)}")
            return {}
    
    def classify_scene(self, vision_result: Dict[str, Any], ocr_text: str) -> str:
        """
        Classify scene type based on analysis
        
        Returns: 'menu', 'gameplay', 'dialog', 'victory', 'defeat', 'loading', 'unknown'
        """
        # Check summary from parallel analysis first
        if vision_result.get('summary', {}).get('scene_type'):
            return vision_result['summary']['scene_type']
        
        # Check vision result next
        if vision_result.get('vision', {}).get('scene_type'):
            return vision_result['vision']['scene_type']
        
        # Fallback to OCR-based classification
        text_lower = ocr_text.lower()
        
        if any(word in text_lower for word in ['play', 'start', 'settings', 'menu']):
            return 'menu'
        elif any(word in text_lower for word in ['victory', 'win', 'complete', 'success', 'you won']):
            return 'victory'
        elif any(word in text_lower for word in ['defeat', 'game over', 'failed', 'lost', 'try again']):
            return 'defeat'
        elif any(word in text_lower for word in ['loading', 'please wait']):
            return 'loading'
        elif any(word in text_lower for word in ['score', 'health', 'hp', 'coins', 'level']):
            return 'gameplay'
        else:
            return 'unknown'
    
    async def _analyze_single_frame(
        self,
        frame_path: str,
        frame_num: int,
        timestamp_ms: int,
        video_id: str,
        game_id: str,
        total_frames: int,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Analyze a single frame - designed for parallel execution"""
        try:
            # Read frame
            frame = cv2.imread(frame_path)
            if frame is None:
                logger.warning(f"Failed to read frame: {frame_path}")
                return None
            
            # Detect touch (CPU-bound, fast)
            touch_data = self.touch_detector.detect_touch(frame)
            
            # Vision analysis (I/O-bound, slow - benefits from parallelization)
            vision_result = await self.analyze_frame_with_vision(frame_path)
            
            # Extract data from parallel analysis result
            ocr_data = vision_result.get('ocr', {})
            vision_data = vision_result.get('vision', {})
            ui_data = vision_result.get('ui_detection', {})
            summary = vision_result.get('summary', {})
            
            # Combine OCR text from all detected regions
            ocr_text = ocr_data.get('text', '')
            
            # Get scene type from summary or vision data
            scene_type = self.classify_scene(vision_result, ocr_text)
            
            # Build comprehensive screen analysis
            screen_analysis = {
                'ocr_text': ocr_text,
                'ocr_confidence': ocr_data.get('confidence', 0.0),
                'ocr_regions': ocr_data.get('regions_found', 0),
                'ui_elements': ui_data.get('elements', []),
                'ui_total_detected': ui_data.get('total_detected', 0),
                'scene_description': vision_data.get('description', ''),
                'scene_type': vision_data.get('scene_type', 'unknown'),
                'vision_confidence': vision_data.get('confidence', 0.0),
                'patterns_detected': vision_result.get('patterns', {}).get('detected', []),
                'overall_confidence': summary.get('overall_confidence', 0.5),
                'analysis_methods': vision_result.get('methods_used', []),
                'worker_id': vision_result.get('worker_id', 'unknown'),
                'analysis_time': vision_result.get('analysis_time', 0)
            }
            
            # Save frame record to DB
            frame_record = await self.db_manager.execute_one(
                """
                INSERT INTO video_frames (
                    video_id, frame_number, timestamp_ms, frame_path,
                    touch_detected, touch_x_percent, touch_y_percent, touch_type,
                    ocr_analysis, gemini_analysis, grok_analysis, blip_analysis,
                    opencv_analysis, template_analysis, combined_summary,
                    view_state, recommended_action, expected_result,
                    analyzed_at, worker_id, analysis_time_ms, methods_used, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                RETURNING id
                """,
                video_id,
                frame_num,
                timestamp_ms,
                frame_path,
                touch_data is not None,
                touch_data['x'] if touch_data else None,
                touch_data['y'] if touch_data else None,
                touch_data['type'] if touch_data else None,
                # Store per-model analysis in separate columns for UI display
                json.dumps({'text': screen_analysis.get('ocr_text', ''), 'confidence': screen_analysis.get('ocr_confidence', 0), 'regions_found': screen_analysis.get('ocr_regions', 0)}),
                json.dumps({}),  # gemini_analysis - placeholder for now
                json.dumps({}),  # grok_analysis - placeholder for now
                json.dumps({'description': screen_analysis.get('scene_description', ''), 'confidence': screen_analysis.get('vision_confidence', 0)}),
                json.dumps({'ui_elements': screen_analysis.get('ui_elements', []), 'total_detected': screen_analysis.get('ui_total_detected', 0)}),
                json.dumps({'patterns': screen_analysis.get('patterns_detected', []), 'confidence': 0}),
                json.dumps({'scene_type': scene_type, 'description': screen_analysis.get('scene_description', ''), 'overall_confidence': screen_analysis.get('overall_confidence', 0)}),
                json.dumps({'scene': scene_type, 'ui_elements': screen_analysis.get('ui_elements', [])}),
                json.dumps({'type': 'tap', 'x_percent': touch_data['x'], 'y_percent': touch_data['y']} if touch_data else {}),
                json.dumps({}),  # expected_result
                datetime.now(),
                screen_analysis.get('worker_id', 'unknown'),
                int(screen_analysis.get('analysis_time', 0) * 1000),
                screen_analysis.get('analysis_methods', []),
                json.dumps({'fps': 0.5, 'extraction_time': datetime.now().isoformat()})
            )
            frame_id = str(frame_record['id'])
            
            # If touch detected, create learning_data entry
            action_id = None
            if touch_data:
                action_id = await self._create_learning_data_entry(
                    game_id=game_id,
                    video_id=video_id,
                    frame_path=frame_path,
                    touch_data=touch_data,
                    screen_analysis=screen_analysis,
                    scene_type=scene_type,
                    vision_result=vision_result  # Pass complete vision analysis for comprehensive storage
                )
                # Note: action_id stored in learning_data table, not video_frames
            
            return {
                'frame_path': frame_path,
                'frame_num': frame_num,
                'timestamp_ms': timestamp_ms,
                'touch_data': touch_data,
                'vision_result': vision_result,
                'scene_type': scene_type,
                'screen_analysis': screen_analysis,
                'frame_id': frame_id,
                'action_id': action_id
            }
            
        except Exception as e:
            logger.error(f"Error analyzing frame {frame_num}: {e}")
            return None
    
    async def _build_knowledge_from_results(
        self,
        analyzed_results: list,
        game_id: str,
        video_id: str
    ):
        """Build game knowledge from analyzed results"""
        # This is a placeholder - implement your knowledge building logic here
        logger.info(f"Building knowledge from {len(analyzed_results)} analyzed frames")
        # TODO: Implement pattern recognition, state-action mapping, etc.
    
    async def analyze_video(
        self,
        video_id: str,
        video_path: str,
        game_id: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Complete video analysis pipeline with parallel frame processing
        
        Args:
            video_id: UUID of video_demonstrations record
            video_path: Path to video file
            game_id: Game UUID
            progress_callback: Optional async function(progress_dict) for progress updates
            
        Returns:
            Summary statistics
        """
        start_time = time.time()
        
        # Step 1: Get video metadata
        logger.info(f"📊 Analyzing video metadata: {video_path}")
        metadata = await self.get_video_metadata(video_path)
        
        if not metadata:
            raise ValueError("Failed to read video metadata")
        
        # Update video_demonstrations with metadata
        await self.db_manager.execute_write(
            """
            UPDATE video_demonstrations
            SET duration_seconds = $1,
                frame_count = $2,
                fps = $3,
                resolution = $4,
                processing_status = 'processing'
            WHERE id = $5
            """,
            metadata['duration_seconds'],
            metadata['frame_count'],
            metadata['fps'],
            metadata['resolution'],
            video_id
        )
        
        # Step 2: Extract frames (0.5 FPS = 1 frame every 2 seconds for better learning)
        frames_dir = f"/data/video_frames/{video_id}"
        logger.info(f"🎬 Extracting frames to {frames_dir}")
        
        frame_paths = await self.extract_frames(video_path, frames_dir, fps=2)
        
        if not frame_paths:
            raise ValueError("No frames extracted from video")
        
        # Step 3: Analyze frames with 3-frame lookahead for parallel processing
        # Process 3 frames ahead in parallel (using round-robin workers) 
        # but DISPLAY results sequentially as they complete
        total_frames = len(frame_paths)
        actions_extracted = 0
        touches_detected = 0
        
        logger.info(f"🔍 Analyzing {total_frames} frames with 3-frame parallel lookahead...")
        
        # Start processing first 3 frames in parallel
        max_parallel = 3  # Number of frames to process ahead
        analyzed_results = []
        pending_tasks = {}  # {frame_num: task}
        
        # Kick off first batch
        for i in range(min(max_parallel, total_frames)):
            frame_num = i + 1
            frame_path = frame_paths[i]
            timestamp_ms = int((i / 0.5) * 1000)
            
            task = asyncio.create_task(
                self._analyze_single_frame(
                    frame_path=frame_path,
                    frame_num=frame_num,
                    timestamp_ms=timestamp_ms,
                    video_id=video_id,
                    game_id=game_id,
                    total_frames=total_frames,
                    progress_callback=None  # Don't broadcast during processing
                )
            )
            pending_tasks[frame_num] = task
        
        # Process frames sequentially for display, but maintain 3-frame lookahead
        current_frame = 1
        next_to_start = max_parallel + 1
        
        while current_frame <= total_frames:
            # Wait for current frame to complete
            if current_frame in pending_tasks:
                task = pending_tasks[current_frame]
                try:
                    result = await task
                except Exception as e:
                    logger.error(f"Frame {current_frame} analysis failed: {e}")
                    result = None
                
                del pending_tasks[current_frame]
            else:
                result = None
            
            # Now we have the result for current_frame in sequential order
            # Create a fake batch_results list with just this one result
            batch_results = [result]
            batch_start = current_frame - 1
            
            # Process result for current frame (sequential display)
            for idx, result in enumerate(batch_results):
                frame_num = current_frame
                
                if isinstance(result, Exception):
                    logger.error(f"Frame {frame_num} analysis failed: {result}")
                    # Broadcast failure status
                    if progress_callback:
                        await progress_callback({
                            'stage': 'frame_failed',
                            'current_frame': frame_num,
                            'total_frames': total_frames,
                            'progress_percent': int((frame_num / total_frames) * 100),
                            'error': str(result)
                        })
                    continue
                
                if result is None:
                    logger.warning(f"Frame {frame_num} returned None")
                    # Broadcast None result
                    if progress_callback:
                        await progress_callback({
                            'stage': 'frame_skipped',
                            'current_frame': frame_num,
                            'total_frames': total_frames,
                            'progress_percent': int((frame_num / total_frames) * 100)
                        })
                    continue
                    
                analyzed_results.append(result)
                
                # Count successes
                if result.get('touch_data'):
                    touches_detected += 1
                    actions_extracted += 1
                
                # Send progress update with complete vision analysis data (ALWAYS broadcast, even if vision failed)
                if progress_callback:
                    vision_res = result.get('vision_result', {})
                    
                    # Extract data for insights (with safe fallbacks)
                    ocr_text = vision_res.get('ocr', {}).get('text', '') if vision_res else ''
                    scene_type = vision_res.get('summary', {}).get('scene_type', result.get('scene_type', 'unknown')) if vision_res else 'unknown'
                    scene_description = vision_res.get('vision', {}).get('description', '') if vision_res else ''
                    ui_elements = vision_res.get('ui_detection', {}).get('elements', []) if vision_res else []
                    patterns = vision_res.get('patterns', {}).get('detected', []) if vision_res else []
                    touch_data = result.get('touch_data')
                    
                    # Generate human-readable AI insights
                    insights = []
                    if not vision_res:
                        insights.append("⚠️ Vision analysis unavailable")
                    else:
                        if scene_type and scene_type != "unknown":
                            insights.append(f"🎮 Scene: {scene_type.title()}")
                        if scene_description:
                            insights.append(f"👁️ Vision: {scene_description}")
                        if ocr_text:
                            text_preview = ocr_text[:80] + "..." if len(ocr_text) > 80 else ocr_text
                            insights.append(f"📝 Text: '{text_preview}'")
                        if len(ui_elements) > 0:
                            button_count = sum(1 for el in ui_elements if el.get('type') == 'button')
                            insights.append(f"🎯 Found {len(ui_elements)} UI elements ({button_count} buttons)")
                        if patterns:
                            insights.append(f"🔍 Patterns: {', '.join(patterns[:3])}")
                    if touch_data:
                        insights.append(f"👆 Tap detected at ({touch_data['x']}, {touch_data['y']})")
                    
                    # Build frame data for UI display (6+ rows per user requirement)
                    await progress_callback({
                        'stage': 'frame_analyzed',
                        'current_frame': frame_num,
                        'total_frames': total_frames,
                        'progress_percent': int((frame_num / total_frames) * 100),
                        'current_screenshot': result.get('frame_path', ''),
                        'timestamp_ms': result.get('timestamp_ms', 0),
                        'ai_insights': insights,  # Human-readable summary
                        
                        # Row 1: OCR Results
                        'ocr_analysis': {
                            'text': ocr_text,
                            'confidence': vision_res.get('ocr', {}).get('confidence', 0) if vision_res else 0,
                            'regions_found': vision_res.get('ocr', {}).get('regions_found', 0) if vision_res else 0,
                            'what_learned': f"Detected {len(ocr_text.split())} words" if ocr_text else "No text found"
                        },
                        
                        # Row 2: Gemini Results (if available)
                        'gemini_analysis': {
                            'scene_type': scene_type,
                            'description': vision_res.get('gemini', {}).get('description', 'N/A') if vision_res else 'N/A',
                            'confidence': vision_res.get('gemini', {}).get('confidence', 0) if vision_res else 0,
                            'what_learned': vision_res.get('gemini', {}).get('learning_insight', 'N/A') if vision_res else 'N/A'
                        },
                        
                        # Row 3: Grok Results (if available)
                        'grok_analysis': {
                            'analysis': vision_res.get('grok', {}).get('analysis', 'N/A') if vision_res else 'N/A',
                            'confidence': vision_res.get('grok', {}).get('confidence', 0) if vision_res else 0,
                            'what_learned': vision_res.get('grok', {}).get('insight', 'N/A') if vision_res else 'N/A'
                        },
                        
                        # Row 4: BLIP Results
                        'blip_analysis': {
                            'description': scene_description,
                            'confidence': vision_res.get('vision', {}).get('confidence', 0) if vision_res else 0,
                            'what_learned': f"Scene type: {scene_type}" if scene_type != 'unknown' else "Scene analysis unavailable"
                        },
                        
                        # Row 5: OpenCV Results
                        'opencv_analysis': {
                            'ui_elements': ui_elements,
                            'total_detected': vision_res.get('ui_detection', {}).get('total_detected', 0) if vision_res else 0,
                            'what_learned': f"Found {len(ui_elements)} UI components" if ui_elements else "No UI elements detected"
                        },
                        
                        # Row 6: Template Matching Results
                        'template_analysis': {
                            'patterns': patterns,
                            'confidence': vision_res.get('patterns', {}).get('confidence', 0) if vision_res else 0,
                            'what_learned': f"Recognized {len(patterns)} patterns" if patterns else "No patterns matched"
                        },
                        
                        # Row 7: Combined Summary
                        'combined_summary': {
                            'overall_confidence': vision_res.get('summary', {}).get('overall_confidence', 0) if vision_res else 0,
                            'what_ai_learned': ' | '.join(insights) if insights else 'Frame processed with limited data',
                            'touch_detected': touch_data is not None,
                            'touch_point': {
                                'x': touch_data['x'],
                                'y': touch_data['y'],
                                'type': touch_data['type']
                            } if touch_data else None,
                            'worker_id': vision_res.get('worker_id', 'unknown') if vision_res else 'unknown',
                            'analysis_time_ms': vision_res.get('analysis_time', 0) * 1000 if vision_res else 0
                        }
                    })
            
            # Start processing next frame (maintain 3-frame lookahead)
            if next_to_start <= total_frames:
                next_idx = next_to_start - 1
                frame_path = frame_paths[next_idx]
                timestamp_ms = int((next_idx / 0.5) * 1000)
                
                task = asyncio.create_task(
                    self._analyze_single_frame(
                        frame_path=frame_path,
                        frame_num=next_to_start,
                        timestamp_ms=timestamp_ms,
                        video_id=video_id,
                        game_id=game_id,
                        total_frames=total_frames,
                        progress_callback=None
                    )
                )
                pending_tasks[next_to_start] = task
                next_to_start += 1
            
            # Move to next frame for display
            current_frame += 1
        
        logger.info(f"✅ Parallel analysis complete: {total_frames} frames, {touches_detected} touches, {actions_extracted} actions")
        
        # Step 4: Build knowledge from analyzed results
        logger.info(f"🧠 Building game knowledge from patterns...")
        await self._build_knowledge_from_results(analyzed_results, game_id, video_id)
        
        # Step 4.5: Auto-trigger pattern recognition to build game_knowledge
        try:
            logger.info(f"🔍 Auto-triggering pattern recognition for game: {game_id}")
            from src.pattern_recognition import PatternRecognitionEngine
            pattern_engine = PatternRecognitionEngine(self.db_manager)
            pattern_results = await pattern_engine.analyze_and_build_patterns(
                game_id=game_id,
                min_occurrences=2,  # Lower threshold for video demos
                min_success_rate=0.6
            )
            logger.info(f"✅ Pattern recognition complete: {pattern_results}")
            
            # Send WebSocket update about pattern building
            if hasattr(self, 'progress_callback') and self.progress_callback:
                await self.progress_callback({
                    'type': 'pattern_building_complete',
                    'patterns_created': pattern_results,
                    'game_id': game_id
                })
        except Exception as e:
            logger.error(f"Pattern recognition failed (non-critical): {e}")
        
        # Step 5: Update video_demonstrations summary
        await self.db_manager.execute_write(
            """
            UPDATE video_demonstrations
            SET processing_status = 'completed',
                processed_at = NOW(),
                total_frames_analyzed = $1,
                total_actions_extracted = $2,
                actions_by_type = $3
            WHERE id = $4
            """,
            total_frames,
            actions_extracted,
            json.dumps({'tap': touches_detected}),
            video_id
        )
        
        elapsed = time.time() - start_time
        
        summary = {
            'video_id': video_id,
            'total_frames': total_frames,
            'actions_extracted': actions_extracted,
            'touches_detected': touches_detected,
            'processing_time_seconds': elapsed,
            'fps_analyzed': 0.5,
            'parallel_batches': (total_frames + batch_size - 1) // batch_size
        }
        
        logger.info(f"✅ Parallel video analysis complete: {summary}")
        return summary
    
    async def _create_learning_data_entry(
        self,
        game_id: str,
        video_id: str,
        frame_path: str,
        touch_data: Dict[str, Any],
        screen_analysis: Dict[str, Any],
        scene_type: str,
        vision_result: Dict[str, Any] = None,
        screen_width: int = 1080,
        screen_height: int = 1920
    ) -> str:
        """
        Create comprehensive learning_data entry with ALL extracted information
        This data is critical for AI gameplay - saves OCR, vision, CV detection, patterns, etc.
        """
        
        # Determine action type and parameters
        action_type = touch_data['type']  # tap, swipe_start, etc.
        action_params = {
            'x': touch_data['x'],
            'y': touch_data['y'],
            'source': 'video_demonstration',
            'confidence': touch_data.get('confidence', 0.8)
        }
        
        # Extract comprehensive UI elements from all analysis methods
        ui_elements = []
        ai_insights = []  # Human-readable insights
        
        # From OCR text detection (actual API format)
        if vision_result and vision_result.get('ocr', {}).get('text'):
            ocr_text = vision_result['ocr']['text']
            if ocr_text:  # If text was found
                ui_elements.append({
                    'type': 'text',
                    'text': ocr_text,
                    'confidence': vision_result['ocr'].get('confidence', 0),
                    'regions': vision_result['ocr'].get('regions_found', 0),
                    'source': 'ocr',
                    'description': f"Text: '{ocr_text}' ({vision_result['ocr'].get('regions_found', 0)} regions)"
                })
                ai_insights.append(f"📝 Detected text: '{ocr_text[:50]}{'...' if len(ocr_text) > 50 else ''}' with {round(vision_result['ocr'].get('confidence', 0) * 100)}% confidence")
        
        # From OpenCV UI detection (actual API format)
        if vision_result and vision_result.get('ui_detection', {}).get('elements'):
            for idx, elem in enumerate(vision_result['ui_detection']['elements']):
                x_pct = (elem.get('x', 0) / screen_width) * 100
                y_pct = (elem.get('y', 0) / screen_height) * 100
                w_pct = (elem.get('width', 0) / screen_width) * 100
                h_pct = (elem.get('height', 0) / screen_height) * 100
                
                description = f"{elem.get('type', 'button').title()} at ({x_pct:.1f}%, {y_pct:.1f}%) size {w_pct:.1f}%x{h_pct:.1f}%"
                
                ui_elements.append({
                    'type': elem.get('type', 'button'),
                    'x': elem.get('x', 0),
                    'y': elem.get('y', 0),
                    'x_percent': x_pct,
                    'y_percent': y_pct,
                    'width': elem.get('width', 0),
                    'height': elem.get('height', 0),
                    'width_percent': w_pct,
                    'height_percent': h_pct,
                    'source': 'opencv',
                    'description': description
                })
                
                if idx == 0:  # Only add insight for first few elements
                    ai_insights.append(f"🎯 Found {elem.get('type', 'button')} at ({x_pct:.1f}%, {y_pct:.1f}%)")
        
        # From pattern/template matching (actual API format)
        if vision_result and vision_result.get('patterns', {}).get('detected'):
            for pattern in vision_result['patterns']['detected']:
                ui_elements.append({
                    'type': 'pattern',
                    'pattern_id': pattern,
                    'confidence': vision_result['patterns'].get('confidence', 0),
                    'source': 'template_matching'
                })
        
        # Add scene and action insights
        scene_desc = vision_result.get('vision', {}).get('description', '') if vision_result else ''
        if scene_desc:
            ai_insights.append(f"🎮 Scene: {scene_desc}")
        
        if touch_data and touch_data.get('x_percent') and touch_data.get('y_percent'):
            ai_insights.append(f"👆 Touch at ({touch_data['x_percent']:.1f}%, {touch_data['y_percent']:.1f}%) - normalized for any screen size")
        
        # Build comprehensive game state from all analysis (actual API format)
        game_state = {
            'scene_type': scene_type,
            'scene_description': scene_desc,
            'ui_elements_count': vision_result.get('summary', {}).get('ui_elements_count', 0) if vision_result else 0,
            'text_detected': vision_result.get('summary', {}).get('text_detected', False) if vision_result else False,
            'overall_confidence': vision_result.get('summary', {}).get('overall_confidence', 0.5) if vision_result else 0.5,
            'screen_width': screen_width,
            'screen_height': screen_height
        }
        
        # Combine all detected text from OCR (actual API format)
        all_detected_text = vision_result.get('ocr', {}).get('text', '') if vision_result else screen_analysis.get('ocr_text', '')
        
        # Create learning_data entry with COMPLETE analysis data
        action_record = await self.db_manager.execute_one(
            """
            INSERT INTO learning_data (
                session_id, game_id, timestamp,
                action_type, action_params, tap_x, tap_y,
                screenshot_before_path, screenshot_after_path,
                detected_text, ui_elements, game_state,
                success, led_to_progress, is_user_action,
                learning_mode, level_identifier,
                metadata
            ) VALUES (
                NULL, $1, NOW(),
                $2, $3, $4, $5,
                $6, $6,
                $7, $8, $9,
                true, true, true,
                'video_demonstration', $10,
                $11
            )
            RETURNING id
            """,
            game_id,
            action_type,
            json.dumps(action_params),
            touch_data.get('x_percent', touch_data['x']),  # Store percentage for screen-agnostic matching
            touch_data.get('y_percent', touch_data['y']),  # Store percentage for screen-agnostic matching
            frame_path,  # screenshot_before_path and screenshot_after_path
            all_detected_text,
            json.dumps(ui_elements),  # ALL detected UI elements from all methods
            json.dumps(game_state),  # Complete game state with vision description
            scene_type,  # level_identifier (menu, gameplay, etc.)
            json.dumps({
                'source': 'video_demonstration',
                'video_id': video_id,
                'scene_type': scene_type,
                'touch_confidence': touch_data.get('confidence', 0.8),
                'analysis_methods': ['ocr', 'blip2', 'cv_detection', 'template_matching'],
                'vision_confidence': vision_result.get('confidence', 0.5) if vision_result else 0.5,
                'ocr_quality': vision_result.get('ocr', {}).get('quality', 0) if vision_result else 0,
                'full_vision_result': vision_result  # Store COMPLETE vision analysis for future reference
            })
        )
        action_id = str(action_record['id'])
        
        logger.info(f"✅ Saved learning_data with {len(ui_elements)} UI elements and complete vision analysis")
        return action_id


async def analyze_video_with_progress(
    db_manager,
    video_id: str,
    video_path: str,
    game_id: str,
    websocket_broadcast: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Convenience wrapper for video analysis with WebSocket progress
    """
    analyzer = VideoAnalyzer(db_manager)
    
    async def progress_handler(progress: Dict[str, Any]):
        if websocket_broadcast:
            await websocket_broadcast({
                'type': 'video_analysis_progress',
                'video_id': video_id,
                **progress
            })
    
    try:
        summary = await analyzer.analyze_video(
            video_id=video_id,
            video_path=video_path,
            game_id=game_id,
            progress_callback=progress_handler
        )
        return summary
        
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        
        # Update video status to failed
        await db_manager.execute_write(
            """
            UPDATE video_demonstrations
            SET processing_status = 'failed',
                processing_error = $1
            WHERE id = $2
            """,
            str(e),
            video_id
        )
        
        raise
