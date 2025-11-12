"""
Color-based object detection for game elements
Fast detection of game objects by color (red screws, blue pieces, etc.)
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ColorBasedObjectDetector:
    """
    Detects game objects by color using HSV color space
    Optimized for mobile puzzle games with distinct colored pieces
    """
    
    def __init__(self):
        # Define HSV color ranges for common game object colors
        # Format: (lower_hsv, upper_hsv)
        self.color_ranges = {
            'red': [
                (np.array([0, 100, 100]), np.array([10, 255, 255])),  # Lower red
                (np.array([170, 100, 100]), np.array([180, 255, 255]))  # Upper red
            ],
            'blue': [(np.array([100, 100, 100]), np.array([130, 255, 255]))],
            'green': [(np.array([40, 100, 100]), np.array([80, 255, 255]))],
            'yellow': [(np.array([20, 100, 100]), np.array([40, 255, 255]))],
            'orange': [(np.array([10, 100, 100]), np.array([20, 255, 255]))],
            'purple': [(np.array([130, 100, 100]), np.array([160, 255, 255]))],
        }
        
        # Minimum contour area to filter noise (in pixels)
        self.min_area = 500
        self.max_area = 50000
        
    def detect_objects(self, screenshot_path: str) -> List[Dict]:
        """
        Detect colored game objects in screenshot
        
        Args:
            screenshot_path: Path to screenshot image
            
        Returns:
            List of detected objects with color, position, size
        """
        try:
            # Read image
            img = cv2.imread(screenshot_path)
            if img is None:
                logger.warning(f"Could not read screenshot: {screenshot_path}")
                return []
            
            # Convert to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            height, width = img.shape[:2]
            
            detected_objects = []
            
            # Detect each color
            for color_name, ranges in self.color_ranges.items():
                # Create mask for this color
                mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
                for lower, upper in ranges:
                    color_mask = cv2.inRange(hsv, lower, upper)
                    mask = cv2.bitwise_or(mask, color_mask)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Process each contour
                for contour in contours:
                    area = cv2.contourArea(contour)
                    
                    # Filter by size
                    if self.min_area < area < self.max_area:
                        # Get bounding rectangle
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        # Calculate center
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        # Calculate normalized position (0-1)
                        norm_x = center_x / width
                        norm_y = center_y / height
                        
                        detected_objects.append({
                            'type': 'colored_object',
                            'color': color_name,
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'center_x': center_x,
                            'center_y': center_y,
                            'norm_x': norm_x,
                            'norm_y': norm_y,
                            'area': int(area),
                            'confidence': 0.8,  # Color detection is pretty reliable
                            'clickable': True  # Colored objects in games are usually interactive
                        })
            
            if detected_objects:
                logger.debug(f"🎨 Color detection found {len(detected_objects)} objects: {[obj['color'] for obj in detected_objects]}")
            
            return detected_objects
            
        except Exception as e:
            logger.error(f"Color detection error: {e}", exc_info=True)
            return []
    
    def get_object_by_color(self, objects: List[Dict], color: str) -> List[Dict]:
        """Get all objects of a specific color"""
        return [obj for obj in objects if obj.get('color') == color]
    
    def get_largest_object(self, objects: List[Dict]) -> Dict:
        """Get the largest detected object by area"""
        if not objects:
            return None
        return max(objects, key=lambda x: x.get('area', 0))
    
    def get_closest_to_center(self, objects: List[Dict]) -> Dict:
        """Get object closest to screen center"""
        if not objects:
            return None
        return min(objects, key=lambda x: abs(x['norm_x'] - 0.5) + abs(x['norm_y'] - 0.5))
