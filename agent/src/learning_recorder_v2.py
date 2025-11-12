"""
Enhanced Learning Recorder v2 - Production-ready learning system
Captures meaningful observations from both user gameplay and AI auto-play
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import time

logger = logging.getLogger(__name__)


class ObservationRecorder:
    """Records and analyzes user observations for learning"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.session_sequences = {}  # Track sequence numbers per session
        logger.info("✅ Observation Recorder V2 initialized")
    
    async def record_user_observation(
        self,
        session_id: str,
        game_id: str,
        user_action: Dict[str, Any],
        screenshot_path: Optional[str] = None,
        screen_analysis: Optional[Dict[str, Any]] = None,
        ai_interpretation: Optional[str] = None
    ) -> str:
        """
        Record a meaningful user observation with AI analysis
        
        This is called when:
        - User taps/swipes on screen
        - AI analyzes what the user did and why
        - Stores the learning for future AI use
        
        Returns observation ID
        """
        start_time = time.time()
        
        try:
            # Get sequence number
            seq_num = self._get_next_sequence(session_id)
            
            # Analyze the user action
            analysis = await self._analyze_user_action(
                user_action, screen_analysis
            )
            
            # Extract learned pattern
            pattern = self._extract_pattern(user_action, screen_analysis, analysis)
            
            # Calculate confidence
            confidence = self._calculate_confidence(screen_analysis, analysis)
            
            # Build interpretation
            if not ai_interpretation:
                ai_interpretation = self._build_interpretation(user_action, analysis)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Store in database
            observation_id = str(uuid.uuid4())
            await self.db_manager.execute_write(
                """
                INSERT INTO user_observations (
                    id, session_id, game_id, sequence_number, timestamp,
                    screenshot_path, screen_analysis, user_action,
                    ai_interpretation, detected_ui_element, inferred_intent,
                    outcome, learned_pattern, confidence_score, processing_time_ms
                ) VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                observation_id, session_id, game_id, seq_num,
                screenshot_path,
                json.dumps(screen_analysis or {}),
                json.dumps(user_action),
                ai_interpretation,
                analysis.get('ui_element'),
                analysis.get('intent'),
                json.dumps(analysis.get('outcome', {})),
                json.dumps(pattern),
                confidence,
                processing_time
            )
            
            logger.info(f"📝 User observation #{seq_num}: {ai_interpretation} (confidence={confidence:.2f})")
            return observation_id
            
        except Exception as e:
            logger.error(f"❌ Failed to record user observation: {e}")
            raise
    
    async def get_observations(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get user observations for display"""
        try:
            rows = await self.db_manager.execute(
                """
                SELECT 
                    id, timestamp, sequence_number,
                    screenshot_path, screen_analysis, user_action,
                    ai_interpretation, detected_ui_element, inferred_intent,
                    outcome, learned_pattern, confidence_score
                FROM user_observations
                WHERE session_id = $1
                ORDER BY sequence_number DESC
                LIMIT $2
                """,
                session_id, limit
            )
            
            observations = []
            for row in rows:
                obs = dict(row)
                # Parse JSON fields
                obs['screen_analysis'] = json.loads(obs.get('screen_analysis') or '{}')
                obs['user_action'] = json.loads(obs.get('user_action') or '{}')
                obs['outcome'] = json.loads(obs.get('outcome') or '{}')
                obs['learned_pattern'] = json.loads(obs.get('learned_pattern') or '{}')
                observations.append(obs)
            
            return observations
            
        except Exception as e:
            logger.error(f"Failed to get observations: {e}")
            return []
    
    async def _analyze_user_action(
        self,
        user_action: Dict,
        screen_analysis: Optional[Dict]
    ) -> Dict[str, Any]:
        """Analyze what the user action means"""
        analysis = {}
        
        # Detect what UI element was tapped
        if user_action.get('type') == 'tap' and screen_analysis:
            x, y = user_action.get('x'), user_action.get('y')
            ui_elem = self._detect_tapped_element(x, y, screen_analysis)
            if ui_elem:
                analysis['ui_element'] = ui_elem
        
        # Infer intent
        analysis['intent'] = self._infer_intent(user_action, screen_analysis)
        
        # Predict outcome
        analysis['outcome'] = {
            'expected_screen_change': True if user_action.get('type') == 'tap' else False
        }
        
        return analysis
    
    def _detect_tapped_element(self, x: int, y: int, screen_analysis: Dict) -> Optional[str]:
        """Detect which UI element was tapped based on OCR/vision"""
        # Simple heuristic: check if tap is near detected text
        ocr_text = screen_analysis.get('ocr_text', '')
        if ocr_text:
            # Return first significant text as likely button/element
            words = ocr_text.split()
            if words:
                return words[0] if len(words[0]) > 2 else None
        return None
    
    def _infer_intent(self, user_action: Dict, screen_analysis: Optional[Dict]) -> str:
        """Infer what the user was trying to accomplish"""
        action_type = user_action.get('type', 'unknown')
        
        if action_type == 'tap':
            if screen_analysis and 'button' in screen_analysis.get('ocr_text', '').lower():
                return 'press_button'
            return 'interact_with_ui'
        elif action_type == 'swipe_up':
            return 'scroll_up'
        elif action_type == 'swipe_down':
            return 'scroll_down'
        elif action_type == 'back':
            return 'navigate_back'
        
        return 'explore'
    
    def _extract_pattern(
        self,
        user_action: Dict,
        screen_analysis: Optional[Dict],
        analysis: Dict
    ) -> Dict:
        """Extract a reusable pattern from this observation"""
        return {
            "trigger_screen_state": screen_analysis.get('screen_type', 'unknown') if screen_analysis else None,
            "action": {
                "type": user_action.get('type'),
                "coordinates": [user_action.get('x'), user_action.get('y')] if user_action.get('x') else None
            },
            "intent": analysis.get('intent'),
            "context": "user_demonstration"
        }
    
    def _calculate_confidence(self, screen_analysis: Optional[Dict], analysis: Dict) -> float:
        """Calculate confidence in this observation"""
        confidence = 0.6  # Base
        
        if screen_analysis:
            if screen_analysis.get('ocr_text'):
                confidence += 0.15
            if screen_analysis.get('ui_elements', 0) > 0:
                confidence += 0.1
        
        if analysis.get('ui_element'):
            confidence += 0.1
        
        if analysis.get('intent') != 'explore':
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _build_interpretation(self, user_action: Dict, analysis: Dict) -> str:
        """Build human-readable interpretation"""
        action_type = user_action.get('type', 'unknown')
        intent = analysis.get('intent', 'unknown')
        ui_elem = analysis.get('ui_element')
        
        if action_type == 'tap':
            x, y = user_action.get('x', 0), user_action.get('y', 0)
            if ui_elem:
                return f"User tapped '{ui_elem}' button at ({x}, {y})"
            else:
                return f"User tapped at position ({x}, {y}) to {intent.replace('_', ' ')}"
        elif 'swipe' in action_type:
            return f"User swiped {action_type.split('_')[1]} to {intent.replace('_', ' ')}"
        elif action_type == 'back':
            return "User pressed back button to navigate back"
        
        return f"User performed {action_type} action"
    
    def _get_next_sequence(self, session_id: str) -> int:
        """Get next sequence number for session"""
        if session_id not in self.session_sequences:
            self.session_sequences[session_id] = 0
        self.session_sequences[session_id] += 1
        return self.session_sequences[session_id]


class DecisionRecorder:
    """Records AI decision-making process for auto-play mode"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.session_sequences = {}
        logger.info("✅ Decision Recorder V2 initialized")
    
    async def record_ai_decision(
        self,
        session_id: str,
        game_id: str,
        agent_type: str,
        screenshot_path: Optional[str],
        screen_analysis: Dict,
        reasoning: str,
        chosen_action: Dict,
        action_source: str,  # 'user_demonstration' | 'learned_experience' | 'exploration' | 'vision_analysis'
        available_actions: Optional[List[Dict]] = None,
        decision_factors: Optional[Dict] = None,
        confidence_score: float = 0.5
    ) -> str:
        """
        Record an AI decision before execution
        
        This captures:
        - What AI saw (screen state)
        - What AI thought (reasoning)
        - What AI decided to do
        - Why AI made this choice
        
        Returns decision ID (use to update with outcome later)
        """
        start_time = time.time()
        
        try:
            seq_num = self._get_next_sequence(session_id)
            decision_time_ms = int((time.time() - start_time) * 1000)
            
            decision_id = str(uuid.uuid4())
            await self.db_manager.execute_write(
                """
                INSERT INTO ai_decisions (
                    id, session_id, game_id, sequence_number, timestamp,
                    agent_type, screenshot_path, screen_analysis,
                    available_actions, reasoning, decision_factors,
                    chosen_action, action_source, confidence_score,
                    decision_time_ms
                ) VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                decision_id, session_id, game_id, seq_num,
                agent_type, screenshot_path, json.dumps(screen_analysis),
                json.dumps(available_actions or []), reasoning, json.dumps(decision_factors or {}),
                json.dumps(chosen_action), action_source, confidence_score,
                decision_time_ms
            )
            
            logger.info(f"🤖 AI decision #{seq_num}: {reasoning[:100]}... (source={action_source})")
            return decision_id
            
        except Exception as e:
            logger.error(f"❌ Failed to record AI decision: {e}")
            raise
    
    async def update_decision_outcome(
        self,
        decision_id: str,
        outcome: Dict,
        reward_signal: float,
        was_successful: bool,
        execution_time_ms: int,
        execution_error: Optional[str] = None
    ):
        """Update decision with execution outcome"""
        try:
            await self.db_manager.execute_write(
                """
                UPDATE ai_decisions SET
                    action_executed = $1,
                    execution_error = $2,
                    execution_time_ms = $3,
                    outcome = $4,
                    reward_signal = $5,
                    was_successful = $6,
                    learned_from_outcome = true
                WHERE id = $7
                """,
                execution_error is None,
                execution_error,
                execution_time_ms,
                json.dumps(outcome),
                reward_signal,
                was_successful,
                decision_id
            )
            
            logger.info(f"✅ Updated decision {decision_id[:8]}... outcome (success={was_successful}, reward={reward_signal})")
            
        except Exception as e:
            logger.error(f"Failed to update decision outcome: {e}")
    
    async def get_decisions(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get AI decisions for display"""
        try:
            rows = await self.db_manager.execute(
                """
                SELECT 
                    id, timestamp, sequence_number, agent_type,
                    screenshot_path, screen_analysis, reasoning,
                    chosen_action, action_source, confidence_score,
                    outcome, reward_signal, was_successful,
                    decision_time_ms, execution_time_ms
                FROM ai_decisions
                WHERE session_id = $1
                ORDER BY sequence_number DESC
                LIMIT $2
                """,
                session_id, limit
            )
            
            decisions = []
            for row in rows:
                dec = dict(row)
                # Parse JSON fields
                dec['screen_analysis'] = json.loads(dec.get('screen_analysis') or '{}')
                dec['chosen_action'] = json.loads(dec.get('chosen_action') or '{}')
                dec['outcome'] = json.loads(dec.get('outcome') or '{}')
                decisions.append(dec)
            
            return decisions
            
        except Exception as e:
            logger.error(f"Failed to get decisions: {e}")
            return []
    
    def _get_next_sequence(self, session_id: str) -> int:
        if session_id not in self.session_sequences:
            self.session_sequences[session_id] = 0
        self.session_sequences[session_id] += 1
        return self.session_sequences[session_id]
