"""
Reinforcement Learning Agent - Phase 3 Implementation
Experience-based learning for continuous gameplay improvement
"""
import logging
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque, defaultdict
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class GameState:
    """Represents a simplified game state for RL"""
    
    def __init__(self, screen_hash: str, ocr_features: List, ui_features: List):
        self.screen_hash = screen_hash
        self.ocr_features = ocr_features  # Text keywords present
        self.ui_features = ui_features    # UI element counts/positions
        
    def to_key(self) -> str:
        """Convert state to hashable key for Q-table"""
        # Simple state representation: screen_hash + feature counts
        ocr_count = len(self.ocr_features)
        ui_count = len(self.ui_features)
        return f"{self.screen_hash[:8]}_{ocr_count}_{ui_count}"


class ExperienceReplay:
    """Store and replay past experiences for learning"""
    
    def __init__(self, max_size: int = 10000):
        self.buffer = deque(maxlen=max_size)
        self.positive_buffer = deque(maxlen=1000)  # Store successful experiences
        
    def add(self, state: str, action: Dict, reward: float, next_state: str, done: bool):
        """Add experience to buffer"""
        experience = {
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done
        }
        self.buffer.append(experience)
        
        # Store positive experiences separately
        if reward > 0:
            self.positive_buffer.append(experience)
    
    def sample(self, batch_size: int = 32) -> List[Dict]:
        """Sample random batch from buffer"""
        if len(self.buffer) < batch_size:
            return list(self.buffer)
        
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        return [self.buffer[i] for i in indices]
    
    def get_positive_samples(self, count: int = 10) -> List[Dict]:
        """Get successful experiences for imitation"""
        if len(self.positive_buffer) < count:
            return list(self.positive_buffer)
        
        indices = np.random.choice(len(self.positive_buffer), count, replace=False)
        return [self.positive_buffer[i] for i in indices]


class QLearningAgent:
    """
    Q-Learning agent for game playing with experience replay
    
    Uses simplified Q-table approach suitable for mobile games:
    - State: Screen type + feature counts
    - Actions: tap(x,y), swipe(x1,y1,x2,y2), back
    - Rewards: Level progress, completion, stuck penalties
    """
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.3,  # Exploration rate
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.05
    ):
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        
        # Q-table: state -> action -> Q-value
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        # Experience replay
        self.replay = ExperienceReplay(max_size=10000)
        
        # Action space tracking
        self.action_counts = defaultdict(int)
        self.successful_actions = defaultdict(list)  # state -> [successful actions]
        
        # Statistics
        self.total_episodes = 0
        self.total_rewards = 0
        self.episode_rewards = []
        
        logger.info("🧠 RL Agent initialized with Q-Learning")
    
    def get_state_key(self, state_info: Dict) -> str:
        """Convert game state to Q-table key"""
        screen_type = state_info.get('screen_type', 'unknown')
        ocr_count = len(state_info.get('ocr_text', []))
        ui_count = len(state_info.get('ui_elements', []))
        stuck_count = state_info.get('stuck_count', 0)
        
        return f"{screen_type}_{ocr_count}_{ui_count}_{min(stuck_count, 5)}"
    
    def choose_action(
        self,
        state_key: str,
        available_actions: List[Dict],
        explore: bool = True
    ) -> Optional[Dict]:
        """
        Choose action using epsilon-greedy strategy
        
        Args:
            state_key: Current state identifier
            available_actions: List of possible actions from other agents
            explore: Whether to explore (True) or exploit only (False)
            
        Returns:
            Selected action dict or None if no good action found
        """
        if not available_actions:
            return None
        
        # Exploration: try random action
        if explore and np.random.random() < self.epsilon:
            action = np.random.choice(available_actions)
            logger.debug(f"🎲 RL exploring: random action (ε={self.epsilon:.3f})")
            return action
        
        # Exploitation: choose best known action
        best_action = None
        best_q_value = float('-inf')
        
        for action in available_actions:
            action_key = self._action_to_key(action)
            q_value = self.q_table[state_key][action_key]
            
            if q_value > best_q_value:
                best_q_value = q_value
                best_action = action
        
        # If no learned actions, return highest confidence action
        if best_q_value == 0 and available_actions:
            best_action = max(available_actions, key=lambda a: a.get('confidence', 0))
            logger.debug("🎯 RL: No Q-values, using highest confidence action")
        elif best_action:
            logger.debug(f"🧠 RL exploiting: Q={best_q_value:.3f}")
        
        return best_action
    
    def update_q_value(
        self,
        state_key: str,
        action: Dict,
        reward: float,
        next_state_key: str,
        done: bool = False
    ):
        """
        Update Q-value using Q-learning update rule:
        Q(s,a) = Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]
        """
        action_key = self._action_to_key(action)
        
        current_q = self.q_table[state_key][action_key]
        
        if done:
            # Terminal state: no future reward
            max_future_q = 0
        else:
            # Get max Q-value for next state
            next_actions = self.q_table[next_state_key]
            max_future_q = max(next_actions.values()) if next_actions else 0
        
        # Q-learning update
        new_q = current_q + self.lr * (reward + self.gamma * max_future_q - current_q)
        self.q_table[state_key][action_key] = new_q
        
        # Store experience
        self.replay.add(state_key, action, reward, next_state_key, done)
        
        # Track successful actions
        if reward > 0:
            if state_key not in self.successful_actions:
                self.successful_actions[state_key] = []
            self.successful_actions[state_key].append(action)
        
        self.total_rewards += reward
        
        logger.debug(f"📊 Q-update: {state_key} -> {action_key[:20]}... | R={reward:.2f} | Q: {current_q:.3f} -> {new_q:.3f}")
    
    def replay_experiences(self, batch_size: int = 32):
        """Learn from past experiences (experience replay)"""
        if len(self.replay.buffer) < batch_size:
            return
        
        batch = self.replay.sample(batch_size)
        
        for exp in batch:
            self.update_q_value(
                exp['state'],
                exp['action'],
                exp['reward'],
                exp['next_state'],
                exp['done']
            )
        
        logger.debug(f"🔄 Replayed {len(batch)} experiences")
    
    def decay_epsilon(self):
        """Reduce exploration rate over time"""
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            logger.debug(f"📉 Epsilon decayed to {self.epsilon:.3f}")
    
    def end_episode(self, episode_reward: float):
        """Mark end of episode and update statistics"""
        self.total_episodes += 1
        self.episode_rewards.append(episode_reward)
        
        # Decay exploration
        self.decay_epsilon()
        
        # Replay experiences
        self.replay_experiences(batch_size=32)
        
        logger.info(f"📈 Episode {self.total_episodes} ended | Reward: {episode_reward:.2f} | ε={self.epsilon:.3f}")
    
    def _action_to_key(self, action: Dict) -> str:
        """Convert action dict to hashable key"""
        action_type = action.get('action', 'tap')
        
        if action_type == 'tap':
            x, y = action.get('coordinates', (0, 0))
            # Discretize coordinates to regions (10x10 grid)
            region_x = int(x / 108)  # 1080/10
            region_y = int(y / 192)  # 1920/10
            return f"tap_{region_x}_{region_y}"
        elif action_type == 'swipe':
            # Simplified swipe representation
            return f"swipe_{action.get('direction', 'unknown')}"
        else:
            return action_type
    
    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        avg_reward = np.mean(self.episode_rewards[-100:]) if self.episode_rewards else 0
        
        return {
            'total_episodes': self.total_episodes,
            'total_rewards': self.total_rewards,
            'avg_recent_reward': avg_reward,
            'epsilon': self.epsilon,
            'q_table_size': len(self.q_table),
            'experiences': len(self.replay.buffer),
            'positive_experiences': len(self.replay.positive_buffer)
        }
    
    def save_model(self, filepath: str):
        """Save Q-table and statistics"""
        data = {
            'q_table': dict(self.q_table),
            'successful_actions': dict(self.successful_actions),
            'epsilon': self.epsilon,
            'total_episodes': self.total_episodes,
            'total_rewards': self.total_rewards,
            'episode_rewards': self.episode_rewards
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"💾 RL model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load Q-table and statistics"""
        if not Path(filepath).exists():
            logger.warning(f"Model file not found: {filepath}")
            return
        
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.q_table = defaultdict(lambda: defaultdict(float), data['q_table'])
        self.successful_actions = defaultdict(list, data.get('successful_actions', {}))
        self.epsilon = data.get('epsilon', self.epsilon)
        self.total_episodes = data.get('total_episodes', 0)
        self.total_rewards = data.get('total_rewards', 0)
        self.episode_rewards = data.get('episode_rewards', [])
        
        logger.info(f"📂 RL model loaded from {filepath} | Episodes: {self.total_episodes}")


class RewardCalculator:
    """Calculate rewards for RL training"""
    
    @staticmethod
    def calculate_reward(
        prev_state: Dict,
        new_state: Dict,
        action_result: Dict
    ) -> float:
        """
        Calculate reward based on state transition
        
        Reward structure:
        +10: Level completed
        +5: Progress detected (screen changed meaningfully)
        +1: Screen changed
        -1: No change (stuck)
        -3: Screen moved backward (worse than before)
        -5: Game over / failure
        """
        reward = 0.0
        
        # Check for completion
        if new_state.get('screen_type') == 'completion':
            reward += 10.0
            logger.info("🎉 +10 reward: Level completed!")
            return reward
        
        # Check for failure
        if new_state.get('screen_type') == 'failure':
            reward -= 5.0
            logger.info("💀 -5 reward: Game over")
            return reward
        
        # Check if screen changed
        prev_hash = prev_state.get('screen_hash', '')
        new_hash = new_state.get('screen_hash', '')
        
        if prev_hash != new_hash:
            # Screen changed - good!
            reward += 1.0
            
            # Bonus for progressing from menu to gameplay
            if prev_state.get('screen_type') == 'menu' and new_state.get('screen_type') == 'gameplay':
                reward += 3.0
                logger.info("🎮 +4 reward: Started gameplay")
            else:
                logger.debug("✅ +1 reward: Screen changed")
        else:
            # Screen didn't change - stuck
            reward -= 1.0
            logger.debug("❌ -1 reward: No progress")
        
        # Check UI element changes (objects removed/added)
        prev_ui_count = len(prev_state.get('ui_elements', []))
        new_ui_count = len(new_state.get('ui_elements', []))
        
        if abs(prev_ui_count - new_ui_count) > 2:
            # Significant UI change (e.g., screw removed)
            reward += 2.0
            logger.debug(f"⭐ +2 reward: UI changed ({prev_ui_count} -> {new_ui_count} elements)")
        
        return reward
