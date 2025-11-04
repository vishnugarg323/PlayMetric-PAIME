"""
Screen Capture - Handles screenshot capturing and processing
"""
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Manages screen capture and image processing"""
    
    def __init__(self, output_dir: str = "/data/screenshots", format: str = "png", quality: int = 85):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.format = format
        self.quality = quality
        self.last_screenshot = None
        self.screenshot_count = 0
        
    def save_screenshot(self, image_path: str, session_id: str = "default") -> Optional[str]:
        """Save screenshot with timestamp"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"Screenshot file not found: {image_path}")
                return None
            
            # Create session directory
            session_dir = self.output_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_filename = f"screen_{timestamp}.{self.format}"
            output_path = session_dir / output_filename
            
            # Open and save with compression
            with Image.open(image_path) as img:
                if self.format.lower() == 'jpg' or self.format.lower() == 'jpeg':
                    img.save(output_path, format='JPEG', quality=self.quality, optimize=True)
                elif self.format.lower() == 'png':
                    img.save(output_path, format='PNG', compress_level=6)
                else:
                    img.save(output_path)
            
            self.last_screenshot = str(output_path)
            self.screenshot_count += 1
            
            logger.debug(f"Screenshot saved: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return None
    
    def get_latest_screenshot(self) -> Optional[str]:
        """Get path to latest screenshot"""
        return self.last_screenshot
    
    def load_image(self, path: str) -> Optional[np.ndarray]:
        """Load image as numpy array"""
        try:
            img = cv2.imread(path)
            if img is not None:
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return None
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return None
    
    def compare_screenshots(self, img1_path: str, img2_path: str, threshold: float = 0.95) -> bool:
        """Compare two screenshots for similarity"""
        try:
            img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return False
            
            # Resize to same dimensions if needed
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # Calculate structural similarity
            from skimage.metrics import structural_similarity as ssim
            similarity = ssim(img1, img2)
            
            return similarity >= threshold
            
        except Exception as e:
            logger.error(f"Error comparing screenshots: {e}")
            return False
    
    def detect_ui_elements(self, image_path: str) -> list:
        """Detect potential UI elements (buttons, text areas)"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter and extract bounding boxes
            ui_elements = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if 1000 < area < 100000:  # Filter by size
                    x, y, w, h = cv2.boundingRect(contour)
                    ui_elements.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h),
                        'center_x': int(x + w/2),
                        'center_y': int(y + h/2),
                        'area': int(area)
                    })
            
            return ui_elements
            
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
            return []
    
    def extract_text_regions(self, image_path: str) -> list:
        """Extract regions that likely contain text"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Use MSER for text detection
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            text_regions = []
            for region in regions:
                x, y, w, h = cv2.boundingRect(region)
                if w > 20 and h > 10:  # Minimum text size
                    text_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h)
                    })
            
            return text_regions
            
        except Exception as e:
            logger.error(f"Error extracting text regions: {e}")
            return []
    
    def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """Delete screenshots older than specified hours"""
        try:
            current_time = time.time()
            deleted_count = 0
            
            for screenshot in self.output_dir.rglob(f"*.{self.format}"):
                file_age = current_time - screenshot.stat().st_mtime
                if file_age > (max_age_hours * 3600):
                    screenshot.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old screenshots")
                
        except Exception as e:
            logger.error(f"Error cleaning up screenshots: {e}")
