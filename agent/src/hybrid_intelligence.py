"""
Hybrid Intelligence System - Integration of All Phases
Combines CV (Phase 1), Vision AI (Phase 2), and RL (Phase 3)
"""
import logging
from typing import Dict, List, Optional, Tuple
import hashlib
from pathlib import Path

from .advanced_game_intelligence import AdvancedGameIntelligence, GameState as CVGameState
from .vision_ai_agent import VisionAIAgent
from .rl_agent import QLearningAgent, RewardCalculator

logger = logging.getLogger(__name__)


class HybridGameIntelligence:
    """
    Three-phase intelligent game playing system:
    
    Phase 1 (CV): Fast computer vision analysis (< 100ms)
    Phase 2 (Vision AI): Deep visual understanding via Gemini (2-3s)
    Phase 3 (RL): Experience-based learning and optimization
    
    Decision Flow:
    1. Always run Phase 1 (CV) for quick analysis
    2. Run Phase 2 (Vision AI) if:
       - CV confidence < 0.5
       - Stuck for 3+ actions
       - Complex visual scene
    3. Phase 3 (RL) learns from all decisions to improve over time
    """
    
    def __init__(
        self,
        screen_dimensions: Tuple[int, int] = (1080, 1920),
        gemini_api_key: Optional[str] = None,
        rl_model_path: Optional[str] = None,
        enable_vision_ai: bool = True,
        enable_rl: bool = True
    ):
        self.width, self.height = screen_dimensions
        
        # Initialize all three phases
        self.cv_agent = AdvancedGameIntelligence(screen_dimensions)
        self.vision_ai = VisionAIAgent(api_key=gemini_api_key) if enable_vision_ai else None
        self.rl_agent = QLearningAgent() if enable_rl else None
        
        # Load RL model if path provided
        if self.rl_agent and rl_model_path:
            self.rl_agent.load_model(rl_model_path)
        
        # Tracking
        self.previous_state = None
        self.current_state = None
        self.decision_history = []
        self.vision_ai_calls = 0
        self.max_vision_calls_per_session = 500  # Rate limit
        
        # Statistics
        self.stats = {
            'cv_decisions': 0,
            'vision_ai_decisions': 0,
            'rl_decisions': 0,
            'total_actions': 0
        }
        
        phases_enabled = []
        phases_enabled.append("Phase 1 (CV)")
        if self.vision_ai and self.vision_ai.enabled:
            phases_enabled.append("Phase 2 (Vision AI)")
        if self.rl_agent:
            phases_enabled.append("Phase 3 (RL)")
        
        logger.info(f"🚀 Hybrid Intelligence initialized | Enabled: {', '.join(phases_enabled)}")
    
    def analyze_and_decide(
        self,
        screenshot_path: str,
        ocr_data: Dict,
        ui_elements: List[Dict],
        game_state: Optional[CVGameState] = None
    ) -> Dict:
        """
        Main decision-making pipeline integrating all three phases
        
        Returns:
            Decision dict with action, coordinates, reasoning, confidence, source
        """
        self.stats['total_actions'] += 1
        
        # Build current state representation
        self.current_state = self._build_state(screenshot_path, ocr_data, ui_elements, game_state)
        
        # PHASE 1: Computer Vision (Always run - fast)
        cv_decision = self.cv_agent.analyze_and_decide(
            screenshot_path, ocr_data, ui_elements
        )
        cv_decision['source'] = 'cv'
        self.stats['cv_decisions'] += 1
        
        logger.info(f"🔍 Phase 1 (CV): {cv_decision.get('reasoning', '')} | Confidence: {cv_decision.get('confidence', 0):.2f}")
        
        # Collect available actions for RL
        available_actions = [cv_decision]
        
        # PHASE 2: Vision AI (Selective - when needed)
        use_vision_ai = self._should_use_vision_ai(cv_decision, game_state)
        
        vision_decision = None
        if use_vision_ai and self.vision_ai and self.vision_ai.enabled:
            if self.vision_ai_calls < self.max_vision_calls_per_session:
                try:
                    vision_result = self.vision_ai.analyze_game_screenshot(
                        screenshot_path=screenshot_path,
                        context={'ocr_text': ocr_data, 'ui_elements': ui_elements},
                        history=self.decision_history[-5:],
                        screen_dimensions=(self.width, self.height)
                    )
                    
                    if vision_result.get('action'):
                        vision_decision = {
                            'action': vision_result['action'],
                            'coordinates': tuple(vision_result.get('coordinates', (self.width//2, self.height//2))),
                            'reasoning': vision_result.get('reasoning', 'Vision AI suggestion'),
                            'confidence': vision_result.get('confidence', 0.7),
                            'source': 'vision_ai',
                            'screen_type': vision_result.get('screen_type'),
                            'objective': vision_result.get('objective')
                        }
                        available_actions.append(vision_decision)
                        self.stats['vision_ai_decisions'] += 1
                        self.vision_ai_calls += 1
                        
                        logger.info(f"🤖 Phase 2 (Vision AI): {vision_decision['reasoning'][:100]} | Confidence: {vision_decision['confidence']:.2f}")
                except Exception as e:
                    logger.error(f"Vision AI failed: {e}")
        
        # PHASE 3: Reinforcement Learning (Choose best action)
        final_decision = cv_decision  # Default fallback
        
        if self.rl_agent and len(available_actions) > 0:
            state_key = self.rl_agent.get_state_key(self.current_state)
            
            # RL chooses from available actions
            rl_choice = self.rl_agent.choose_action(
                state_key=state_key,
                available_actions=available_actions,
                explore=True  # Enable exploration
            )
            
            if rl_choice:
                final_decision = rl_choice
                if rl_choice.get('source') != 'cv':
                    self.stats['rl_decisions'] += 1
                    logger.info(f"🧠 Phase 3 (RL): Selected {rl_choice.get('source', 'unknown')} action")
        
        # Prefer Vision AI if confidence is significantly higher
        if vision_decision and vision_decision['confidence'] > cv_decision['confidence'] + 0.2:
            final_decision = vision_decision
            logger.info("⚡ Overriding with high-confidence Vision AI decision")
        
        # Store decision in history
        final_decision['phase_stats'] = self.stats.copy()
        self.decision_history.append(final_decision)
        
        # Keep history manageable
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-100:]
        
        return final_decision
    
    def update_after_action(self, action_result: Dict):
        """
        Update RL agent after action execution (learning)
        
        Args:
            action_result: Result of action execution with new state info
        """
        if not self.rl_agent or not self.previous_state or not self.current_state:
            self.previous_state = self.current_state
            return
        
        # Calculate reward
        reward = RewardCalculator.calculate_reward(
            prev_state=self.previous_state,
            new_state=self.current_state,
            action_result=action_result
        )
        
        # Get state keys
        prev_state_key = self.rl_agent.get_state_key(self.previous_state)
        current_state_key = self.rl_agent.get_state_key(self.current_state)
        
        # Get last action taken
        if self.decision_history:
            last_action = self.decision_history[-1]
            
            # Update Q-value
            done = self.current_state.get('screen_type') in ['completion', 'failure']
            self.rl_agent.update_q_value(
                state_key=prev_state_key,
                action=last_action,
                reward=reward,
                next_state_key=current_state_key,
                done=done
            )
            
            logger.debug(f"📊 RL updated: Reward={reward:.2f}")
        
        # Update previous state
        self.previous_state = self.current_state
    
    def end_session(self, session_result: Dict):
        """
        End session and update RL statistics
        
        Args:
            session_result: Final session results (completed levels, score, etc.)
        """
        if not self.rl_agent:
            return
        
        # Calculate final episode reward
        episode_reward = session_result.get('total_reward', 0)
        
        # End episode
        self.rl_agent.end_episode(episode_reward)
        
        # Get statistics
        rl_stats = self.rl_agent.get_statistics()
        
        logger.info(f"""
🎮 Session Complete | Hybrid Intelligence Stats:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Decision Sources:
   • Phase 1 (CV): {self.stats['cv_decisions']} decisions
   • Phase 2 (Vision AI): {self.stats['vision_ai_decisions']} decisions
   • Phase 3 (RL): {self.stats['rl_decisions']} optimizations
   • Total Actions: {self.stats['total_actions']}

🧠 RL Learning:
   • Episodes: {rl_stats['total_episodes']}
   • Q-Table Size: {rl_stats['q_table_size']} states
   • Experiences: {rl_stats['experiences']}
   • Avg Recent Reward: {rl_stats['avg_recent_reward']:.2f}
   • Exploration Rate: {rl_stats['epsilon']:.3f}

🤖 Vision AI Usage:
   • API Calls: {self.vision_ai_calls}
   • Limit: {self.max_vision_calls_per_session}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
    
    def save_rl_model(self, filepath: str = "/app/data/rl_model.pkl"):
        """Save RL model for future sessions"""
        if self.rl_agent:
            self.rl_agent.save_model(filepath)
    
    def _build_state(
        self,
        screenshot_path: str,
        ocr_data: Dict,
        ui_elements: List[Dict],
        game_state: Optional[CVGameState]
    ) -> Dict:
        """Build comprehensive state representation"""
        
        # Calculate screen hash for change detection
        try:
            with open(screenshot_path, 'rb') as f:
                screen_hash = hashlib.md5(f.read()).hexdigest()
        except:
            screen_hash = "unknown"
        
        # Extract OCR text
        ocr_text = []
        if isinstance(ocr_data, dict):
            ocr_text = ocr_data.get('buttons', [])
        elif isinstance(ocr_data, list):
            ocr_text = ocr_data
        
        # Determine screen type from game state
        screen_type = 'unknown'
        stuck_count = 0
        if game_state:
            screen_type = game_state.current_screen_type
            stuck_count = game_state.stuck_counter
        
        return {
            'screen_hash': screen_hash,
            'screen_type': screen_type,
            'ocr_text': ocr_text,
            'ui_elements': ui_elements,
            'stuck_count': stuck_count,
            'timestamp': self.stats['total_actions']
        }
    
    def _should_use_vision_ai(self, cv_decision: Dict, game_state: Optional[CVGameState]) -> bool:
        """Determine if Vision AI should be invoked (PHASE 2 optimized)"""
        
        if not self.vision_ai or not self.vision_ai.enabled:
            return False
        
        # Don't exceed call limit
        if self.vision_ai_calls >= self.max_vision_calls_per_session:
            return False
        
        # PHASE 2: Use frequency-based calls from environment
        import os
        vision_ai_frequency = int(os.getenv('VISION_AI_FREQUENCY', '7'))
        
        # Use Vision AI if:
        # 1. CV confidence is low (immediate help needed)
        if cv_decision.get('confidence', 1.0) < 0.5:
            logger.debug("🔍 Low CV confidence -> Using Vision AI")
            return True
        
        # 2. Agent is stuck (strategic help needed)
        if game_state and game_state.stuck_counter >= 5:
            logger.debug("🔍 Agent stuck (5+ actions) -> Using Vision AI")
            return True
        
        # 3. Periodic strategic validation (configurable frequency)
        if self.stats['total_actions'] % vision_ai_frequency == 0:
            logger.debug(f"🔍 Periodic check (every {vision_ai_frequency} actions) -> Using Vision AI")
            return True
        
        return False
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        stats = self.stats.copy()
        
        if self.rl_agent:
            stats['rl'] = self.rl_agent.get_statistics()
        
        stats['vision_ai_calls'] = self.vision_ai_calls
        stats['vision_ai_enabled'] = self.vision_ai.enabled if self.vision_ai else False
        
        return stats
