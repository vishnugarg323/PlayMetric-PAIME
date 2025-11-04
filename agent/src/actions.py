"""
Action Space - Defines all possible actions the agent can take
"""
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Optional
import random


class ActionType(str, Enum):
    """Types of actions"""
    TAP = "tap"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    BACK = "back"
    HOME = "home"
    MENU = "menu"
    WAIT = "wait"
    LONG_PRESS = "long_press"


@dataclass
class Action:
    """Represents an action to perform"""
    action_type: ActionType
    x: Optional[int] = None
    y: Optional[int] = None
    x2: Optional[int] = None
    y2: Optional[int] = None
    duration: int = 300
    
    def to_dict(self):
        return {
            "action_type": self.action_type.value,
            "x": self.x,
            "y": self.y,
            "x2": self.x2,
            "y2": self.y2,
            "duration": self.duration
        }


class ActionSpace:
    """Manages action space for the agent"""
    
    def __init__(self, screen_width: int = 1080, screen_height: int = 1920):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Define action zones (to avoid edges)
        self.safe_margin = 50
        self.action_width = screen_width - (2 * self.safe_margin)
        self.action_height = screen_height - (2 * self.safe_margin)
        
        # Swipe distances
        self.swipe_distance_short = 200
        self.swipe_distance_medium = 400
        self.swipe_distance_long = 600
        
    def get_random_tap(self) -> Action:
        """Generate random tap action"""
        x = random.randint(self.safe_margin, self.screen_width - self.safe_margin)
        y = random.randint(self.safe_margin, self.screen_height - self.safe_margin)
        
        return Action(
            action_type=ActionType.TAP,
            x=x,
            y=y
        )
    
    def get_tap_at(self, x: int, y: int) -> Action:
        """Generate tap action at specific coordinates"""
        return Action(
            action_type=ActionType.TAP,
            x=x,
            y=y
        )
    
    def get_swipe_up(self, distance: str = "medium") -> Action:
        """Generate swipe up action"""
        distance_px = self._get_swipe_distance(distance)
        
        x = self.screen_width // 2
        y2 = self.screen_height - self.safe_margin - 100
        y1 = max(self.safe_margin, y2 - distance_px)
        
        return Action(
            action_type=ActionType.SWIPE_UP,
            x=x,
            y=y2,
            x2=x,
            y2=y1,
            duration=300
        )
    
    def get_swipe_down(self, distance: str = "medium") -> Action:
        """Generate swipe down action"""
        distance_px = self._get_swipe_distance(distance)
        
        x = self.screen_width // 2
        y1 = self.safe_margin + 100
        y2 = min(self.screen_height - self.safe_margin, y1 + distance_px)
        
        return Action(
            action_type=ActionType.SWIPE_DOWN,
            x=x,
            y=y1,
            x2=x,
            y2=y2,
            duration=300
        )
    
    def get_swipe_left(self, distance: str = "medium") -> Action:
        """Generate swipe left action"""
        distance_px = self._get_swipe_distance(distance)
        
        y = self.screen_height // 2
        x1 = self.screen_width - self.safe_margin - 100
        x2 = max(self.safe_margin, x1 - distance_px)
        
        return Action(
            action_type=ActionType.SWIPE_LEFT,
            x=x1,
            y=y,
            x2=x2,
            y2=y,
            duration=300
        )
    
    def get_swipe_right(self, distance: str = "medium") -> Action:
        """Generate swipe right action"""
        distance_px = self._get_swipe_distance(distance)
        
        y = self.screen_height // 2
        x1 = self.safe_margin + 100
        x2 = min(self.screen_width - self.safe_margin, x1 + distance_px)
        
        return Action(
            action_type=ActionType.SWIPE_RIGHT,
            x=x1,
            y=y,
            x2=x2,
            y2=y,
            duration=300
        )
    
    def get_back_action(self) -> Action:
        """Generate back button action"""
        return Action(action_type=ActionType.BACK)
    
    def get_wait_action(self) -> Action:
        """Generate wait action"""
        return Action(action_type=ActionType.WAIT)
    
    def get_random_action(self) -> Action:
        """Generate random action"""
        action_types = [
            ActionType.TAP,
            ActionType.SWIPE_UP,
            ActionType.SWIPE_DOWN,
            ActionType.SWIPE_LEFT,
            ActionType.SWIPE_RIGHT,
        ]
        
        action_type = random.choice(action_types)
        
        if action_type == ActionType.TAP:
            return self.get_random_tap()
        elif action_type == ActionType.SWIPE_UP:
            return self.get_swipe_up()
        elif action_type == ActionType.SWIPE_DOWN:
            return self.get_swipe_down()
        elif action_type == ActionType.SWIPE_LEFT:
            return self.get_swipe_left()
        elif action_type == ActionType.SWIPE_RIGHT:
            return self.get_swipe_right()
        else:
            return self.get_wait_action()
    
    def _get_swipe_distance(self, distance: str) -> int:
        """Get swipe distance in pixels"""
        if distance == "short":
            return self.swipe_distance_short
        elif distance == "long":
            return self.swipe_distance_long
        else:
            return self.swipe_distance_medium
    
    def get_action_from_discrete(self, action_id: int) -> Action:
        """Convert discrete action ID to Action object"""
        # Discrete action space mapping
        actions = [
            self.get_random_tap,
            lambda: self.get_swipe_up("short"),
            lambda: self.get_swipe_down("short"),
            lambda: self.get_swipe_left("short"),
            lambda: self.get_swipe_right("short"),
            lambda: self.get_swipe_up("medium"),
            lambda: self.get_swipe_down("medium"),
            lambda: self.get_swipe_left("medium"),
            lambda: self.get_swipe_right("medium"),
            self.get_back_action,
            self.get_wait_action,
        ]
        
        if 0 <= action_id < len(actions):
            return actions[action_id]()
        else:
            return self.get_random_tap()
    
    def get_discrete_action_count(self) -> int:
        """Get number of discrete actions"""
        return 11  # Total discrete actions defined above
    
    def get_action_count(self) -> int:
        """Get total number of discrete actions (alias for RL agent)"""
        return self.get_discrete_action_count()
    
    def get_action_by_index(self, index: int) -> Action:
        """Get action by index (alias for get_action_from_discrete)"""
        return self.get_action_from_discrete(index)
    
    def action_to_index(self, action_type: ActionType) -> int:
        """Convert action type to discrete index"""
        # Map action types to indices
        action_map = {
            ActionType.TAP: 0,
            ActionType.SWIPE_UP: 1,
            ActionType.SWIPE_DOWN: 2,
            ActionType.SWIPE_LEFT: 3,
            ActionType.SWIPE_RIGHT: 4,
            ActionType.BACK: 9,
            ActionType.WAIT: 10
        }
        return action_map.get(action_type, 0)
