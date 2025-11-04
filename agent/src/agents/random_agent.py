"""
Random Agent - Performs random actions
"""
import random
import logging
from typing import Dict, Any
from .base import BaseAgent

logger = logging.getLogger(__name__)


class RandomAgent(BaseAgent):
    """Agent that performs random actions"""
    
    def __init__(self, action_space, config: Dict[str, Any]):
        super().__init__(action_space, config)
        self.action_history = []
        
    def decide_action(self, observation: Dict[str, Any]):
        """Choose random action"""
        action = self.action_space.get_random_action()
        self.action_count += 1
        self.action_history.append(action.action_type.value)
        
        logger.debug(f"Random action: {action.action_type.value}")
        return action
    
    def reset(self):
        """Reset agent state"""
        self.action_count = 0
        self.episode_reward = 0.0
        self.action_history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        stats = super().get_statistics()
        
        # Add action distribution
        action_counts = {}
        for action in self.action_history:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        stats["action_distribution"] = action_counts
        return stats
