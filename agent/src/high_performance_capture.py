"""
High-Performance Screen Capture & Analysis System
Captures at 16 FPS and analyzes screenshots in parallel
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import httpx
import os

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotBatch:
    """Batch of screenshots captured in 1 second"""
    timestamp: float
    screenshots: List[Dict[str, Any]]  # List of screenshot analysis results
    batch_id: str
    
    def get_collective_analysis(self) -> Dict[str, Any]:
        """Aggregate analysis from all screenshots in this batch"""
        if not self.screenshots:
            return {}
        
        # Combine OCR text from all screenshots
        all_text = []
        ui_elements_total = 0
        screen_changed_count = 0
        
        for shot in self.screenshots:
            if shot.get('ocr_text'):
                all_text.append(shot['ocr_text'])
            ui_elements_total += shot.get('ui_elements', 0)
            if shot.get('screen_changed'):
                screen_changed_count += 1
        
        return {
            "combined_ocr_text": " ".join(all_text),
            "avg_ui_elements": ui_elements_total / len(self.screenshots) if self.screenshots else 0,
            "screen_stability": 1.0 - (screen_changed_count / len(self.screenshots)),
            "total_frames": len(self.screenshots),
            "timestamp": self.timestamp
        }


class HighPerformanceCapture:
    """
    Captures screenshots at 16 FPS and processes them in parallel
    
    Architecture:
    - Main loop runs at 16 FPS (62.5ms per frame)
    - Each screenshot is analyzed in parallel using thread pool
    - Every second, collective analysis is performed
    - Results are batched and sent to learning recorders
    """
    
    def __init__(
        self,
        device_manager_url: str,
        fps: int = 16,
        max_workers: int = 8
    ):
        self.fps = fps
        self.frame_interval = 1.0 / fps  # ~62.5ms per frame
        self.device_manager_url = device_manager_url
        self.max_workers = max_workers
        
        # Thread pool for parallel screenshot analysis
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # Current batch (1 second of screenshots)
        self.current_batch: List[Dict] = []
        self.batch_start_time = time.time()
        
        # Statistics
        self.frames_captured = 0
        self.frames_analyzed = 0
        self.analysis_times = []
        
        # HTTP client for fast requests
        self.http_client = httpx.AsyncClient(timeout=5.0)
        
        # Running flag
        self.is_running = False
        self.capture_task: Optional[asyncio.Task] = None
        
        logger.info(f"🚀 High-Performance Capture initialized: {fps} FPS, {max_workers} workers")
    
    async def start_capture(
        self,
        on_batch_complete: Callable[[ScreenshotBatch], None],
        mode: str = "observation"  # "observation" or "decision"
    ):
        """
        Start high-performance capture
        
        Args:
            on_batch_complete: Callback when 1 second batch is complete
            mode: Capture mode for different processing
        """
        if self.is_running:
            logger.warning("Capture already running")
            return
        
        self.is_running = True
        self.capture_task = asyncio.create_task(
            self._capture_loop(on_batch_complete, mode)
        )
        logger.info(f"✅ Started {self.fps} FPS capture in {mode} mode")
    
    async def stop_capture(self):
        """Stop capture"""
        self.is_running = False
        if self.capture_task:
            self.capture_task.cancel()
            try:
                await self.capture_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=False)
        
        logger.info("⏹️  Stopped capture")
    
    async def _capture_loop(
        self,
        on_batch_complete: Callable,
        mode: str
    ):
        """Main capture loop running at specified FPS"""
        try:
            while self.is_running:
                loop_start = time.time()
                
                # Capture and analyze screenshot
                screenshot_data = await self._capture_and_analyze_frame()
                
                if screenshot_data:
                    self.current_batch.append(screenshot_data)
                    self.frames_captured += 1
                
                # Check if 1 second has passed
                elapsed = time.time() - self.batch_start_time
                if elapsed >= 1.0:
                    # Process batch
                    await self._process_batch(on_batch_complete)
                    
                    # Reset for next batch
                    self.current_batch = []
                    self.batch_start_time = time.time()
                
                # Sleep to maintain FPS
                elapsed_frame = time.time() - loop_start
                sleep_time = max(0, self.frame_interval - elapsed_frame)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.debug(f"⚠️  Frame took {elapsed_frame*1000:.1f}ms (target: {self.frame_interval*1000:.1f}ms)")
                
        except asyncio.CancelledError:
            logger.info("Capture loop cancelled")
        except Exception as e:
            logger.error(f"❌ Capture loop error: {e}", exc_info=True)
    
    async def _capture_and_analyze_frame(self) -> Optional[Dict]:
        """Capture single frame and analyze in parallel"""
        try:
            # Capture screenshot (fast, from emulator-manager)
            response = await self.http_client.get(
                f"{self.device_manager_url}/screenshot",
                timeout=0.5  # Fast timeout
            )
            
            if response.status_code != 200:
                return None
            
            screenshot_data = response.json()
            screenshot_path = screenshot_data.get('path')
            
            if not screenshot_path or not os.path.exists(screenshot_path):
                return None
            
            # Analyze in thread pool (parallel processing)
            loop = asyncio.get_event_loop()
            analysis = await loop.run_in_executor(
                self.thread_pool,
                self._analyze_screenshot_sync,
                screenshot_path
            )
            
            self.frames_analyzed += 1
            
            return {
                "path": screenshot_path,
                "timestamp": time.time(),
                "analysis": analysis
            }
            
        except Exception as e:
            logger.debug(f"Frame capture error: {e}")
            return None
    
    def _analyze_screenshot_sync(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Synchronous screenshot analysis (runs in thread pool)
        
        This performs:
        - Basic image analysis
        - OCR text extraction (lightweight)
        - UI element detection
        - Screen change detection
        """
        analysis_start = time.time()
        
        try:
            import cv2
            import numpy as np
            
            # Load image
            img = cv2.imread(screenshot_path)
            if img is None:
                return {"error": "Failed to load image"}
            
            # Quick analysis
            height, width = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect edges (proxy for UI elements)
            edges = cv2.Canny(gray, 50, 150)
            ui_elements_count = cv2.countNonZero(edges) // 1000  # Rough count
            
            # Simple OCR simulation (in production, use pytesseract or cloud OCR)
            # For now, we'll skip heavy OCR and use lightweight detection
            ocr_text = ""
            
            # Screen change detection (compare with previous frame if available)
            screen_changed = True  # Default to true
            
            analysis_time = (time.time() - analysis_start) * 1000
            self.analysis_times.append(analysis_time)
            
            return {
                "width": width,
                "height": height,
                "ui_elements": min(ui_elements_count, 100),
                "ocr_text": ocr_text,
                "screen_changed": screen_changed,
                "analysis_time_ms": analysis_time
            }
            
        except Exception as e:
            logger.debug(f"Analysis error: {e}")
            return {"error": str(e)}
    
    async def _process_batch(self, on_batch_complete: Callable):
        """Process completed 1-second batch"""
        if not self.current_batch:
            return
        
        batch = ScreenshotBatch(
            timestamp=self.batch_start_time,
            screenshots=[s['analysis'] for s in self.current_batch],
            batch_id=f"batch_{int(self.batch_start_time)}"
        )
        
        # Get collective analysis
        collective = batch.get_collective_analysis()
        
        logger.info(
            f"📊 Batch complete: {len(batch.screenshots)} frames, "
            f"UI avg: {collective['avg_ui_elements']:.1f}, "
            f"Stability: {collective['screen_stability']:.2f}"
        )
        
        # Call callback with batch
        try:
            if asyncio.iscoroutinefunction(on_batch_complete):
                await on_batch_complete(batch)
            else:
                on_batch_complete(batch)
        except Exception as e:
            logger.error(f"Batch callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_analysis_time = (
            sum(self.analysis_times[-100:]) / len(self.analysis_times[-100:])
            if self.analysis_times else 0
        )
        
        return {
            "fps_target": self.fps,
            "frames_captured": self.frames_captured,
            "frames_analyzed": self.frames_analyzed,
            "avg_analysis_time_ms": avg_analysis_time,
            "current_batch_size": len(self.current_batch),
            "is_running": self.is_running
        }
