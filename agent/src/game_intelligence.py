"""
Intelligent Game Analysis Module
Provides OCR, screenshot comparison, UI detection, and smart decision making
"""
import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple
import imagehash
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import logging

logger = logging.getLogger(__name__)

# Try to import pytesseract, but make it optional
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available - OCR features will be disabled")


class GameIntelligence:
    """Smart game analysis and decision making"""
    
    def __init__(self):
        self.last_screenshot = None
        self.last_screenshot_hash = None
        self.last_ocr_text = ""
        self.action_history = []  # Last 10 actions with results
        self.stuck_counter = 0
        self.last_detected_buttons = []
        
    def extract_text_from_screenshot(self, screenshot_path: str) -> Dict[str, any]:
        """
        Extract text from screenshot using OCR
        Returns: {
            'text': full text,
            'words': list of word positions,
            'buttons_detected': list of button-like text areas
        }
        """
        if not TESSERACT_AVAILABLE:
            return {'text': '', 'words': [], 'buttons_detected': []}
        
        try:
            img = cv2.imread(screenshot_path)
            if img is None:
                return {'text': '', 'words': [], 'buttons_detected': []}
            
            # Convert to grayscale for better OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding to preprocess
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Extract text with position data
            ocr_data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
            
            # Compile full text
            full_text = pytesseract.image_to_string(thresh).strip()
            
            # Extract words with positions
            words = []
            buttons_detected = []
            
            for i in range(len(ocr_data['text'])):
                if int(ocr_data['conf'][i]) > 30:  # Confidence threshold
                    word = ocr_data['text'][i].strip()
                    if word:
                        x, y, w, h = (
                            ocr_data['left'][i],
                            ocr_data['top'][i],
                            ocr_data['width'][i],
                            ocr_data['height'][i]
                        )
                        
                        words.append({
                            'text': word,
                            'x': x, 'y': y, 'w': w, 'h': h,
                            'center': (x + w // 2, y + h // 2),
                            'confidence': ocr_data['conf'][i]
                        })
                        
                        # Detect button-like words
                        button_keywords = [
                            'play', 'start', 'continue', 'next', 'ok', 'yes', 
                            'tap', 'click', 'go', 'begin', 'level', 'menu',
                            'retry', 'restart', 'skip', 'close', 'accept'
                        ]
                        if word.lower() in button_keywords:
                            buttons_detected.append({
                                'text': word,
                                'center': (x + w // 2, y + h // 2),
                                'bounds': (x, y, w, h)
                            })
            
            self.last_ocr_text = full_text
            self.last_detected_buttons = buttons_detected
            
            return {
                'text': full_text,
                'words': words,
                'buttons_detected': buttons_detected
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {'text': '', 'words': [], 'buttons_detected': []}
    
    def compare_screenshots(self, current_screenshot_path: str) -> Dict[str, any]:
        """
        Compare current screenshot with previous one
        Returns: {
            'changed': bool,
            'similarity_score': float (0-1),
            'changed_significantly': bool
        }
        """
        try:
            current_img = cv2.imread(current_screenshot_path)
            if current_img is None:
                return {'changed': False, 'similarity_score': 0.0, 'changed_significantly': False}
            
            # Convert to grayscale
            current_gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
            
            # If no previous screenshot, store this one
            if self.last_screenshot is None:
                self.last_screenshot = current_gray
                
                # Calculate perceptual hash
                pil_img = Image.fromarray(current_gray)
                self.last_screenshot_hash = imagehash.phash(pil_img)
                
                return {'changed': True, 'similarity_score': 0.0, 'changed_significantly': True}
            
            # Resize if needed to match dimensions
            if current_gray.shape != self.last_screenshot.shape:
                current_gray = cv2.resize(current_gray, 
                    (self.last_screenshot.shape[1], self.last_screenshot.shape[0]))
            
            # Calculate structural similarity
            similarity = ssim(self.last_screenshot, current_gray)
            
            # Calculate perceptual hash difference
            pil_img = Image.fromarray(current_gray)
            current_hash = imagehash.phash(pil_img)
            hash_diff = current_hash - self.last_screenshot_hash
            
            # Determine if changed significantly
            # SSIM < 0.95 means noticeable change
            # Hash diff > 5 means perceptual change
            changed_significantly = similarity < 0.95 or hash_diff > 5
            
            # Update stored screenshot
            self.last_screenshot = current_gray
            self.last_screenshot_hash = current_hash
            
            return {
                'changed': similarity < 0.99,  # Any change
                'similarity_score': float(similarity),
                'changed_significantly': changed_significantly,
                'hash_difference': int(hash_diff)
            }
            
        except Exception as e:
            logger.error(f"Screenshot comparison failed: {e}")
            return {'changed': False, 'similarity_score': 1.0, 'changed_significantly': False}
    
    def detect_ui_elements(self, screenshot_path: str) -> List[Dict]:
        """
        Detect interactive UI elements using computer vision
        Returns list of detected elements with positions
        """
        try:
            img = cv2.imread(screenshot_path)
            if img is None:
                return []
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours (potential buttons/UI elements)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            ui_elements = []
            height, width = img.shape[:2]
            
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size (buttons are usually 40-300px in both dimensions)
                if 40 < w < 300 and 40 < h < 300:
                    # Calculate aspect ratio
                    aspect_ratio = float(w) / h
                    
                    # Buttons are usually close to square or wide rectangles
                    if 0.3 < aspect_ratio < 4.0:
                        # Calculate area percentage
                        area = w * h
                        screen_area = width * height
                        area_percentage = (area / screen_area) * 100
                        
                        # Skip if too large (probably not a button)
                        if area_percentage < 25:
                            center = (x + w // 2, y + h // 2)
                            ui_elements.append({
                                'type': 'button_candidate',
                                'center': center,
                                'bounds': (x, y, w, h),
                                'area': area,
                                'aspect_ratio': aspect_ratio
                            })
            
            # Sort by vertical position (top to bottom) and size
            ui_elements.sort(key=lambda el: (el['center'][1], -el['area']))
            
            return ui_elements[:20]  # Return top 20 candidates
            
        except Exception as e:
            logger.error(f"UI detection failed: {e}")
            return []
    
    def record_action_result(self, action: str, coordinates: Tuple[int, int], 
                           screen_changed: bool, reward: float):
        """Record action and its result for pattern learning"""
        self.action_history.append({
            'action': action,
            'coords': coordinates,
            'screen_changed': screen_changed,
            'reward': reward
        })
        
        # Keep only last 10 actions
        if len(self.action_history) > 10:
            self.action_history.pop(0)
        
        # Update stuck counter
        if not screen_changed:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
    
    def is_stuck(self) -> bool:
        """Detect if AI is stuck (no screen changes for 3+ actions)"""
        return self.stuck_counter >= 3
    
    def get_smart_action_recommendation(self, ocr_data: Dict, ui_elements: List[Dict],
                                       screenshot_changed: bool) -> Optional[Dict]:
        """
        Recommend smart action based on analysis
        Returns: {
            'action': 'tap' | 'swipe_up' | 'back',
            'coordinates': (x, y),
            'reasoning': str
        }
        """
        # Priority 1: Correlate OCR text with visual UI elements for accurate button detection
        if ocr_data.get('buttons_detected') and ui_elements:
            # Find UI element near button text (within 200px)
            button = ocr_data['buttons_detected'][0]
            button_pos = button['center']
            
            for ui_el in ui_elements:
                el_pos = ui_el['center']
                # Calculate distance between OCR text and UI element
                distance = ((button_pos[0] - el_pos[0])**2 + (button_pos[1] - el_pos[1])**2)**0.5
                
                if distance < 200:  # Within 200px - likely the same button
                    logger.info(f"✨ CORRELATED: Button text '{button['text']}' at {button_pos} → UI element at {el_pos} (distance: {distance:.0f}px)")
                    return {
                        'action': 'tap',
                        'coordinates': el_pos,  # Use UI element position, not text position!
                        'reasoning': f"🎯 SMART TAP: Clicking button '{button['text']}' - correlated OCR text with visual UI element at {el_pos}"
                    }
        
        # Priority 2: Click visual UI elements (actual buttons) even without text match
        if ui_elements:
            # Prefer elements in center or bottom (where game buttons usually are)
            center_elements = [el for el in ui_elements if 400 < el['center'][1] < 1600]
            if center_elements:
                target = center_elements[0]
                return {
                    'action': 'tap',
                    'coordinates': target['center'],
                    'reasoning': f"🎯 UI ELEMENT TAP: Clicking detected visual UI element at {target['center']} (size: {target['area']}px)"
                }
            # Fallback to any UI element
            target = ui_elements[0]
            return {
                'action': 'tap',
                'coordinates': target['center'],
                'reasoning': f"🎯 UI ELEMENT TAP: Clicking detected visual element at {target['center']}"
            }
        
        # Priority 3: If only OCR buttons (no UI elements), use OCR position as fallback
        if ocr_data.get('buttons_detected'):
            button = ocr_data['buttons_detected'][0]
            return {
                'action': 'tap',
                'coordinates': button['center'],
                'reasoning': f"📝 OCR FALLBACK: Clicking text '{button['text']}' at {button['center']} (no visual UI element found)"
            }
        
        # Priority 3: If text detected but no clear buttons, click center of text areas
        if ocr_data.get('words'):
            # Look for clickable-looking words - when stuck, try ANY text
            clickable_words = [w for w in ocr_data['words'] 
                             if len(w['text']) > 2 and w['confidence'] > 60]
            if clickable_words:
                # When stuck, prefer words in upper half of screen (where dialogs/buttons are)
                if self.is_stuck():
                    upper_words = [w for w in clickable_words if w['center'][1] < 960]
                    if upper_words:
                        word = upper_words[0]
                        logger.info(f"🚨 STUCK RECOVERY: Tapping on text '{word['text']}'")
                        return {
                            'action': 'tap',
                            'coordinates': word['center'],
                            'reasoning': f"🚨 STUCK TAP: Clicking on text '{word['text']}' at {word['center']} to escape stuck state"
                        }
                
                # Normal case - tap first clickable word
                word = clickable_words[0]
                return {
                    'action': 'tap',
                    'coordinates': word['center'],
                    'reasoning': f"📝 TEXT TAP: Clicking on text '{word['text']}' at {word['center']}"
                }
        
        # Priority 4: If stuck and nothing to click, try BACK as last resort
        if self.is_stuck():
            logger.info("🚨 AI is stuck! Trying BACK button as last resort")
            return {
                'action': 'back',
                'coordinates': None,
                'reasoning': f"STUCK RECOVERY: No screen changes for {self.stuck_counter} actions. Pressing BACK to escape."
            }
        
        # No smart recommendations - return None to let RL agent decide
        return None
    
    def calculate_smart_reward(self, observation: dict, screen_changed: bool,
                              ocr_data: Dict) -> float:
        """Calculate reward based on game understanding"""
        reward = 0.0
        
        # Base reward for taking action
        reward += 0.01
        
        # Big reward for screen changes (progress)
        if screen_changed:
            reward += 1.0
            logger.info("✅ Screen changed - POSITIVE action!")
        else:
            # Penalty for no change
            reward -= 0.1
        
        # Penalty for being stuck
        if self.is_stuck():
            reward -= 0.5
        
        # Reward for detecting interactive elements
        if ocr_data.get('buttons_detected'):
            reward += 0.2  # Found actionable UI
        
        # Penalty for crashes
        if observation.get('crashed', False):
            reward -= 10.0
        
        # Reward for score/level changes
        score_change = observation.get('score_change', 0)
        if score_change > 0:
            reward += min(score_change * 0.1, 2.0)
        
        return reward
