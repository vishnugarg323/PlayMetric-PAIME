"""
Hybrid AI Decision Engine - Combines learned patterns with real-time AI analysis

This engine implements the "teach & play" vision:
1. Query game_knowledge for learned patterns (fast, high confidence)
2. Run parallel AI analysis (OCR + Vision AI) for real-time understanding
3. Blend decisions using confidence scores and context
4. Fall back to exploration when no patterns match
5. Provide detailed reasoning for every decision
"""
import logging
import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class HybridDecisionEngine:
    """
    Hybrid decision engine combining learned knowledge with real-time AI
    
    Decision Priority (Option B - Flexible Blending):
    - Query learned patterns based on current scene
    - Run AI analysis in parallel
    - Compare confidence scores
    - Choose action with highest confidence OR blend both
    - Track success for continuous learning
    """
    
    def __init__(
        self,
        game_id: str,
        db_manager,
        vision_service_url: str = "http://vision:8006",
        observation_service_url: str = "http://observation:8001",
        learning_service_url: str = "http://learning:8007"
    ):
        self.game_id = game_id
        self.db_manager = db_manager
        self.vision_url = vision_service_url
        self.observation_url = observation_service_url
        self.learning_url = learning_service_url
        
        # Performance tracking
        self.knowledge_hits = 0
        self.knowledge_misses = 0
        self.ai_fallbacks = 0
        
    async def capture_screenshot(self) -> str:
        """Capture current game screen"""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.observation_url}/capture") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["screenshot_path"]
                raise Exception(f"Screenshot capture failed: {resp.status}")
    
    async def analyze_with_ai(
        self,
        screenshot_path: str,
        use_gemini: bool = True
    ) -> Dict[str, Any]:
        """
        Run AI analysis on screenshot (OCR + Vision AI in parallel)
        
        Returns:
            {
                'ocr': {...},
                'vision': {...},
                'scene_type': str,
                'detected_text': str,
                'ui_elements': [...],
                'analysis_time': float
            }
        """
        start_time = time.time()
        analysis = {
            'ocr': {},
            'vision': {},
            'scene_type': 'unknown',
            'detected_text': '',
            'ui_elements': [],
            'analysis_time': 0
        }
        
        async with aiohttp.ClientSession() as session:
            # Run OCR and Vision in parallel
            async def run_ocr():
                try:
                    async with session.post(
                        f"{self.vision_url}/analyze/ocr",
                        json={"screenshot_path": screenshot_path},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            ocr_result = await resp.json()
                            analysis['ocr'] = ocr_result
                            analysis['detected_text'] = ocr_result.get('full_text', '')
                            analysis['ui_elements'] = ocr_result.get('buttons', [])
                except Exception as e:
                    logger.warning(f"OCR failed: {e}")
            
            async def run_vision():
                try:
                    endpoint = "/analyze/gemini" if use_gemini else "/analyze"
                    async with session.post(
                        f"{self.vision_url}{endpoint}",
                        json={"screenshot_path": screenshot_path},
                        timeout=aiohttp.ClientTimeout(total=30 if use_gemini else 120)
                    ) as resp:
                        if resp.status == 200:
                            vision_result = await resp.json()
                            analysis['vision'] = vision_result
                            analysis['scene_type'] = vision_result.get('scene_type', 'unknown')
                except Exception as e:
                    logger.warning(f"Vision AI failed: {e}")
            
            await asyncio.gather(run_ocr(), run_vision(), return_exceptions=True)
        
        # Fallback scene classification from OCR if vision didn't provide it
        if analysis['scene_type'] == 'unknown':
            analysis['scene_type'] = self._classify_scene_from_text(
                analysis['detected_text']
            )
        
        analysis['analysis_time'] = time.time() - start_time
        return analysis
    
    def _classify_scene_from_text(self, text: str) -> str:
        """Classify scene based on detected text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['play', 'start', 'settings', 'menu']):
            return 'menu'
        elif any(word in text_lower for word in ['victory', 'win', 'complete', 'you won']):
            return 'victory'
        elif any(word in text_lower for word in ['defeat', 'game over', 'failed', 'try again']):
            return 'defeat'
        elif any(word in text_lower for word in ['loading', 'please wait']):
            return 'loading'
        elif any(word in text_lower for word in ['score', 'health', 'hp', 'coins', 'level']):
            return 'gameplay'
        else:
            return 'unknown'
    
    async def query_learned_patterns(
        self,
        current_scene: str,
        detected_text: str,
        ui_elements: List[Dict],
        scene_description: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Query learned patterns using comprehensive knowledge query engine
        
        Returns:
            List of matching patterns with confidence scores
        """
        try:
            from src.knowledge_query import KnowledgeQueryEngine
            
            # Use comprehensive query engine
            query_engine = KnowledgeQueryEngine(self.db_manager)
            
            matches = await query_engine.query_learned_actions(
                game_id=self.game_id,
                current_scene=current_scene,
                ui_elements=ui_elements,
                detected_text=detected_text,
                scene_description=scene_description,
                min_confidence=0.5,
                limit=10
            )
            
            if matches:
                self.knowledge_hits += 1
                logger.info(f"✅ Knowledge: Found {len(matches)} matching learned actions")
                
                # Convert to pattern format expected by decision blending
                patterns = []
                for match in matches:
                    patterns.append({
                        'id': match['id'],
                        'pattern_name': f"Learned_{match['action_type']}_{match['id'][:8]}",
                        'action_template': match['action'],
                        'confidence': match['match_confidence'],
                        'success_rate': 0.8,  # Assume high success for learned actions
                        'metadata': {
                            'ui_elements': match['ui_elements'],
                            'game_state': match['game_state'],
                            'detected_text': match['detected_text'],
                            'ui_similarity': match.get('ui_similarity', 0)
                        }
                    })
                
                return patterns
            else:
                self.knowledge_misses += 1
                logger.info(f"❌ Knowledge: No patterns match current scene")
                return []
                
        except Exception as e:
            logger.error(f"Failed to query learned patterns: {e}", exc_info=True)
            return []
    
    async def decide(
        self,
        screenshot_path: str,
        use_gemini: bool = True
    ) -> Dict[str, Any]:
        """
        Make hybrid decision combining learned patterns and AI analysis
        
        Returns:
            {
                'action': 'tap' | 'swipe' | 'wait',
                'params': {...},
                'reasoning': {...},
                'confidence': float,
                'source': 'learned' | 'ai' | 'blended' | 'exploration',
                'pattern_id': str (if from learned pattern)
            }
        """
        decision_start = time.time()
        
        # Step 1: Run AI analysis
        logger.info("🔍 Step 1: AI Analysis...")
        ai_analysis = await self.analyze_with_ai(screenshot_path, use_gemini)
        
        logger.info(f"   Scene: {ai_analysis['scene_type']}")
        logger.info(f"   Text: {ai_analysis['detected_text'][:100]}...")
        logger.info(f"   UI Elements: {len(ai_analysis['ui_elements'])} found")
        
        # Step 2: Query learned patterns with comprehensive data
        logger.info("🧠 Step 2: Querying learned patterns...")
        learned_patterns = await self.query_learned_patterns(
            current_scene=ai_analysis['scene_type'],
            detected_text=ai_analysis['detected_text'],
            ui_elements=ai_analysis['ui_elements'],
            scene_description=ai_analysis.get('vision', {}).get('description', '')
        )
        
        # Step 3: Generate AI-based decision options
        logger.info("🤖 Step 3: Generating AI decision options...")
        ai_options = self._generate_ai_options(ai_analysis)
        
        # Step 4: Blend decisions
        logger.info("⚖️  Step 4: Blending decisions...")
        final_decision = self._blend_decisions(
            learned_patterns=learned_patterns,
            ai_options=ai_options,
            ai_analysis=ai_analysis
        )
        
        # Add metadata
        final_decision['decision_time'] = time.time() - decision_start
        final_decision['timestamp'] = datetime.now().isoformat()
        final_decision['screenshot_path'] = screenshot_path
        final_decision['ai_analysis'] = ai_analysis
        
        # Log decision
        logger.info(f"\n🎯 FINAL DECISION:")
        logger.info(f"   Source: {final_decision['source']}")
        logger.info(f"   Action: {final_decision['action']}")
        logger.info(f"   Confidence: {final_decision['confidence']:.2%}")
        logger.info(f"   Reason: {final_decision['reasoning']['summary']}")
        
        return final_decision
    
    def _generate_ai_options(self, ai_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate action options based on AI analysis"""
        options = []
        scene_type = ai_analysis['scene_type']
        ui_elements = ai_analysis['ui_elements']
        
        # Scene-specific rules
        if scene_type == 'menu':
            # Look for play/start buttons
            for elem in ui_elements:
                text = elem.get('text', '').lower()
                if any(word in text for word in ['play', 'start', 'continue']):
                    options.append({
                        'action': 'tap',
                        'params': {'x': elem['x'], 'y': elem['y']},
                        'confidence': 0.8,
                        'reason': f"Tap '{elem['text']}' to start game"
                    })
        
        elif scene_type == 'victory' or scene_type == 'defeat':
            # Tap to continue/retry
            for elem in ui_elements:
                text = elem.get('text', '').lower()
                if any(word in text for word in ['continue', 'retry', 'again', 'next']):
                    options.append({
                        'action': 'tap',
                        'params': {'x': elem['x'], 'y': elem['y']},
                        'confidence': 0.7,
                        'reason': f"Tap '{elem['text']}' to continue"
                    })
            
            # Fallback: tap center
            if not options:
                options.append({
                    'action': 'tap',
                    'params': {'x': 540, 'y': 1200},
                    'confidence': 0.5,
                    'reason': 'Tap center to dismiss result screen'
                })
        
        elif scene_type == 'loading':
            options.append({
                'action': 'wait',
                'params': {'duration': 2.0},
                'confidence': 0.9,
                'reason': 'Wait for loading'
            })
        
        elif scene_type == 'gameplay':
            # Explore by tapping detected UI elements
            for elem in ui_elements[:3]:  # Top 3 elements
                options.append({
                    'action': 'tap',
                    'params': {'x': elem['x'], 'y': elem['y']},
                    'confidence': 0.4,
                    'reason': f"Explore by tapping {elem.get('text', 'element')}"
                })
        
        # Always have a fallback option
        if not options:
            options.append({
                'action': 'wait',
                'params': {'duration': 1.0},
                'confidence': 0.3,
                'reason': 'Observe to gather information'
            })
        
        return options
    
    def _blend_decisions(
        self,
        learned_patterns: List[Dict],
        ai_options: List[Dict],
        ai_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Blend learned patterns and AI options to make final decision
        
        Strategy:
        - If learned pattern has high confidence (>0.7), use it
        - If AI option has higher confidence, use AI
        - Otherwise blend or choose highest confidence
        """
        all_options = []
        
        # Add learned patterns as options
        for pattern in learned_patterns:
            action_template = pattern['action_template']
            all_options.append({
                'action': action_template['type'],
                'params': {k: v for k, v in action_template.items() if k != 'type'},
                'confidence': pattern['confidence'],
                'reason': f"Learned: {pattern['pattern_name']}",
                'source': 'learned',
                'pattern_id': pattern['id'],
                'success_rate': pattern.get('success_rate', 0.5)
            })
        
        # Add AI options
        for ai_opt in ai_options:
            all_options.append({
                **ai_opt,
                'source': 'ai',
                'success_rate': 0.5  # Unknown success rate for AI decisions
            })
        
        if not all_options:
            # Absolute fallback
            return {
                'action': 'wait',
                'params': {'duration': 2.0},
                'confidence': 0.2,
                'source': 'exploration',
                'reasoning': {
                    'summary': 'No patterns or AI options available',
                    'learned_patterns': 0,
                    'ai_options': 0,
                    'decision_process': 'Fallback to observation'
                }
            }
        
        # Sort by confidence * success_rate (weighted score)
        all_options.sort(
            key=lambda x: x['confidence'] * x['success_rate'],
            reverse=True
        )
        
        # Choose best option
        best = all_options[0]
        
        # Determine if blended
        source = best['source']
        if len(learned_patterns) > 0 and len(ai_options) > 0:
            # Both sources contributed
            source = 'blended'
        
        decision = {
            'action': best['action'],
            'params': best['params'],
            'confidence': best['confidence'],
            'source': source,
            'reasoning': {
                'summary': best['reason'],
                'learned_patterns': len(learned_patterns),
                'ai_options': len(ai_options),
                'total_options': len(all_options),
                'chosen_option': best,
                'decision_process': f"Selected {source} option with {best['confidence']:.0%} confidence"
            }
        }
        
        # Add pattern_id if from learned pattern
        if 'pattern_id' in best:
            decision['pattern_id'] = best['pattern_id']
        
        return decision
    
    async def execute_action(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the decided action"""
        action = decision['action']
        params = decision['params']
        
        async with aiohttp.ClientSession() as session:
            if action == 'tap':
                x, y = params['x'], params['y']
                logger.info(f"👆 Executing: Tap at ({x}, {y})")
                
                async with session.post(
                    f"{self.observation_url}/tap",
                    json={"x": x, "y": y}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    raise Exception(f"Tap failed: {resp.status}")
            
            elif action == 'swipe':
                # TODO: Implement swipe
                logger.info(f"👆 Executing: Swipe {params}")
                return {'status': 'swipe_not_implemented'}
            
            elif action == 'wait':
                duration = params.get('duration', 1.0)
                logger.info(f"⏳ Executing: Wait {duration}s")
                await asyncio.sleep(duration)
                return {'status': 'waited', 'duration': duration}
        
        return {'status': 'no_action'}
    
    async def report_outcome(
        self,
        decision: Dict[str, Any],
        success: bool,
        reward: float = 0.0
    ):
        """
        Report decision outcome for continuous learning
        
        Args:
            decision: The decision that was executed
            success: Whether the action was successful
            reward: Reward/score change (if available)
        """
        # If decision came from learned pattern, update its statistics
        if decision.get('pattern_id'):
            try:
                async with aiohttp.ClientSession() as session:
                    # Update pattern feedback
                    # TODO: Add endpoint in learning service to update pattern stats
                    logger.info(
                        f"📊 Pattern {decision['pattern_id']}: "
                        f"success={success}, reward={reward}"
                    )
            except Exception as e:
                logger.warning(f"Failed to report outcome: {e}")
        
        # Log decision and outcome to database
        try:
            await self.db_manager.execute_write(
                """
                INSERT INTO ai_decisions (
                    session_id, game_id, timestamp,
                    screenshot_path, analysis_result, decision_made,
                    confidence_score, execution_success, reward,
                    metadata
                ) VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, $8, $9)
                """,
                decision.get('session_id', 'autonomous_play'),
                self.game_id,
                decision.get('screenshot_path'),
                json.dumps(decision.get('ai_analysis', {})),
                json.dumps({
                    'action': decision['action'],
                    'params': decision['params'],
                    'source': decision['source']
                }),
                decision['confidence'],
                success,
                reward,
                json.dumps({
                    'reasoning': decision.get('reasoning', {}),
                    'pattern_id': decision.get('pattern_id')
                })
            )
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get engine performance statistics"""
        total_decisions = self.knowledge_hits + self.knowledge_misses
        
        return {
            'total_decisions': total_decisions,
            'knowledge_hits': self.knowledge_hits,
            'knowledge_misses': self.knowledge_misses,
            'knowledge_hit_rate': self.knowledge_hits / max(total_decisions, 1),
            'ai_fallbacks': self.ai_fallbacks
        }
