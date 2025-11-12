"""
Template Matching Module
Fast button detection using pre-saved templates (<10ms)
"""
import logging
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, List

logger = logging.getLogger(__name__)


class TemplateMatcher:
    """
    Fast template matching for common UI patterns
    Uses pre-saved button templates for instant recognition
    """
    
    def __init__(self, template_dir: str = "/app/data/templates"):
        self.template_dir = Path(template_dir)
        self.templates = {}
        self.template_sizes = {}
        self._load_templates()
        
        if self.templates:
            logger.info(f"📋 Template Matcher initialized with {len(self.templates)} templates")
        else:
            logger.info("📋 Template Matcher initialized (no templates loaded yet)")
    
    def _load_templates(self):
        """Load button templates from directory"""
        if not self.template_dir.exists():
            logger.debug(f"Template directory not found: {self.template_dir}")
            return
        
        # Load all PNG templates
        for template_file in self.template_dir.glob("*.png"):
            try:
                name = template_file.stem
                template = cv2.imread(str(template_file), cv2.IMREAD_GRAYSCALE)
                
                if template is not None:
                    self.templates[name] = template
                    self.template_sizes[name] = template.shape
                    logger.debug(f"  ✓ Loaded template: {name} ({template.shape[1]}x{template.shape[0]})")
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
    
    def find_button(
        self,
        screenshot_path: str,
        button_type: str,
        confidence_threshold: float = 0.8
    ) -> Optional[Tuple[int, int]]:
        """
        Find button using template matching (very fast: <10ms)
        
        Args:
            screenshot_path: Path to screenshot
            button_type: Template name (e.g., 'play', 'start', 'next', 'close')
            confidence_threshold: Minimum match confidence (0-1)
            
        Returns:
            (x, y) center coordinates if found, None otherwise
        """
        if button_type not in self.templates:
            return None
        
        try:
            # Load screenshot in grayscale
            img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None
            
            template = self.templates[button_type]
            
            # Template matching
            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence_threshold:
                # Get template size
                h, w = template.shape
                # Calculate center of match
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                
                logger.info(f"🎯 Template '{button_type}' found at ({center_x}, {center_y}) | Confidence: {max_val:.3f}")
                return (center_x, center_y)
            else:
                logger.debug(f"Template '{button_type}' not found (max confidence: {max_val:.3f})")
                return None
                
        except Exception as e:
            logger.error(f"Template matching failed for '{button_type}': {e}")
            return None
    
    def find_all_matches(
        self,
        screenshot_path: str,
        confidence_threshold: float = 0.8
    ) -> Dict[str, Tuple[int, int]]:
        """
        Find all known templates in screenshot
        
        Returns:
            Dict mapping template_name -> (x, y) coordinates
        """
        matches = {}
        
        for button_type in self.templates.keys():
            location = self.find_button(screenshot_path, button_type, confidence_threshold)
            if location:
                matches[button_type] = location
        
        if matches:
            logger.info(f"📋 Found {len(matches)} template matches: {list(matches.keys())}")
        
        return matches
    
    def find_multi_scale(
        self,
        screenshot_path: str,
        button_type: str,
        scales: List[float] = [0.8, 0.9, 1.0, 1.1, 1.2],
        confidence_threshold: float = 0.75
    ) -> Optional[Tuple[int, int, float]]:
        """
        Find button at multiple scales (handles size variations)
        Slower than regular matching but more robust
        
        Returns:
            (x, y, scale) if found, None otherwise
        """
        if button_type not in self.templates:
            return None
        
        try:
            img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None
            
            template = self.templates[button_type]
            best_match = None
            best_confidence = 0.0
            
            for scale in scales:
                # Resize template
                if scale != 1.0:
                    width = int(template.shape[1] * scale)
                    height = int(template.shape[0] * scale)
                    scaled_template = cv2.resize(template, (width, height))
                else:
                    scaled_template = template
                
                # Match
                result = cv2.matchTemplate(img, scaled_template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    h, w = scaled_template.shape
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    best_match = (center_x, center_y, scale)
            
            if best_confidence >= confidence_threshold and best_match:
                x, y, s = best_match
                logger.info(f"🎯 Multi-scale '{button_type}' found at ({x}, {y}) | Scale: {s:.2f} | Confidence: {best_confidence:.3f}")
                return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"Multi-scale matching failed for '{button_type}': {e}")
            return None
    
    def add_template(self, name: str, screenshot_path: str, x: int, y: int, width: int, height: int):
        """
        Extract and save a new template from a screenshot
        Useful for building template library from successful sessions
        
        Args:
            name: Template name (e.g., 'play_button')
            screenshot_path: Source screenshot
            x, y: Top-left corner of button
            width, height: Button dimensions
        """
        try:
            img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                logger.error(f"Could not load screenshot: {screenshot_path}")
                return False
            
            # Extract region
            template = img[y:y+height, x:x+width]
            
            if template.size == 0:
                logger.error(f"Invalid template region: ({x},{y}) {width}x{height}")
                return False
            
            # Save template
            self.template_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.template_dir / f"{name}.png"
            cv2.imwrite(str(output_path), template)
            
            # Add to loaded templates
            self.templates[name] = template
            self.template_sizes[name] = template.shape
            
            logger.info(f"✅ Template '{name}' saved to {output_path} ({width}x{height})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add template '{name}': {e}")
            return False
    
    def get_template_info(self) -> Dict:
        """Get information about loaded templates"""
        return {
            'total_templates': len(self.templates),
            'template_names': list(self.templates.keys()),
            'template_sizes': {name: f"{size[1]}x{size[0]}" for name, size in self.template_sizes.items()},
            'template_dir': str(self.template_dir)
        }


# Pre-defined common button types for mobile games
COMMON_BUTTON_TYPES = [
    'play', 'start', 'begin', 'go',  # Start game
    'next', 'continue', 'proceed',    # Progress
    'close', 'x', 'back',             # Navigation
    'ok', 'yes', 'confirm',           # Confirmation
    'level', 'stage', 'chapter',      # Level selection
    'menu', 'home', 'settings',       # Menu
    'retry', 'restart', 'replay'      # Replay
]
