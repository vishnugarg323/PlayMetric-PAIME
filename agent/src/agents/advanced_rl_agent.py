"""
Advanced DQN Agent with Experience Replay and Shared Learning
Optimized for simple puzzle games (match-3, screw games, traffic jam, etc.)
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import List, Tuple, Optional, Dict
from collections import deque
import random
import json
import os
import logging
from datetime import datetime
import cv2

logger = logging.getLogger(__name__)


class SimplePuzzleDQN(nn.Module):
    """
    Deep Q-Network optimized for simple puzzle games
    Input: Screen features (preprocessed image)
    Output: Q-values for each possible action
    """
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super(SimplePuzzleDQN, self).__init__()
        
        # Feature extraction network
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )
    
    def forward(self, x):
        return self.network(x)


class PrioritizedReplayBuffer:
    """
    Prioritized Experience Replay Buffer with PostgreSQL backing
    Stores experiences in DB for cross-session learning
    """
    
    def __init__(
        self, 
        capacity: int = 100000,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 0.001
    ):
        self.capacity = capacity
        self.alpha = alpha  # Prioritization exponent
        self.beta = beta  # Importance sampling exponent
        self.beta_increment = beta_increment
        self.epsilon = 1e-6  # Small constant to prevent zero priority
        
        # In-memory buffer for recent experiences
        self.buffer = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        
        # DB manager will be injected
        self.db_manager = None
        self.game_id = None
        self.session_id = None
    
    def set_context(self, db_manager, game_id: str, session_id: str):
        """Set database context for storing experiences"""
        self.db_manager = db_manager
        self.game_id = game_id
        self.session_id = session_id
    
    async def push(
        self,
        state: np.ndarray,
        action: int,
        action_params: dict,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        level_identifier: str = None,
        difficulty_estimate: float = 0.5
    ):
        """Add experience to buffer and database"""
        # Calculate initial priority (TD error not available yet)
        priority = max(self.priorities) if self.priorities else 1.0
        
        # Add to in-memory buffer
        experience = {
            'state': state,
            'action': action,
            'action_params': action_params,
            'reward': reward,
            'next_state': next_state,
            'done': done,
            'level_identifier': level_identifier,
            'difficulty_estimate': difficulty_estimate
        }
        self.buffer.append(experience)
        self.priorities.append(priority)
        
        # Store in database for long-term learning
        if self.db_manager and self.game_id:
            try:
                state_hash = self._hash_state(state)
                action_type = self._action_to_type(action)
                
                query = """
                INSERT INTO rl_experiences (
                    game_id, session_id, state_features, state_hash,
                    action_type, action_params, reward, next_state_features,
                    done, level_identifier, difficulty_estimate, priority
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """
                
                await self.db_manager.execute_write(
                    query,
                    self.game_id,
                    self.session_id,
                    state.tolist(),
                    state_hash,
                    action_type,
                    json.dumps(action_params),
                    reward,
                    next_state.tolist(),
                    done,
                    level_identifier,
                    difficulty_estimate,
                    priority
                )
            except Exception as e:
                logger.error(f"Failed to store experience in DB: {e}")
    
    def sample(self, batch_size: int) -> Tuple[List, np.ndarray]:
        """Sample batch with prioritized sampling"""
        if len(self.buffer) < batch_size:
            batch_size = len(self.buffer)
        
        # Calculate sampling probabilities
        priorities_array = np.array(self.priorities)
        probabilities = priorities_array ** self.alpha
        probabilities /= probabilities.sum()
        
        # Sample indices
        indices = np.random.choice(
            len(self.buffer), 
            batch_size, 
            p=probabilities,
            replace=False
        )
        
        # Calculate importance sampling weights
        weights = (len(self.buffer) * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()  # Normalize
        
        # Increase beta over time
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        # Get experiences
        batch = [self.buffer[idx] for idx in indices]
        
        return batch, weights
    
    def update_priorities(self, indices: List[int], td_errors: np.ndarray):
        """Update priorities based on TD errors"""
        for idx, td_error in zip(indices, td_errors):
            priority = (abs(td_error) + self.epsilon) ** self.alpha
            self.priorities[idx] = priority
    
    async def load_from_db(self, game_id: str, limit: int = 10000):
        """Load experiences from database for transfer learning"""
        if not self.db_manager:
            return
        
        try:
            query = """
            SELECT state_features, action_type, action_params, reward,
                   next_state_features, done, level_identifier, 
                   difficulty_estimate, priority
            FROM rl_experiences
            WHERE game_id = $1
            ORDER BY priority DESC, timestamp DESC
            LIMIT $2
            """
            
            rows = await self.db_manager.execute(query, game_id, limit)
            
            for row in rows:
                action = self._type_to_action(row['action_type'])
                action_params = json.loads(row['action_params'])
                
                experience = {
                    'state': np.array(row['state_features']),
                    'action': action,
                    'action_params': action_params,
                    'reward': row['reward'],
                    'next_state': np.array(row['next_state_features']),
                    'done': row['done'],
                    'level_identifier': row['level_identifier'],
                    'difficulty_estimate': row['difficulty_estimate']
                }
                
                self.buffer.append(experience)
                self.priorities.append(row['priority'])
            
            logger.info(f"Loaded {len(rows)} experiences from database")
        except Exception as e:
            logger.error(f"Failed to load experiences from DB: {e}")
    
    def _hash_state(self, state: np.ndarray) -> str:
        """Create hash of state for deduplication"""
        return hash(state.tobytes()).to_bytes(8, 'big', signed=True).hex()
    
    def _action_to_type(self, action: int) -> str:
        """Convert action index to type string"""
        action_types = [
            'tap_center', 'tap_top', 'tap_bottom', 'tap_left', 'tap_right',
            'swipe_up', 'swipe_down', 'swipe_left', 'swipe_right',
            'back', 'home'
        ]
        return action_types[action] if action < len(action_types) else 'tap_center'
    
    def _type_to_action(self, action_type: str) -> int:
        """Convert action type string to index"""
        action_types = [
            'tap_center', 'tap_top', 'tap_bottom', 'tap_left', 'tap_right',
            'swipe_up', 'swipe_down', 'swipe_left', 'swipe_right',
            'back', 'home'
        ]
        try:
            return action_types.index(action_type)
        except ValueError:
            return 0  # Default to tap_center
    
    def __len__(self):
        return len(self.buffer)


class AdvancedRLAgent:
    """
    Advanced RL Agent with:
    - DQN with target network
    - Prioritized experience replay
    - Cross-session learning via database
    - Puzzle-specific optimizations
    """
    
    def __init__(
        self,
        state_dim: int = 128,
        action_dim: int = 11,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        batch_size: int = 64,
        target_update_freq: int = 1000,
        device: str = "cpu"
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.device = torch.device(device)
        
        # Epsilon-greedy exploration
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        
        # Neural networks
        self.policy_net = SimplePuzzleDQN(state_dim, action_dim).to(self.device)
        self.target_net = SimplePuzzleDQN(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # Optimizer
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # Experience replay
        self.memory = PrioritizedReplayBuffer()
        
        # Training stats
        self.steps = 0
        self.episodes = 0
        self.total_reward = 0.0
        self.losses = []
        
        # Feature extractor for screen images
        self.feature_extractor = ScreenFeatureExtractor(state_dim)
    
    async def initialize_from_db(self, db_manager, game_id: str, session_id: str):
        """Initialize agent with database context and load past experiences"""
        self.memory.set_context(db_manager, game_id, session_id)
        
        # Try to load pre-trained model
        await self.load_model(game_id)
        
        # Load past experiences for transfer learning
        await self.memory.load_from_db(game_id, limit=10000)
        
        logger.info(f"Initialized RL agent with {len(self.memory)} experiences")
    
    def preprocess_observation(self, screenshot: np.ndarray) -> np.ndarray:
        """Convert screenshot to state features"""
        return self.feature_extractor.extract(screenshot)
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Select action using epsilon-greedy policy"""
        # Store whether this is exploration
        self.last_exploration_action = None
        
        if training and random.random() < self.epsilon:
            action = random.randint(0, self.action_dim - 1)
            self.last_exploration_action = action
            self.last_q_values = None
            return action
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            self.last_q_values = q_values.squeeze().cpu().numpy()
            return q_values.argmax().item()
    
    async def store_transition(
        self,
        state: np.ndarray,
        action: int,
        action_params: dict,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        level_identifier: str = None
    ):
        """Store transition in replay buffer and database"""
        await self.memory.push(
            state, action, action_params, reward, next_state, done,
            level_identifier=level_identifier
        )
    
    def train_step(self) -> Optional[float]:
        """Perform one training step"""
        if len(self.memory) < self.batch_size:
            return None
        
        # Sample batch with prioritized replay
        batch, weights = self.memory.sample(self.batch_size)
        
        # Prepare tensors
        states = torch.FloatTensor(np.array([e['state'] for e in batch])).to(self.device)
        actions = torch.LongTensor([e['action'] for e in batch]).to(self.device)
        rewards = torch.FloatTensor([e['reward'] for e in batch]).to(self.device)
        next_states = torch.FloatTensor(np.array([e['next_state'] for e in batch])).to(self.device)
        dones = torch.FloatTensor([e['done'] for e in batch]).to(self.device)
        weights_tensor = torch.FloatTensor(weights).to(self.device)
        
        # Current Q values
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        
        # Next Q values (Double DQN)
        with torch.no_grad():
            # Use policy network to select actions
            next_actions = self.policy_net(next_states).argmax(1)
            # Use target network to evaluate actions
            next_q_values = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze()
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # Compute TD errors for priority update
        td_errors = (target_q_values - current_q_values).detach().cpu().numpy()
        
        # Weighted loss (importance sampling)
        loss = (weights_tensor * (current_q_values - target_q_values).pow(2)).mean()
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        # Update target network periodically
        self.steps += 1
        if self.steps % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        
        # Track loss
        loss_value = loss.item()
        self.losses.append(loss_value)
        
        return loss_value
    
    async def save_model(self, game_id: str, version: int = 1):
        """Save model to disk and register in database"""
        os.makedirs("/data/models", exist_ok=True)
        model_path = f"/data/models/dqn_{game_id}_v{version}.pt"
        
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps': self.steps,
            'episodes': self.episodes
        }, model_path)
        
        # Register in database
        if self.memory.db_manager:
            try:
                avg_reward = np.mean(self.losses[-1000:]) if self.losses else 0.0
                
                query = """
                INSERT INTO rl_models (
                    game_id, model_name, algorithm, version, model_path,
                    training_episodes, training_steps, average_reward,
                    hyperparameters
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (game_id, model_name, version) 
                DO UPDATE SET
                    training_episodes = $6,
                    training_steps = $7,
                    average_reward = $8
                """
                
                hyperparams = {
                    'learning_rate': self.optimizer.param_groups[0]['lr'],
                    'gamma': self.gamma,
                    'batch_size': self.batch_size,
                    'epsilon': self.epsilon
                }
                
                await self.memory.db_manager.execute_write(
                    query, game_id, 'dqn', 'DQN', version, model_path,
                    self.episodes, self.steps, avg_reward, json.dumps(hyperparams)
                )
                
                logger.info(f"Saved model: {model_path}")
            except Exception as e:
                logger.error(f"Failed to register model in DB: {e}")
    
    async def load_model(self, game_id: str):
        """Load latest model for this game"""
        if not self.memory.db_manager:
            return
        
        try:
            query = """
            SELECT model_path FROM rl_models
            WHERE game_id = $1 AND status = 'active'
            ORDER BY version DESC
            LIMIT 1
            """
            
            row = await self.memory.db_manager.execute_one(query, game_id)
            
            if row and os.path.exists(row['model_path']):
                checkpoint = torch.load(row['model_path'], map_location=self.device)
                self.policy_net.load_state_dict(checkpoint['policy_net'])
                self.target_net.load_state_dict(checkpoint['target_net'])
                self.optimizer.load_state_dict(checkpoint['optimizer'])
                self.epsilon = checkpoint.get('epsilon', self.epsilon)
                self.steps = checkpoint.get('steps', 0)
                self.episodes = checkpoint.get('episodes', 0)
                
                logger.info(f"Loaded model from {row['model_path']}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")


class ScreenFeatureExtractor:
    """Extract features from game screenshots optimized for puzzle games"""
    
    def __init__(self, output_dim: int = 128):
        self.output_dim = output_dim
    
    def extract(self, screenshot: np.ndarray) -> np.ndarray:
        """Extract features from screenshot"""
        if screenshot is None or screenshot.size == 0:
            return np.zeros(self.output_dim)
        
        try:
            # Resize to standard size
            img = cv2.resize(screenshot, (84, 84))
            
            # Convert to grayscale
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # Normalize
            normalized = gray.astype(np.float32) / 255.0
            
            # Extract features
            features = []
            
            # 1. Histogram (16 bins)
            hist = cv2.calcHist([gray], [0], None, [16], [0, 256]).flatten()
            features.extend(hist / hist.sum())
            
            # 2. Edge detection
            edges = cv2.Canny(gray, 50, 150)
            edge_density = edges.sum() / edges.size
            features.append(edge_density)
            
            # 3. Grid features (divide into 3x3 grid)
            h, w = normalized.shape
            for i in range(3):
                for j in range(3):
                    cell = normalized[i*h//3:(i+1)*h//3, j*w//3:(j+1)*w//3]
                    features.extend([
                        cell.mean(),
                        cell.std(),
                        cell.max()
                    ])
            
            # 4. Flattened downsampled image
            downsampled = cv2.resize(normalized, (10, 10)).flatten()
            features.extend(downsampled)
            
            # Pad or truncate to output_dim
            features = np.array(features)
            if len(features) < self.output_dim:
                features = np.pad(features, (0, self.output_dim - len(features)))
            else:
                features = features[:self.output_dim]
            
            return features.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return np.zeros(self.output_dim)
