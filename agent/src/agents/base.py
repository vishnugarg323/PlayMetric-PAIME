"""
Base Agent - Abstract base class for all agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np


class BaseAgent(ABC):
    """Base class for all game-playing agents"""
    
    def __init__(self, action_space, config: Dict[str, Any]):
        self.action_space = action_space
        self.config = config
        self.action_count = 0
        self.episode_reward = 0.0
        
    @abstractmethod
    def decide_action(self, observation: Dict[str, Any]):
        """
        Decide next action based on observation
        
        Args:
            observation: Dict containing 'screenshot', 'ui_elements', etc.
            
        Returns:
            Action object
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset agent state for new episode"""
        pass
    
    def update_reward(self, reward: float):
        """Update episode reward"""
        self.episode_reward += reward
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "total_actions": self.action_count,
            "episode_reward": self.episode_reward
        }
