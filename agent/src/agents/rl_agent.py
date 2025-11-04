"""
RL Agent - Reinforcement Learning agent using Deep Q-Network
"""
import os
import logging
from typing import Dict, Any
import numpy as np
import cv2
from .base import BaseAgent

logger = logging.getLogger(__name__)

# Import RL libraries
try:
    from stable_baselines3 import DQN
    from stable_baselines3.common.vec_env import DummyVecEnv
    RL_AVAILABLE = True
except ImportError:
    logger.warning("Stable-Baselines3 not available. RL agent will use random actions.")
    RL_AVAILABLE = False


class RLAgent(BaseAgent):
    """Reinforcement Learning agent using DQN"""
    
    def __init__(self, action_space, config: Dict[str, Any]):
        super().__init__(action_space, config)
        
        self.model = None
        self.model_path = config.get('model_path', '/data/models/dqn_model.zip')
        self.learning_rate = config.get('learning_rate', 0.0003)
        self.exploration_rate = config.get('exploration_rate', 0.1)
        
        # Load model if exists
        if RL_AVAILABLE and os.path.exists(self.model_path):
            try:
                self.model = DQN.load(self.model_path)
                logger.info(f"Loaded RL model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
        
        self.episode_observations = []
        self.episode_actions = []
        self.episode_rewards = []
        
    def decide_action(self, observation: Dict[str, Any]):
        """Decide action using RL model or exploration"""
        screenshot = observation.get('screenshot')
        
        # Preprocess observation
        obs_array = self._preprocess_observation(screenshot)
        self.episode_observations.append(obs_array)
        
        # If model not loaded or exploring
        if not self.model or np.random.random() < self.exploration_rate:
            action = self.action_space.get_random_action()
            logger.debug("RL agent exploring (random action)")
        else:
            try:
                # Predict action using model
                action_id, _ = self.model.predict(obs_array, deterministic=True)
                action = self.action_space.get_action_from_discrete(int(action_id))
                logger.debug(f"RL agent decided action: {action.action_type.value}")
            except Exception as e:
                logger.error(f"Error predicting action: {e}")
                action = self.action_space.get_random_action()
        
        self.action_count += 1
        self.episode_actions.append(action)
        
        return action
    
    def _preprocess_observation(self, screenshot_path: str) -> np.ndarray:
        """Preprocess screenshot for model input"""
        try:
            if not screenshot_path or not os.path.exists(screenshot_path):
                # Return empty observation
                return np.zeros((84, 84, 3), dtype=np.uint8)
            
            # Load and resize image
            img = cv2.imread(screenshot_path)
            if img is None:
                return np.zeros((84, 84, 3), dtype=np.uint8)
            
            # Resize to 84x84 (common for DQN)
            img = cv2.resize(img, (84, 84))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            return img
            
        except Exception as e:
            logger.error(f"Error preprocessing observation: {e}")
            return np.zeros((84, 84, 3), dtype=np.uint8)
    
    def learn_from_episode(self):
        """Learn from collected episode data"""
        if not RL_AVAILABLE or not self.model:
            logger.warning("Cannot learn: RL not available or model not loaded")
            return
        
        if len(self.episode_observations) < 2:
            return
        
        try:
            # This is a simplified version
            # In production, you'd use a proper replay buffer and training loop
            logger.info(f"Episode completed with {len(self.episode_actions)} actions")
            
            # Save model periodically
            if self.action_count % 1000 == 0:
                self.save_model()
                
        except Exception as e:
            logger.error(f"Error learning from episode: {e}")
    
    def save_model(self):
        """Save model to disk"""
        if not self.model:
            return
        
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path)
            logger.info(f"Saved model to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def reset(self):
        """Reset episode data"""
        self.action_count = 0
        self.episode_reward = 0.0
        self.episode_observations.clear()
        self.episode_actions.clear()
        self.episode_rewards.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        stats = super().get_statistics()
        stats["model_loaded"] = self.model is not None
        stats["exploration_rate"] = self.exploration_rate
        stats["episode_length"] = len(self.episode_actions)
        return stats
