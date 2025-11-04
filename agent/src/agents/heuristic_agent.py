"""
Heuristic Agent - Uses rule-based logic to play games
"""
import random
import logging
from typing import Dict, Any, List, Optional
import cv2
import numpy as np
from .base import BaseAgent

logger = logging.getLogger(__name__)


class HeuristicAgent(BaseAgent):
    """Agent that uses heuristics to play games"""
    
    def __init__(self, action_space, config: Dict[str, Any]):
        super().__init__(action_space, config)
        self.last_screenshot = None
        self.stuck_counter = 0
        self.stuck_threshold = 5
        self.action_history = []
        self.ui_elements_history = []
        
    def decide_action(self, observation: Dict[str, Any]):
        """Decide action using heuristics"""
        screenshot = observation.get('screenshot')
        ui_elements = observation.get('ui_elements', [])
        
        # Check if stuck (same screen)
        if self._is_stuck(screenshot):
            self.stuck_counter += 1
            logger.warning(f"Potentially stuck (count: {self.stuck_counter})")
            
            if self.stuck_counter >= self.stuck_threshold:
                logger.info("Agent stuck, performing recovery action")
                return self._recovery_action()
        else:
            self.stuck_counter = 0
        
        # Update history
        self.last_screenshot = screenshot
        self.ui_elements_history.append(ui_elements)
        
        # Decide action based on heuristics
        action = self._heuristic_decision(ui_elements, observation)
        
        self.action_count += 1
        self.action_history.append(action.action_type.value)
        
        return action
    
    def _heuristic_decision(self, ui_elements: List[Dict], observation: Dict) -> Any:
        """Make decision based on game state"""
        # Priority 1: Tap on large UI elements (likely buttons)
        large_elements = [e for e in ui_elements if e.get('area', 0) > 10000]
        if large_elements:
            # Choose element in middle or lower part of screen (common for action buttons)
            suitable = [e for e in large_elements if e['center_y'] > 600]
            if suitable:
                element = random.choice(suitable)
                logger.debug(f"Tapping UI element at ({element['center_x']}, {element['center_y']})")
                return self.action_space.get_tap_at(element['center_x'], element['center_y'])
        
        # Priority 2: Tap on medium-sized elements
        medium_elements = [e for e in ui_elements if 2000 < e.get('area', 0) < 10000]
        if medium_elements:
            element = random.choice(medium_elements)
            logger.debug(f"Tapping medium UI element")
            return self.action_space.get_tap_at(element['center_x'], element['center_y'])
        
        # Priority 3: Explore with swipes (70% chance) or taps (30% chance)
        if random.random() < 0.7:
            # Swipe in a random direction
            swipe_actions = [
                self.action_space.get_swipe_up,
                self.action_space.get_swipe_down,
                self.action_space.get_swipe_left,
                self.action_space.get_swipe_right,
            ]
            action_func = random.choice(swipe_actions)
            logger.debug(f"Exploring with swipe")
            return action_func()
        else:
            # Random tap
            logger.debug(f"Exploring with tap")
            return self.action_space.get_random_tap()
    
    def _is_stuck(self, current_screenshot: Optional[str]) -> bool:
        """Check if agent is stuck on same screen"""
        if not self.last_screenshot or not current_screenshot:
            return False
        
        try:
            # Load images
            img1 = cv2.imread(self.last_screenshot, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(current_screenshot, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return False
            
            # Resize if needed
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # Calculate similarity
            diff = cv2.absdiff(img1, img2)
            diff_score = np.sum(diff) / diff.size
            
            # If very similar, likely stuck
            return diff_score < 5.0
            
        except Exception as e:
            logger.error(f"Error checking if stuck: {e}")
            return False
    
    def _recovery_action(self):
        """Perform action to recover from stuck state"""
        self.stuck_counter = 0
        
        # Try different recovery strategies
        strategy = random.choice(['back', 'swipe', 'tap'])
        
        if strategy == 'back':
            logger.info("Recovery: pressing back button")
            return self.action_space.get_back_action()
        elif strategy == 'swipe':
            logger.info("Recovery: performing long swipe")
            return self.action_space.get_swipe_up(distance="long")
        else:
            logger.info("Recovery: tapping center")
            return self.action_space.get_tap_at(
                self.action_space.screen_width // 2,
                self.action_space.screen_height // 2
            )
    
    def reset(self):
        """Reset agent state"""
        self.action_count = 0
        self.episode_reward = 0.0
        self.last_screenshot = None
        self.stuck_counter = 0
        self.action_history.clear()
        self.ui_elements_history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        stats = super().get_statistics()
        
        # Add action distribution
        action_counts = {}
        for action in self.action_history:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        stats["action_distribution"] = action_counts
        stats["stuck_events"] = self.stuck_counter
        return stats
