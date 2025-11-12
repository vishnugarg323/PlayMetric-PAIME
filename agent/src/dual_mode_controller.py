"""
Dual-Mode Learning Controller
Handles both User Observation Mode and AI Auto-Play Mode with 16 FPS capture
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
import httpx

from .high_performance_capture import HighPerformanceCapture, ScreenshotBatch
from .learning_recorder_v2 import ObservationRecorder, DecisionRecorder

logger = logging.getLogger(__name__)


class DualModeController:
    """
    Production-ready dual-mode learning system
    
    Mode 1 - USER OBSERVATION:
    - Captures at 16 FPS
    - Detects user taps/swipes
    - Analyzes 16 frames per second
    - Makes collective decision each second about what user did
    - Stores meaningful observations in database
    
    Mode 2 - AI AUTO-PLAY:
    - Captures at 16 FPS
    - Analyzes all 16 frames
    - Makes collective AI decision each second
    - Uses learned user demonstrations
    - Stores AI decisions and outcomes
    """
    
    def __init__(
        self,
        db_manager,
        emulator_manager_url: str,
        observation_service_url: str,
        http_client: httpx.AsyncClient
    ):
        self.db_manager = db_manager
        self.emulator_manager_url = emulator_manager_url
        self.observation_service_url = observation_service_url
        self.http_client = http_client
        
        # Initialize recorders
        self.observation_recorder = ObservationRecorder(db_manager)
        self.decision_recorder = DecisionRecorder(db_manager)
        
        # High-performance capture (16 FPS)
        self.hp_capture = HighPerformanceCapture(
            device_manager_url=emulator_manager_url,
            fps=16,
            max_workers=8
        )
        
        # Mode tracking
        self.current_mode: Optional[str] = None  # 'user_observation' or 'ai_autoplay'
        self.session_id: Optional[str] = None
        self.game_id: Optional[str] = None
        self.agent = None
        self.action_space = None
        
        # User tap buffer (from observation service)
        self.pending_user_taps: List[Dict] = []
        
        # AI decision buffer
        self.last_ai_decision_time = 0
        self.ai_decision_interval = 1.0  # Make decision every second
        
        logger.info("✅ Dual-Mode Controller initialized (16 FPS)")
    
    async def start_user_observation_mode(
        self,
        session_id: str,
        game_id: str
    ):
        """
        Start User Observation Mode
        - User plays the game
        - AI watches at 16 FPS
        - AI learns from user actions
        """
        logger.info(f"👤 Starting USER OBSERVATION MODE for session {session_id}")
        
        self.current_mode = 'user_observation'
        self.session_id = session_id
        self.game_id = game_id
        
        # Start user input monitoring
        try:
            await self.http_client.post(
                f"{self.observation_service_url}/user-input/start",
                json={"session_id": session_id, "mode": "learning"}
            )
            logger.info("✅ User input monitoring started")
        except Exception as e:
            logger.error(f"Failed to start user monitoring: {e}")
        
        # Start 16 FPS capture with user observation callback
        await self.hp_capture.start_capture(
            on_batch_complete=self._on_user_observation_batch,
            mode="observation"
        )
        
        logger.info("🎥 16 FPS capture started for user observation")
    
    async def start_ai_autoplay_mode(
        self,
        session_id: str,
        game_id: str,
        agent,
        action_space
    ):
        """
        Start AI Auto-Play Mode
        - AI plays the game
        - Captures at 16 FPS
        - Makes decisions every second based on 16 frames
        - Uses learned user demonstrations
        """
        logger.info(f"🤖 Starting AI AUTO-PLAY MODE for session {session_id}")
        
        self.current_mode = 'ai_autoplay'
        self.session_id = session_id
        self.game_id = game_id
        self.agent = agent
        self.action_space = action_space
        
        # Stop user monitoring if running
        try:
            await self.http_client.post(f"{self.observation_service_url}/user-input/stop")
        except:
            pass
        
        # Start 16 FPS capture with AI decision callback
        await self.hp_capture.start_capture(
            on_batch_complete=self._on_ai_decision_batch,
            mode="decision"
        )
        
        logger.info("🎥 16 FPS capture started for AI auto-play")
    
    async def stop(self):
        """Stop current mode"""
        logger.info(f"⏹️  Stopping {self.current_mode} mode")
        
        # Stop capture
        await self.hp_capture.stop_capture()
        
        # Stop user monitoring if running
        if self.current_mode == 'user_observation':
            try:
                await self.http_client.post(f"{self.observation_service_url}/user-input/stop")
            except:
                pass
        
        self.current_mode = None
    
    async def _on_user_observation_batch(self, batch: ScreenshotBatch):
        """
        Process 1 second batch of screenshots in USER OBSERVATION mode
        
        This is called every second with 16 screenshots.
        We need to:
        1. Get user taps that happened in this second
        2. Correlate taps with screen state
        3. Analyze what user did and why
        4. Store meaningful observation
        """
        try:
            # Get user taps from observation service
            response = await self.http_client.get(
                f"{self.observation_service_url}/user-input/taps?limit=20"
            )
            if response.status_code == 200:
                tap_data = response.json()
                recent_taps = tap_data.get('taps', [])
                
                # Filter taps from this batch timeframe
                batch_taps = [
                    tap for tap in recent_taps
                    if tap.get('timestamp') and self._is_in_batch_timeframe(tap['timestamp'], batch.timestamp)
                ]
                
                if batch_taps:
                    # User performed actions - analyze them
                    await self._analyze_user_actions(batch, batch_taps)
                else:
                    logger.debug("No user actions detected in this batch")
            
        except Exception as e:
            logger.error(f"Error processing user observation batch: {e}")
    
    async def _analyze_user_actions(self, batch: ScreenshotBatch, taps: List[Dict]):
        """
        Analyze user actions and store observations
        """
        collective_analysis = batch.get_collective_analysis()
        
        for tap in taps:
            try:
                # Build user action
                user_action = {
                    "type": "tap",
                    "x": tap.get('x'),
                    "y": tap.get('y'),
                    "timestamp": tap.get('timestamp')
                }
                
                # Get screenshot closest to tap time
                screenshot_path = batch.screenshots[0].get('path') if batch.screenshots else None
                
                # Build screen analysis
                screen_analysis = {
                    "ocr_text": collective_analysis.get('combined_ocr_text', ''),
                    "ui_elements": collective_analysis.get('avg_ui_elements', 0),
                    "screen_stability": collective_analysis.get('screen_stability', 0),
                    "total_frames": collective_analysis.get('total_frames', 0)
                }
                
                # Record observation
                await self.observation_recorder.record_user_observation(
                    session_id=self.session_id,
                    game_id=self.game_id,
                    user_action=user_action,
                    screenshot_path=screenshot_path,
                    screen_analysis=screen_analysis
                )
                
                logger.info(f"📝 Recorded user tap at ({tap.get('x')}, {tap.get('y')})")
                
            except Exception as e:
                logger.error(f"Failed to record user observation: {e}")
    
    async def _on_ai_decision_batch(self, batch: ScreenshotBatch):
        """
        Process 1 second batch for AI AUTO-PLAY mode
        
        Every second:
        1. Analyze all 16 screenshots collectively
        2. Query learned user demonstrations
        3. Make AI decision
        4. Execute action
        5. Record decision and outcome
        """
        try:
            # Check if it's time to make a decision (every second)
            current_time = time.time()
            if current_time - self.last_ai_decision_time < self.ai_decision_interval:
                return
            
            self.last_ai_decision_time = current_time
            
            # Get collective analysis
            collective = batch.get_collective_analysis()
            
            # Make AI decision
            await self._make_ai_decision(batch, collective)
            
        except Exception as e:
            logger.error(f"Error in AI decision batch: {e}")
    
    async def _make_ai_decision(self, batch: ScreenshotBatch, collective_analysis: Dict):
        """
        Make and execute AI decision
        """
        start_time = time.time()
        
        try:
            # Get screenshot path
            screenshot_path = batch.screenshots[0].get('path') if batch.screenshots else None
            
            # Build screen analysis
            screen_analysis = {
                "combined_ocr_text": collective_analysis.get('combined_ocr_text', ''),
                "avg_ui_elements": collective_analysis.get('avg_ui_elements', 0),
                "screen_stability": collective_analysis.get('screen_stability', 0),
                "frames_analyzed": len(batch.screenshots)
            }
            
            # Check for learned user demonstrations
            user_demos = await self._get_similar_user_demonstrations(screen_analysis)
            
            # Build reasoning
            reasoning = self._build_ai_reasoning(screen_analysis, user_demos)
            
            # Choose action
            if user_demos and len(user_demos) > 0:
                # Use user demonstration
                demo = user_demos[0]
                action_dict = demo.get('user_action', {})
                action_source = 'user_demonstration'
                confidence = 0.8
            else:
                # Use agent's own decision
                if self.agent and self.action_space:
                    state = self._build_state_vector(screen_analysis)
                    action = self.agent.choose_action(state)
                    action_dict = self.action_space.get_action_dict(action)
                    action_source = 'exploration'
                    confidence = 0.5
                else:
                    # Fallback: random tap
                    action_dict = {"type": "tap", "x": 500, "y": 500}
                    action_source = 'fallback'
                    confidence = 0.3
            
            decision_time_ms = int((time.time() - start_time) * 1000)
            
            # Record decision
            decision_id = await self.decision_recorder.record_ai_decision(
                session_id=self.session_id,
                game_id=self.game_id,
                agent_type=self.agent.__class__.__name__ if self.agent else 'None',
                screenshot_path=screenshot_path,
                screen_analysis=screen_analysis,
                reasoning=reasoning,
                chosen_action=action_dict,
                action_source=action_source,
                available_actions=[],
                decision_factors={"user_demos_available": len(user_demos)},
                confidence_score=confidence
            )
            
            # Execute action
            exec_start = time.time()
            success, error = await self._execute_action(action_dict)
            exec_time_ms = int((time.time() - exec_start) * 1000)
            
            # Calculate reward
            reward = 0.5 if success else -0.5
            
            # Update decision with outcome
            await self.decision_recorder.update_decision_outcome(
                decision_id=decision_id,
                outcome={"action_executed": success, "error": error},
                reward_signal=reward,
                was_successful=success,
                execution_time_ms=exec_time_ms,
                execution_error=error
            )
            
            logger.info(f"🤖 AI decision: {reasoning[:80]}... (source={action_source}, success={success})")
            
        except Exception as e:
            logger.error(f"Failed to make AI decision: {e}")
    
    async def _get_similar_user_demonstrations(self, screen_analysis: Dict) -> List[Dict]:
        """Query database for similar user demonstrations"""
        try:
            # Get recent user observations for this game
            observations = await self.observation_recorder.get_observations(
                self.session_id,
                limit=10
            )
            return observations
        except Exception as e:
            logger.debug(f"No user demonstrations found: {e}")
            return []
    
    def _build_ai_reasoning(self, screen_analysis: Dict, user_demos: List[Dict]) -> str:
        """Build human-readable AI reasoning"""
        if user_demos:
            return f"Found {len(user_demos)} similar user demonstrations. Mimicking user's strategy. Screen has {screen_analysis.get('avg_ui_elements', 0):.0f} UI elements."
        else:
            return f"No user demonstrations available. Exploring based on vision analysis. Detected {screen_analysis.get('avg_ui_elements', 0):.0f} UI elements."
    
    def _build_state_vector(self, screen_analysis: Dict):
        """Build state vector for agent"""
        # Simple state representation
        import numpy as np
        return np.array([
            screen_analysis.get('avg_ui_elements', 0) / 100.0,
            screen_analysis.get('screen_stability', 0),
            len(screen_analysis.get('combined_ocr_text', '')) / 1000.0
        ])
    
    async def _execute_action(self, action_dict: Dict) -> tuple[bool, Optional[str]]:
        """Execute action via emulator manager"""
        try:
            action_type = action_dict.get('type', 'tap')
            
            if action_type == 'tap':
                response = await self.http_client.post(
                    f"{self.emulator_manager_url}/input/tap",
                    json={"x": action_dict.get('x'), "y": action_dict.get('y')}
                )
                return response.status_code == 200, None
            elif 'swipe' in action_type:
                response = await self.http_client.post(
                    f"{self.emulator_manager_url}/input/swipe",
                    json=action_dict
                )
                return response.status_code == 200, None
            
            return False, "Unknown action type"
            
        except Exception as e:
            return False, str(e)
    
    def _is_in_batch_timeframe(self, tap_timestamp: str, batch_timestamp: float) -> bool:
        """Check if tap is in batch timeframe"""
        try:
            from datetime import datetime
            tap_time = datetime.fromisoformat(tap_timestamp).timestamp()
            return abs(tap_time - batch_timestamp) < 1.0
        except:
            return True  # Include if can't parse
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        capture_stats = self.hp_capture.get_stats()
        return {
            "mode": self.current_mode,
            "session_id": self.session_id,
            **capture_stats
        }
