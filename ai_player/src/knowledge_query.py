"""
Knowledge Query Engine - Query learning_data for AI gameplay decisions

Uses comprehensive vision analysis data (OCR, UI elements, scene descriptions, patterns)
to find matching learned actions and build gameplay decisions.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class KnowledgeQueryEngine:
    """
    Query learning_data using comprehensive vision analysis
    
    Matches current game state against learned demonstrations to find
    appropriate actions based on:
    - Scene type similarity
    - UI element matching
    - OCR text similarity
    - Game state conditions
    - Success patterns
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    async def query_learned_actions(
        self,
        game_id: str,
        current_scene: str,
        ui_elements: List[Dict] = None,
        detected_text: str = "",
        scene_description: str = "",
        min_confidence: float = 0.5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query learning_data for actions matching current game state
        
        Args:
            game_id: Game being played
            current_scene: Scene type (menu, gameplay, victory, etc.)
            ui_elements: Detected UI elements with positions
            detected_text: OCR text from screen
            scene_description: BLIP-2 scene description
            min_confidence: Minimum confidence threshold
            limit: Max number of results
            
        Returns:
            List of matching actions with confidence scores
        """
        try:
            # Build query based on available data
            conditions = ["game_id = $1", "success = true"]
            params = [game_id]
            param_idx = 2
            
            # Match scene type
            if current_scene and current_scene != 'unknown':
                conditions.append(f"game_state->>'scene_type' = ${param_idx}")
                params.append(current_scene)
                param_idx += 1
            
            # Match by OCR text similarity (if significant text detected)
            if detected_text and len(detected_text.strip()) > 10:
                conditions.append(f"detected_text ILIKE ${param_idx}")
                params.append(f"%{detected_text[:50]}%")  # First 50 chars
                param_idx += 1
            
            # Build query
            query = f"""
                SELECT 
                    id,
                    action_type,
                    action_params,
                    tap_x,
                    tap_y,
                    detected_text,
                    ui_elements,
                    game_state,
                    metadata,
                    created_at,
                    -- Calculate confidence based on multiple factors
                    CASE 
                        WHEN game_state->>'scene_type' = $2 THEN 0.4
                        ELSE 0.2
                    END +
                    CASE 
                        WHEN detected_text ILIKE ${param_idx if len(detected_text.strip()) > 10 else 'NULL'} THEN 0.3
                        ELSE 0
                    END +
                    CASE 
                        WHEN jsonb_array_length(ui_elements) > 0 THEN 0.3
                        ELSE 0.1
                    END AS match_confidence
                FROM learning_data
                WHERE {' AND '.join(conditions)}
                ORDER BY match_confidence DESC, created_at DESC
                LIMIT ${param_idx}
            """
            params.append(limit)
            
            results = await self.db_manager.execute_many(query, *params)
            
            if not results:
                logger.info(f"No learned actions found for scene: {current_scene}")
                return []
            
            # Process results and calculate UI similarity
            matched_actions = []
            for row in results:
                action = {
                    'id': str(row['id']),
                    'action_type': row['action_type'],
                    'action': {
                        'type': row['action_type'],
                        'x': row['tap_x'],
                        'y': row['tap_y'],
                        'params': json.loads(row['action_params']) if row['action_params'] else {}
                    },
                    'detected_text': row['detected_text'],
                    'ui_elements': json.loads(row['ui_elements']) if row['ui_elements'] else [],
                    'game_state': json.loads(row['game_state']) if row['game_state'] else {},
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'match_confidence': float(row['match_confidence']),
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
                
                # Boost confidence if UI elements match
                if ui_elements and action['ui_elements']:
                    ui_similarity = self._calculate_ui_similarity(
                        ui_elements,
                        action['ui_elements']
                    )
                    action['match_confidence'] = min(
                        action['match_confidence'] + (ui_similarity * 0.2),
                        1.0
                    )
                    action['ui_similarity'] = ui_similarity
                
                # Filter by minimum confidence
                if action['match_confidence'] >= min_confidence:
                    matched_actions.append(action)
            
            logger.info(
                f"✅ Found {len(matched_actions)} learned actions "
                f"(filtered from {len(results)} total, min_conf={min_confidence})"
            )
            
            return sorted(
                matched_actions,
                key=lambda x: x['match_confidence'],
                reverse=True
            )
            
        except Exception as e:
            logger.error(f"Failed to query learned actions: {e}", exc_info=True)
            return []
    
    def _calculate_ui_similarity(
        self,
        current_elements: List[Dict],
        learned_elements: List[Dict]
    ) -> float:
        """
        Calculate similarity between current and learned UI elements
        
        Matches based on:
        - Element type
        - Relative position
        - Text content (if available)
        
        Returns: Similarity score 0.0-1.0
        """
        if not current_elements or not learned_elements:
            return 0.0
        
        matches = 0
        total_comparisons = min(len(current_elements), len(learned_elements))
        
        for curr_elem in current_elements[:total_comparisons]:
            for learn_elem in learned_elements[:total_comparisons]:
                similarity = 0.0
                
                # Type match
                if curr_elem.get('type') == learn_elem.get('type'):
                    similarity += 0.5
                
                # Position similarity (within 10% tolerance)
                curr_x = curr_elem.get('x', 0)
                curr_y = curr_elem.get('y', 0)
                learn_x = learn_elem.get('x', 0)
                learn_y = learn_elem.get('y', 0)
                
                if curr_x and learn_x and curr_y and learn_y:
                    x_diff = abs(curr_x - learn_x) / max(curr_x, learn_x, 1)
                    y_diff = abs(curr_y - learn_y) / max(curr_y, learn_y, 1)
                    
                    if x_diff < 0.1 and y_diff < 0.1:
                        similarity += 0.3
                
                # Text match
                if curr_elem.get('text') and learn_elem.get('text'):
                    if curr_elem['text'].lower() == learn_elem['text'].lower():
                        similarity += 0.2
                
                if similarity > 0.5:  # Threshold for considering it a match
                    matches += 1
                    break  # Found a match for this element
        
        return matches / total_comparisons if total_comparisons > 0 else 0.0
    
    async def query_by_scene_progression(
        self,
        game_id: str,
        current_scene: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Query actions that successfully led to scene progression
        
        Finds actions that:
        1. Were performed in current_scene
        2. Had led_to_progress = true
        3. Were successful
        
        Args:
            game_id: Game ID
            current_scene: Current scene type
            limit: Max results
            
        Returns:
            List of progressive actions
        """
        try:
            query = """
                SELECT 
                    id,
                    action_type,
                    tap_x,
                    tap_y,
                    action_params,
                    ui_elements,
                    game_state,
                    detected_text,
                    metadata
                FROM learning_data
                WHERE game_id = $1
                    AND game_state->>'scene_type' = $2
                    AND success = true
                    AND led_to_progress = true
                ORDER BY created_at DESC
                LIMIT $3
            """
            
            results = await self.db_manager.execute_many(query, game_id, current_scene, limit)
            
            actions = []
            for row in results:
                actions.append({
                    'id': str(row['id']),
                    'action_type': row['action_type'],
                    'action': {
                        'type': row['action_type'],
                        'x': row['tap_x'],
                        'y': row['tap_y'],
                        'params': json.loads(row['action_params']) if row['action_params'] else {}
                    },
                    'ui_elements': json.loads(row['ui_elements']) if row['ui_elements'] else [],
                    'game_state': json.loads(row['game_state']) if row['game_state'] else {},
                    'detected_text': row['detected_text'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'confidence': 0.8,  # High confidence for progressive actions
                    'reason': 'Action led to game progression'
                })
            
            logger.info(f"Found {len(actions)} progressive actions for scene: {current_scene}")
            return actions
            
        except Exception as e:
            logger.error(f"Failed to query progressive actions: {e}")
            return []
    
    async def query_by_ui_pattern(
        self,
        game_id: str,
        ui_pattern: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query actions based on UI pattern matching
        
        Args:
            game_id: Game ID
            ui_pattern: UI element pattern to match (type, position, text)
            limit: Max results
            
        Returns:
            Matching actions
        """
        try:
            # Query all successful actions with UI elements
            query = """
                SELECT 
                    id,
                    action_type,
                    tap_x,
                    tap_y,
                    action_params,
                    ui_elements,
                    game_state,
                    metadata
                FROM learning_data
                WHERE game_id = $1
                    AND success = true
                    AND jsonb_array_length(ui_elements) > 0
                ORDER BY created_at DESC
                LIMIT 100
            """
            
            results = await self.db_manager.execute_many(query, game_id)
            
            # Filter by UI pattern similarity
            matched_actions = []
            for row in results:
                ui_elements = json.loads(row['ui_elements']) if row['ui_elements'] else []
                
                # Check if any UI element matches the pattern
                for elem in ui_elements:
                    match_score = 0.0
                    
                    if ui_pattern.get('type') == elem.get('type'):
                        match_score += 0.5
                    
                    if ui_pattern.get('text') and elem.get('text'):
                        if ui_pattern['text'].lower() in elem['text'].lower():
                            match_score += 0.5
                    
                    if match_score > 0.5:
                        matched_actions.append({
                            'id': str(row['id']),
                            'action_type': row['action_type'],
                            'action': {
                                'type': row['action_type'],
                                'x': row['tap_x'],
                                'y': row['tap_y'],
                                'params': json.loads(row['action_params']) if row['action_params'] else {}
                            },
                            'ui_elements': ui_elements,
                            'game_state': json.loads(row['game_state']) if row['game_state'] else {},
                            'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                            'match_confidence': match_score,
                            'matched_element': elem
                        })
                        break  # Found a match
                
                if len(matched_actions) >= limit:
                    break
            
            logger.info(f"Found {len(matched_actions)} UI pattern matches")
            return sorted(matched_actions, key=lambda x: x['match_confidence'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to query by UI pattern: {e}")
            return []
    
    async def get_knowledge_stats(self, game_id: str) -> Dict[str, Any]:
        """
        Get statistics about learned knowledge for a game
        
        Returns:
            Stats about learned actions, scenes, UI elements, etc.
        """
        try:
            stats_query = """
                SELECT 
                    COUNT(*) as total_actions,
                    COUNT(DISTINCT game_state->>'scene_type') as unique_scenes,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_actions,
                    SUM(CASE WHEN led_to_progress THEN 1 ELSE 0 END) as progressive_actions,
                    AVG(jsonb_array_length(ui_elements)) as avg_ui_elements,
                    COUNT(DISTINCT detected_text) as unique_text_patterns
                FROM learning_data
                WHERE game_id = $1
            """
            
            result = await self.db_manager.execute_one(stats_query, game_id)
            
            if not result:
                return {'total_actions': 0}
            
            return {
                'total_actions': result['total_actions'] or 0,
                'unique_scenes': result['unique_scenes'] or 0,
                'successful_actions': result['successful_actions'] or 0,
                'progressive_actions': result['progressive_actions'] or 0,
                'avg_ui_elements': float(result['avg_ui_elements'] or 0),
                'unique_text_patterns': result['unique_text_patterns'] or 0,
                'success_rate': (result['successful_actions'] / max(result['total_actions'], 1)) if result['total_actions'] else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge stats: {e}")
            return {'total_actions': 0, 'error': str(e)}
