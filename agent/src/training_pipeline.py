"""
Automated Training Pipeline
Continuously improves AI from collected data
"""

import logging
import asyncio
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """
    Automated training system that continuously improves AI
    from user demonstrations and AI's own experiences
    """
    
    def __init__(
        self,
        db_manager,
        rl_agent=None,
        vision_intelligence=None,
        reward_system=None
    ):
        self.db_manager = db_manager
        self.rl_agent = rl_agent
        self.vision_intelligence = vision_intelligence
        self.reward_system = reward_system
        
        self.is_training = False
        self.training_task = None
        
        # Training configuration
        self.training_interval = 300  # Train every 5 minutes
        self.min_experiences = 50  # Minimum experiences before training
        self.batch_size = 64
        self.training_iterations = 10
        
        # Statistics
        self.total_training_sessions = 0
        self.total_experiences_used = 0
        self.last_training_time = 0
        self.training_history = []
        
        logger.info("🎓 Automated Training Pipeline initialized")
    
    async def start_training_loop(self):
        """Start continuous training in background"""
        if self.is_training:
            logger.warning("Training loop already running")
            return
        
        self.is_training = True
        self.training_task = asyncio.create_task(self._training_loop())
        logger.info("🚀 Training loop started")
    
    async def stop_training_loop(self):
        """Stop continuous training"""
        self.is_training = False
        if self.training_task:
            self.training_task.cancel()
            try:
                await self.training_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️  Training loop stopped")
    
    async def _training_loop(self):
        """Main training loop running in background"""
        logger.info("🔄 Training loop active - will train every 5 minutes")
        
        while self.is_training:
            try:
                await asyncio.sleep(self.training_interval)
                
                if not self.is_training:
                    break
                
                logger.info("⏰ Training interval reached - checking for new data...")
                
                # Check if enough new data available
                experience_count = await self._count_new_experiences()
                
                if experience_count >= self.min_experiences:
                    logger.info(f"📚 Found {experience_count} new experiences - starting training...")
                    await self.train()
                else:
                    logger.info(f"⏳ Not enough new data yet ({experience_count}/{self.min_experiences}) - waiting...")
                
            except asyncio.CancelledError:
                logger.info("Training loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
                # Continue loop even on error
    
    async def _count_new_experiences(self) -> int:
        """Count new experiences since last training"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM learning_actions
                WHERE timestamp > $1
            """
            
            last_training = self.last_training_time or 0
            result = await self.db_manager.execute_one(query, last_training)
            
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to count experiences: {e}")
            return 0
    
    async def train(self, force: bool = False) -> Dict:
        """
        Execute one training session
        
        Args:
            force: Force training even if not enough data
        
        Returns:
            Training statistics
        """
        start_time = time.time()
        logger.info("🎯 Starting training session...")
        
        stats = {
            'session_number': self.total_training_sessions + 1,
            'experiences_loaded': 0,
            'user_demos_loaded': 0,
            'ai_experiences_loaded': 0,
            'training_loss': 0.0,
            'training_iterations': 0,
            'duration_seconds': 0.0,
            'success': False
        }
        
        try:
            # 1. Load experiences from database
            experiences = await self._load_training_experiences()
            stats['experiences_loaded'] = len(experiences)
            
            if not force and len(experiences) < self.min_experiences:
                logger.warning(f"Not enough experiences ({len(experiences)}/{self.min_experiences})")
                return stats
            
            # Separate user demonstrations from AI experiences
            user_demos = [e for e in experiences if e.get('is_user_action')]
            ai_experiences = [e for e in experiences if not e.get('is_user_action')]
            
            stats['user_demos_loaded'] = len(user_demos)
            stats['ai_experiences_loaded'] = len(ai_experiences)
            
            logger.info(f"📊 Loaded {len(experiences)} experiences: "
                       f"{len(user_demos)} user demos, {len(ai_experiences)} AI experiences")
            
            # 2. Train RL agent if available
            if self.rl_agent and ai_experiences:
                rl_stats = await self._train_rl_agent(ai_experiences)
                stats['training_loss'] = rl_stats.get('avg_loss', 0.0)
                stats['training_iterations'] = rl_stats.get('iterations', 0)
            
            # 3. Learn from user demonstrations
            if user_demos:
                await self._learn_from_user_demos(user_demos)
            
            # 4. Update statistics
            self.total_training_sessions += 1
            self.total_experiences_used += len(experiences)
            self.last_training_time = time.time()
            
            stats['duration_seconds'] = time.time() - start_time
            stats['success'] = True
            
            # Store training history
            self.training_history.append(stats)
            if len(self.training_history) > 100:
                self.training_history.pop(0)
            
            logger.info(f"✅ Training complete! "
                       f"Loss: {stats['training_loss']:.4f}, "
                       f"Duration: {stats['duration_seconds']:.1f}s")
            
            # Save model checkpoint
            await self._save_model_checkpoint()
            
            return stats
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            stats['error'] = str(e)
            return stats
    
    async def _load_training_experiences(self) -> list:
        """Load recent experiences for training"""
        try:
            query = """
                SELECT 
                    session_id, game_id, action_type, action_params,
                    screenshot_before, screenshot_after,
                    is_user_action, game_state, reward, success,
                    led_to_progress, ui_elements, detected_text
                FROM learning_actions
                WHERE timestamp > NOW() - INTERVAL '1 day'
                ORDER BY timestamp DESC
                LIMIT 1000
            """
            
            results = await self.db_manager.execute(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to load experiences: {e}")
            return []
    
    async def _train_rl_agent(self, experiences: list) -> Dict:
        """Train RL agent on experiences"""
        if not self.rl_agent:
            return {'iterations': 0, 'avg_loss': 0.0}
        
        logger.info(f"🤖 Training RL agent on {len(experiences)} experiences...")
        
        total_loss = 0.0
        iterations = 0
        
        try:
            # Convert experiences to RL format
            for exp in experiences:
                # Extract state, action, reward, next_state
                state = self._experience_to_state(exp)
                action = exp.get('action_type')
                reward = exp.get('reward', 0.0)
                next_state = self._experience_to_state(exp, use_after=True)
                done = exp.get('episode_done', False)
                
                # Store in RL agent's replay buffer
                if hasattr(self.rl_agent, 'remember'):
                    self.rl_agent.remember(state, action, reward, next_state, done)
            
            # Train for multiple iterations
            for i in range(self.training_iterations):
                if hasattr(self.rl_agent, 'train') and len(self.rl_agent.memory) >= self.batch_size:
                    loss = await asyncio.to_thread(
                        self.rl_agent.train,
                        batch_size=self.batch_size
                    )
                    total_loss += loss
                    iterations += 1
            
            avg_loss = total_loss / iterations if iterations > 0 else 0.0
            
            logger.info(f"✅ RL training complete: {iterations} iterations, avg loss: {avg_loss:.4f}")
            
            return {
                'iterations': iterations,
                'avg_loss': avg_loss
            }
            
        except Exception as e:
            logger.error(f"RL training failed: {e}")
            return {'iterations': 0, 'avg_loss': 0.0}
    
    def _experience_to_state(self, experience: Dict, use_after: bool = False) -> list:
        """Convert experience to state vector for RL"""
        # Simple state representation (can be enhanced)
        state = []
        
        # UI elements count
        ui_elements = experience.get('ui_elements', [])
        state.append(len(ui_elements))
        
        # Text detected
        detected_text = experience.get('detected_text', '')
        state.append(len(detected_text.split()))
        
        # Game state features
        game_state = experience.get('game_state', {})
        state.append(game_state.get('level', 0))
        state.append(game_state.get('score', 0))
        
        # Pad to fixed size (128 features)
        while len(state) < 128:
            state.append(0.0)
        
        return state[:128]
    
    async def _learn_from_user_demos(self, user_demos: list):
        """Process and store patterns from user demonstrations"""
        logger.info(f"👤 Learning from {len(user_demos)} user demonstrations...")
        
        try:
            # Extract patterns
            patterns = {}
            
            for demo in user_demos:
                # Create pattern: screen_state -> action -> outcome
                screen_state = self._hash_screen_state(demo)
                action = demo.get('action_type')
                outcome = 'positive' if demo.get('led_to_progress') else 'neutral'
                
                pattern_key = f"{screen_state}_{action}"
                
                if pattern_key not in patterns:
                    patterns[pattern_key] = {
                        'count': 0,
                        'positive_outcomes': 0,
                        'total_reward': 0.0
                    }
                
                patterns[pattern_key]['count'] += 1
                if outcome == 'positive':
                    patterns[pattern_key]['positive_outcomes'] += 1
                patterns[pattern_key]['total_reward'] += demo.get('reward', 0.0)
            
            # Store valuable patterns
            valuable_patterns = {
                k: v for k, v in patterns.items()
                if v['positive_outcomes'] / v['count'] > 0.6  # >60% success rate
            }
            
            logger.info(f"📈 Extracted {len(valuable_patterns)} valuable patterns from user demos")
            
            # TODO: Store patterns in database for quick lookup
            
        except Exception as e:
            logger.error(f"Failed to learn from user demos: {e}")
    
    def _hash_screen_state(self, experience: Dict) -> str:
        """Create a hash of screen state for pattern matching"""
        # Simple hash based on UI elements and text
        ui_count = len(experience.get('ui_elements', []))
        text_words = len(experience.get('detected_text', '').split())
        
        return f"ui{ui_count}_text{text_words}"
    
    async def _save_model_checkpoint(self):
        """Save trained model checkpoint"""
        try:
            if self.rl_agent and hasattr(self.rl_agent, 'save'):
                checkpoint_path = f"/app/data/rl_model_checkpoint_{int(time.time())}.pkl"
                await asyncio.to_thread(self.rl_agent.save, checkpoint_path)
                logger.info(f"💾 Model checkpoint saved: {checkpoint_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def get_training_stats(self) -> Dict:
        """Get training pipeline statistics"""
        return {
            'is_training': self.is_training,
            'total_sessions': self.total_training_sessions,
            'total_experiences_used': self.total_experiences_used,
            'last_training_time': self.last_training_time,
            'training_interval_seconds': self.training_interval,
            'recent_history': self.training_history[-10:]  # Last 10 sessions
        }
