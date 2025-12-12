"""
Pattern Recognition Engine - Build game_knowledge from learning_data

Analyzes comprehensive vision data to identify:
- Recurring UI patterns and their associated actions
- Scene transition sequences
- Successful action patterns
- UI element -> Action mappings
"""
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class PatternRecognitionEngine:
    """
    Analyze learning_data to extract actionable patterns for AI gameplay
    
    Patterns identified:
    1. UI Element Patterns: Recurring UI elements and successful actions
    2. Scene Transitions: Successful paths through game scenes
    3. Text Triggers: OCR text that indicates specific actions
    4. Position Clusters: Common tap positions for each scene type
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    async def analyze_and_build_patterns(
        self,
        game_id: str,
        min_occurrences: int = 3,
        min_success_rate: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze learning_data and build game_knowledge patterns
        
        Args:
            game_id: Game to analyze
            min_occurrences: Minimum times a pattern must occur
            min_success_rate: Minimum success rate for a pattern
            
        Returns:
            Summary of patterns created
        """
        logger.info(f"🔍 Starting pattern analysis for game: {game_id}")
        
        # Fetch all learning data for analysis
        learning_data = await self._fetch_learning_data(game_id)
        
        if not learning_data:
            logger.warning(f"No learning data found for game: {game_id}")
            return {'patterns_created': 0, 'error': 'No learning data'}
        
        logger.info(f"Analyzing {len(learning_data)} learned actions...")
        
        # Extract different pattern types
        patterns_created = {
            'ui_element_patterns': 0,
            'scene_transition_patterns': 0,
            'text_trigger_patterns': 0,
            'position_cluster_patterns': 0
        }
        
        # 1. UI Element Patterns
        ui_patterns = await self._extract_ui_element_patterns(
            learning_data,
            min_occurrences,
            min_success_rate
        )
        patterns_created['ui_element_patterns'] = len(ui_patterns)
        
        # 2. Scene Transition Patterns
        transition_patterns = await self._extract_scene_transitions(
            learning_data,
            min_occurrences,
            min_success_rate
        )
        patterns_created['scene_transition_patterns'] = len(transition_patterns)
        
        # 3. Text Trigger Patterns
        text_patterns = await self._extract_text_triggers(
            learning_data,
            min_occurrences,
            min_success_rate
        )
        patterns_created['text_trigger_patterns'] = len(text_patterns)
        
        # 4. Position Cluster Patterns
        position_patterns = await self._extract_position_clusters(
            learning_data,
            min_occurrences,
            min_success_rate
        )
        patterns_created['position_cluster_patterns'] = len(position_patterns)
        
        # Save all patterns to game_knowledge
        total_saved = 0
        for patterns in [ui_patterns, transition_patterns, text_patterns, position_patterns]:
            for pattern in patterns:
                if await self._save_pattern_to_knowledge(game_id, pattern):
                    total_saved += 1
        
        logger.info(f"✅ Pattern analysis complete: {total_saved} patterns saved to game_knowledge")
        
        return {
            **patterns_created,
            'total_patterns': total_saved,
            'total_actions_analyzed': len(learning_data)
        }
    
    async def _fetch_learning_data(self, game_id: str) -> List[Dict[str, Any]]:
        """Fetch all learning data for a game"""
        try:
            query = """
                SELECT 
                    id,
                    action_type,
                    tap_x,
                    tap_y,
                    action_params,
                    detected_text,
                    ui_elements,
                    game_state,
                    success,
                    led_to_progress,
                    metadata,
                    timestamp
                FROM learning_data
                WHERE game_id = $1
                ORDER BY timestamp ASC
            """
            
            results = await self.db_manager.execute_many(query, game_id)
            
            return [
                {
                    'id': str(row['id']),
                    'action_type': row['action_type'],
                    'tap_x': row['tap_x'],
                    'tap_y': row['tap_y'],
                    'action_params': json.loads(row['action_params']) if row['action_params'] else {},
                    'detected_text': row['detected_text'] or '',
                    'ui_elements': json.loads(row['ui_elements']) if row['ui_elements'] else [],
                    'game_state': json.loads(row['game_state']) if row['game_state'] else {},
                    'success': row['success'],
                    'led_to_progress': row['led_to_progress'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'timestamp': row['timestamp']
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to fetch learning data: {e}")
            return []
    
    async def _extract_ui_element_patterns(
        self,
        learning_data: List[Dict],
        min_occurrences: int,
        min_success_rate: float
    ) -> List[Dict[str, Any]]:
        """
        Extract patterns based on UI elements
        
        Groups actions by UI element type and position, identifies successful patterns
        """
        patterns = []
        
        # Group by UI element characteristics
        ui_action_groups = defaultdict(list)
        
        for action in learning_data:
            if not action['ui_elements']:
                continue
            
            for elem in action['ui_elements']:
                # Create key based on element type and approximate position
                elem_type = elem.get('type', 'unknown')
                elem_text = elem.get('text', '').lower()[:20] if elem.get('text') else ''
                elem_x_bucket = round(elem.get('x', 0) / 100) * 100  # Bucket positions
                elem_y_bucket = round(elem.get('y', 0) / 100) * 100
                
                key = f"{elem_type}_{elem_text}_{elem_x_bucket}_{elem_y_bucket}"
                
                ui_action_groups[key].append({
                    'action': action,
                    'element': elem
                })
        
        # Analyze each group for patterns
        for key, group in ui_action_groups.items():
            if len(group) < min_occurrences:
                continue
            
            # Calculate success rate
            successful = sum(1 for item in group if item['action']['success'])
            success_rate = successful / len(group)
            
            if success_rate < min_success_rate:
                continue
            
            # Get most common action type
            action_types = [item['action']['action_type'] for item in group]
            most_common_action = Counter(action_types).most_common(1)[0][0]
            
            # Calculate average tap position
            avg_x = sum(item['action']['tap_x'] for item in group) / len(group)
            avg_y = sum(item['action']['tap_y'] for item in group) / len(group)
            
            # Get representative element
            rep_elem = group[0]['element']
            
            patterns.append({
                'pattern_name': f"UI_{rep_elem.get('type', 'element')}_{rep_elem.get('text', '')[:10]}",
                'pattern_type': 'ui_element',
                'trigger_conditions': {
                    'ui_element_type': rep_elem.get('type'),
                    'ui_element_text': rep_elem.get('text', ''),
                    'position_tolerance': 50  # pixels
                },
                'action_template': {
                    'type': most_common_action,
                    'x': int(avg_x),
                    'y': int(avg_y)
                },
                'confidence': success_rate,
                'occurrences': len(group),
                'success_rate': success_rate,
                'metadata': {
                    'ui_element': rep_elem,
                    'sample_actions': [item['action']['id'] for item in group[:5]]
                }
            })
        
        logger.info(f"Extracted {len(patterns)} UI element patterns")
        return patterns
    
    async def _extract_scene_transitions(
        self,
        learning_data: List[Dict],
        min_occurrences: int,
        min_success_rate: float
    ) -> List[Dict[str, Any]]:
        """
        Extract scene transition patterns
        
        Identifies actions that successfully move from one scene to another
        """
        patterns = []
        
        # Group by scene type and action
        scene_action_groups = defaultdict(list)
        
        for action in learning_data:
            scene_type = action['game_state'].get('scene_type', 'unknown')
            if scene_type == 'unknown':
                continue
            
            key = f"{scene_type}_{action['action_type']}"
            scene_action_groups[key].append(action)
        
        # Analyze each scene-action combination
        for key, group in scene_action_groups.items():
            if len(group) < min_occurrences:
                continue
            
            successful_progressive = sum(
                1 for a in group 
                if a['success'] and a['led_to_progress']
            )
            success_rate = successful_progressive / len(group)
            
            if success_rate < min_success_rate:
                continue
            
            scene_type = key.split('_')[0]
            action_type = key.split('_')[1]
            
            # Calculate average action position
            avg_x = sum(a['tap_x'] for a in group if a['tap_x']) / len(group)
            avg_y = sum(a['tap_y'] for a in group if a['tap_y']) / len(group)
            
            patterns.append({
                'pattern_name': f"Scene_{scene_type}_{action_type}",
                'pattern_type': 'scene_transition',
                'trigger_conditions': {
                    'scene_type': scene_type
                },
                'action_template': {
                    'type': action_type,
                    'x': int(avg_x),
                    'y': int(avg_y)
                },
                'confidence': success_rate,
                'occurrences': len(group),
                'success_rate': success_rate,
                'metadata': {
                    'leads_to_progress': True,
                    'sample_actions': [a['id'] for a in group[:5]]
                }
            })
        
        logger.info(f"Extracted {len(patterns)} scene transition patterns")
        return patterns
    
    async def _extract_text_triggers(
        self,
        learning_data: List[Dict],
        min_occurrences: int,
        min_success_rate: float
    ) -> List[Dict[str, Any]]:
        """
        Extract patterns based on OCR text triggers
        
        Identifies keywords/phrases that indicate specific actions
        """
        patterns = []
        
        # Group by detected text keywords
        text_action_groups = defaultdict(list)
        
        # Common keywords to look for
        keywords = [
            'play', 'start', 'continue', 'next', 'retry', 'again',
            'menu', 'settings', 'back', 'ok', 'confirm', 'accept',
            'close', 'exit', 'quit', 'skip'
        ]
        
        for action in learning_data:
            text = action['detected_text'].lower()
            if not text:
                continue
            
            # Check for keywords
            for keyword in keywords:
                if keyword in text:
                    key = f"{keyword}_{action['action_type']}"
                    text_action_groups[key].append(action)
        
        # Analyze each text-action combination
        for key, group in text_action_groups.items():
            if len(group) < min_occurrences:
                continue
            
            successful = sum(1 for a in group if a['success'])
            success_rate = successful / len(group)
            
            if success_rate < min_success_rate:
                continue
            
            keyword = key.split('_')[0]
            action_type = key.split('_')[1]
            
            # Calculate average action position
            avg_x = sum(a['tap_x'] for a in group if a['tap_x']) / len(group)
            avg_y = sum(a['tap_y'] for a in group if a['tap_y']) / len(group)
            
            patterns.append({
                'pattern_name': f"Text_{keyword}_{action_type}",
                'pattern_type': 'text_trigger',
                'trigger_conditions': {
                    'text_contains': keyword
                },
                'action_template': {
                    'type': action_type,
                    'x': int(avg_x),
                    'y': int(avg_y)
                },
                'confidence': success_rate,
                'occurrences': len(group),
                'success_rate': success_rate,
                'metadata': {
                    'trigger_keyword': keyword,
                    'sample_actions': [a['id'] for a in group[:5]]
                }
            })
        
        logger.info(f"Extracted {len(patterns)} text trigger patterns")
        return patterns
    
    async def _extract_position_clusters(
        self,
        learning_data: List[Dict],
        min_occurrences: int,
        min_success_rate: float
    ) -> List[Dict[str, Any]]:
        """
        Extract position cluster patterns
        
        Identifies commonly tapped positions for each scene type
        """
        patterns = []
        
        # Group by scene and position clusters
        scene_position_groups = defaultdict(list)
        
        for action in learning_data:
            if not action['tap_x'] or not action['tap_y']:
                continue
            
            scene_type = action['game_state'].get('scene_type', 'unknown')
            if scene_type == 'unknown':
                continue
            
            # Cluster positions (50 pixel buckets)
            x_bucket = round(action['tap_x'] / 50) * 50
            y_bucket = round(action['tap_y'] / 50) * 50
            
            key = f"{scene_type}_{x_bucket}_{y_bucket}"
            scene_position_groups[key].append(action)
        
        # Analyze each cluster
        for key, group in scene_position_groups.items():
            if len(group) < min_occurrences:
                continue
            
            successful = sum(1 for a in group if a['success'])
            success_rate = successful / len(group)
            
            if success_rate < min_success_rate:
                continue
            
            parts = key.split('_')
            scene_type = parts[0]
            
            # Calculate precise average position
            avg_x = sum(a['tap_x'] for a in group) / len(group)
            avg_y = sum(a['tap_y'] for a in group) / len(group)
            
            # Most common action type
            action_types = [a['action_type'] for a in group]
            common_action = Counter(action_types).most_common(1)[0][0]
            
            patterns.append({
                'pattern_name': f"Position_{scene_type}_{int(avg_x)}_{int(avg_y)}",
                'pattern_type': 'position_cluster',
                'trigger_conditions': {
                    'scene_type': scene_type
                },
                'action_template': {
                    'type': common_action,
                    'x': int(avg_x),
                    'y': int(avg_y)
                },
                'confidence': success_rate,
                'occurrences': len(group),
                'success_rate': success_rate,
                'metadata': {
                    'position_cluster': f"({int(avg_x)}, {int(avg_y)})",
                    'sample_actions': [a['id'] for a in group[:5]]
                }
            })
        
        logger.info(f"Extracted {len(patterns)} position cluster patterns")
        return patterns
    
    async def _save_pattern_to_knowledge(
        self,
        game_id: str,
        pattern: Dict[str, Any]
    ) -> bool:
        """Save a pattern to game_knowledge table"""
        try:
            query = """
                INSERT INTO game_knowledge (
                    game_id,
                    pattern_name,
                    pattern_type,
                    trigger_conditions,
                    action_template,
                    confidence_score,
                    usage_count,
                    success_count,
                    last_used,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, NULL, $9, NOW(), NOW()
                )
                ON CONFLICT (game_id, pattern_name) 
                DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    usage_count = EXCLUDED.usage_count,
                    success_count = EXCLUDED.success_count,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """
            
            await self.db_manager.execute_write(
                query,
                game_id,
                pattern['pattern_name'],
                pattern['pattern_type'],
                json.dumps(pattern['trigger_conditions']),
                json.dumps(pattern['action_template']),
                pattern['confidence'],
                pattern['occurrences'],
                int(pattern['occurrences'] * pattern['success_rate']),
                json.dumps(pattern.get('metadata', {}))
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save pattern {pattern['pattern_name']}: {e}")
            return False
    
    async def get_pattern_analysis_status(self, game_id: str) -> Dict[str, Any]:
        """Get status of pattern analysis for a game"""
        try:
            # Count learning data
            learning_count = await self.db_manager.execute_one(
                "SELECT COUNT(*) as count FROM learning_data WHERE game_id = $1",
                game_id
            )
            
            # Count patterns
            pattern_count = await self.db_manager.execute_one(
                "SELECT COUNT(*) as count FROM game_knowledge WHERE game_id = $1",
                game_id
            )
            
            # Get pattern type breakdown
            pattern_types = await self.db_manager.execute_many(
                """
                SELECT pattern_type, COUNT(*) as count
                FROM game_knowledge
                WHERE game_id = $1
                GROUP BY pattern_type
                """,
                game_id
            )
            
            return {
                'learning_data_count': learning_count['count'] if learning_count else 0,
                'total_patterns': pattern_count['count'] if pattern_count else 0,
                'pattern_breakdown': {
                    row['pattern_type']: row['count']
                    for row in pattern_types
                },
                'ready_for_ai_play': (pattern_count['count'] if pattern_count else 0) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get pattern analysis status: {e}")
            return {'error': str(e)}
