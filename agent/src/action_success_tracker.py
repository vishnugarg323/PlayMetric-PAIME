"""
Action Success Tracking Module
Tracks which actions lead to progress and builds success heatmap
"""
import logging
import numpy as np
from typing import Dict, Tuple, List
from collections import deque
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class ActionSuccessTracker:
    """
    Tracks which screen locations lead to successful actions.
    Builds a heatmap of successful tap locations to prefer in future.
    """
    
    def __init__(self, screen_width: int = 1080, screen_height: int = 1920):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Success heatmap: higher values = more successful actions
        self.success_heatmap = np.zeros((screen_height, screen_width), dtype=np.float32)
        
        # Action history: recent actions with their outcomes
        self.action_history = deque(maxlen=100)
        
        # Statistics
        self.total_actions = 0
        self.successful_actions = 0
        self.failed_actions = 0
        
        logger.info(f"📊 Action Success Tracker initialized ({screen_width}x{screen_height})")
    
    def record_action(self, x: int, y: int, success: bool, reward: float = 0.0):
        """
        Record an action and its outcome
        
        Args:
            x, y: Action coordinates
            success: Whether action led to progress
            reward: Reward value (if available from RL)
        """
        self.total_actions += 1
        
        if success:
            self.successful_actions += 1
        else:
            self.failed_actions += 1
        
        # Store in history
        self.action_history.append({
            'x': x,
            'y': y,
            'success': success,
            'reward': reward,
            'timestamp': self.total_actions
        })
        
        # Update heatmap with gaussian blob around action point
        self._update_heatmap(x, y, success, reward)
        
        logger.debug(f"{'✅' if success else '❌'} Action at ({x}, {y}) | Success rate: {self.get_success_rate():.1%}")
    
    def _update_heatmap(self, x: int, y: int, success: bool, reward: float):
        """
        Update success heatmap with gaussian distribution around action point
        Successful actions increase nearby values, failed actions decrease them
        """
        # Influence radius (pixels) - actions affect nearby locations
        radius = 150
        
        # Create coordinate grids
        y_grid, x_grid = np.ogrid[0:self.screen_height, 0:self.screen_width]
        
        # Calculate distance from action point
        distance = np.sqrt((x_grid - x)**2 + (y_grid - y)**2)
        
        # Gaussian weight: stronger near action point, weaker farther away
        weight = np.exp(-(distance**2) / (2 * (radius/2)**2))
        
        # Update heatmap
        if success:
            # Increase value for successful actions
            update_value = 1.0 + abs(reward)  # Reward boosts the update
            self.success_heatmap += weight * update_value
        else:
            # Decrease value for failed actions (but not too much)
            self.success_heatmap -= weight * 0.3
        
        # Normalize to prevent unbounded growth
        if self.total_actions % 50 == 0:
            max_val = self.success_heatmap.max()
            if max_val > 100:
                self.success_heatmap = self.success_heatmap / max_val * 100
    
    def get_best_tap_location(self, exclude_radius: int = 200) -> Tuple[int, int]:
        """
        Get screen location with highest success probability
        
        Args:
            exclude_radius: Exclude recently tried locations within this radius
            
        Returns:
            (x, y) coordinates of best location
        """
        heatmap = self.success_heatmap.copy()
        
        # Exclude recently failed locations
        for action in list(self.action_history)[-10:]:
            if not action['success']:
                x, y = action['x'], action['y']
                y_grid, x_grid = np.ogrid[0:self.screen_height, 0:self.screen_width]
                distance = np.sqrt((x_grid - x)**2 + (y_grid - y)**2)
                mask = distance < exclude_radius
                heatmap[mask] = -999  # Heavily penalize
        
        # Find maximum
        if heatmap.max() > 0:
            y, x = np.unravel_index(heatmap.argmax(), heatmap.shape)
            logger.info(f"🎯 Best location from heatmap: ({x}, {y}) | Score: {heatmap[y, x]:.2f}")
            return (int(x), int(y))
        else:
            # No good location found, return center
            logger.debug("⚠️ No good location in heatmap, using center")
            return (self.screen_width // 2, self.screen_height // 2)
    
    def get_top_locations(self, count: int = 5) -> List[Tuple[int, int, float]]:
        """
        Get top N successful locations
        
        Returns:
            List of (x, y, score) tuples
        """
        # Find top values
        flat = self.success_heatmap.flatten()
        top_indices = np.argpartition(flat, -count)[-count:]
        top_indices = top_indices[np.argsort(-flat[top_indices])]  # Sort descending
        
        locations = []
        for idx in top_indices:
            y, x = np.unravel_index(idx, self.success_heatmap.shape)
            score = self.success_heatmap[y, x]
            if score > 0:
                locations.append((int(x), int(y), float(score)))
        
        return locations
    
    def get_success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_actions == 0:
            return 0.0
        return self.successful_actions / self.total_actions
    
    def get_recent_success_rate(self, window: int = 20) -> float:
        """Calculate success rate for recent actions"""
        recent = list(self.action_history)[-window:]
        if not recent:
            return 0.0
        successes = sum(1 for a in recent if a['success'])
        return successes / len(recent)
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        return {
            'total_actions': self.total_actions,
            'successful_actions': self.successful_actions,
            'failed_actions': self.failed_actions,
            'success_rate': self.get_success_rate(),
            'recent_success_rate': self.get_recent_success_rate(),
            'heatmap_max': float(self.success_heatmap.max()),
            'heatmap_mean': float(self.success_heatmap.mean()),
            'top_locations': self.get_top_locations(3)
        }
    
    def save(self, filepath: str = "/app/data/action_success_tracker.pkl"):
        """Save tracker state to file"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            data = {
                'heatmap': self.success_heatmap,
                'history': list(self.action_history),
                'stats': {
                    'total': self.total_actions,
                    'successful': self.successful_actions,
                    'failed': self.failed_actions
                }
            }
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"💾 Action tracker saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save action tracker: {e}")
    
    def load(self, filepath: str = "/app/data/action_success_tracker.pkl"):
        """Load tracker state from file"""
        try:
            if not Path(filepath).exists():
                logger.info("No saved action tracker found, starting fresh")
                return
            
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.success_heatmap = data['heatmap']
            self.action_history = deque(data['history'], maxlen=100)
            self.total_actions = data['stats']['total']
            self.successful_actions = data['stats']['successful']
            self.failed_actions = data['stats']['failed']
            
            logger.info(f"📂 Action tracker loaded from {filepath} | {self.total_actions} actions")
        except Exception as e:
            logger.error(f"Failed to load action tracker: {e}")
    
    def reset(self):
        """Reset all tracking data"""
        self.success_heatmap = np.zeros((self.screen_height, self.screen_width), dtype=np.float32)
        self.action_history.clear()
        self.total_actions = 0
        self.successful_actions = 0
        self.failed_actions = 0
        logger.info("🔄 Action tracker reset")
    
    def visualize_heatmap(self, output_path: str = "/app/data/success_heatmap.png"):
        """
        Save heatmap visualization to file
        Useful for debugging and understanding learned patterns
        """
        try:
            import cv2
            
            # Normalize heatmap to 0-255
            if self.success_heatmap.max() > 0:
                normalized = (self.success_heatmap / self.success_heatmap.max() * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(self.success_heatmap, dtype=np.uint8)
            
            # Apply color map
            heatmap_colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
            
            # Save
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(output_path, heatmap_colored)
            logger.info(f"🎨 Heatmap visualization saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to visualize heatmap: {e}")
