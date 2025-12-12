"""
Knowledge Builder - Convert learning data into actionable game knowledge

This module:
1. Analyzes video_frames and learning_data to identify patterns
2. Builds game_knowledge entries (state-action templates)
3. Tracks pattern success rates and confidence scores
4. Provides query API for fast pattern matching during gameplay
"""
import logging
import json
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class KnowledgeBuilder:
    """Build game knowledge from learning data"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    async def build_knowledge_from_video(
        self,
        video_id: str,
        game_id: str
    ) -> Dict[str, Any]:
        """
        Analyze video frames and extracted actions to build game knowledge
        
        Returns:
            Statistics about patterns created
        """
        logger.info(f"🧠 Building knowledge from video {video_id}")
        
        # Step 1: Get all frames from video
        frames = await self.db_manager.execute_read(
            """
            SELECT 
                id, frame_number, timestamp_ms,
                touch_detected, touch_x, touch_y, touch_type,
                screen_analysis, scene_type, action_id
            FROM video_frames
            WHERE video_id = $1
            ORDER BY frame_number
            """,
            video_id
        )
        
        if not frames:
            logger.warning(f"No frames found for video {video_id}")
            return {'patterns_created': 0}
        
        # Step 2: Group frames by scene type
        scenes_by_type = defaultdict(list)
        for frame in frames:
            scenes_by_type[frame['scene_type']].append(frame)
        
        # Step 3: Identify patterns
        patterns_created = 0
        
        # Pattern 1: Button tap patterns (most common in games)
        tap_patterns = await self._identify_tap_patterns(frames, game_id)
        patterns_created += len(tap_patterns)
        
        # Pattern 2: Scene-specific UI interactions
        ui_patterns = await self._identify_ui_patterns(scenes_by_type, game_id)
        patterns_created += len(ui_patterns)
        
        # Pattern 3: Action sequences (e.g., navigate to play button)
        sequence_patterns = await self._identify_sequences(frames, game_id)
        patterns_created += len(sequence_patterns)
        
        # Pattern 4: Recovery patterns (getting unstuck)
        recovery_patterns = await self._identify_recovery_patterns(scenes_by_type, game_id)
        patterns_created += len(recovery_patterns)
        
        logger.info(f"✅ Created {patterns_created} knowledge patterns")
        
        return {
            'patterns_created': patterns_created,
            'tap_patterns': len(tap_patterns),
            'ui_patterns': len(ui_patterns),
            'sequence_patterns': len(sequence_patterns),
            'recovery_patterns': len(recovery_patterns)
        }
    
    async def _identify_tap_patterns(
        self,
        frames: List[Dict],
        game_id: str
    ) -> List[str]:
        """
        Identify tap patterns from frames with detected touches
        
        Returns:
            List of created pattern IDs
        """
        patterns = []
        
        # Group taps by screen region (grid-based clustering)
        tap_clusters = defaultdict(list)
        
        for frame in frames:
            if not frame['touch_detected'] or frame['touch_type'] != 'tap':
                continue
            
            # Cluster by 100x100 pixel regions
            region_x = frame['touch_x'] // 100
            region_y = frame['touch_y'] // 100
            region_key = f"{region_x}_{region_y}"
            
            tap_clusters[region_key].append(frame)
        
        # Create pattern for each significant cluster (>= 2 taps)
        for region_key, cluster_frames in tap_clusters.items():
            if len(cluster_frames) < 2:
                continue  # Skip single-tap regions
            
            # Calculate average tap position
            avg_x = int(np.mean([f['touch_x'] for f in cluster_frames]))
            avg_y = int(np.mean([f['touch_y'] for f in cluster_frames]))
            
            # Get most common scene type for this tap
            scene_types = [f['scene_type'] for f in cluster_frames]
            most_common_scene = Counter(scene_types).most_common(1)[0][0]
            
            # Analyze screen conditions (what was on screen when this tap occurred)
            screen_conditions = await self._analyze_screen_conditions(cluster_frames)
            
            # Create action template
            action_template = {
                'type': 'tap',
                'x': avg_x,
                'y': avg_y,
                'region': region_key,
                'delay_after': 0.5  # Default delay
            }
            
            # Create knowledge entry
            pattern_record = await self.db_manager.execute_one(
                """
                INSERT INTO game_knowledge (
                    game_id, pattern_type, pattern_name, pattern_data,
                    screen_conditions, action_template,
                    times_seen, confidence_score,
                    learned_from_video, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                game_id,
                'tap_button',
                f"Tap at ({avg_x}, {avg_y}) in {most_common_scene}",
                json.dumps({
                    'region': region_key,
                    'tap_count': len(cluster_frames),
                    'scene': most_common_scene
                }),
                json.dumps(screen_conditions),
                json.dumps(action_template),
                len(cluster_frames),
                0.6,  # Initial confidence
                True,
                json.dumps({
                    'created_from': 'video_analysis',
                    'cluster_size': len(cluster_frames)
                })
            )
            pattern_id = str(pattern_record['id'])
            
            patterns.append(pattern_id)
            logger.debug(f"  Created tap pattern: {region_key} ({len(cluster_frames)} taps)")
        
        return patterns
    
    async def _identify_ui_patterns(
        self,
        scenes_by_type: Dict[str, List],
        game_id: str
    ) -> List[str]:
        """
        Identify UI interaction patterns specific to scene types
        (e.g., "Play" button in menu, "Continue" in dialog)
        """
        patterns = []
        
        for scene_type, scene_frames in scenes_by_type.items():
            if scene_type == 'unknown':
                continue
            
            # Find frames with detected UI elements
            ui_frames = [f for f in scene_frames if f.get('screen_analysis')]
            if not ui_frames:
                continue
            
            # Parse screen analysis to find buttons
            all_ui_elements = []
            for frame in ui_frames:
                try:
                    analysis = json.loads(frame['screen_analysis']) if isinstance(frame['screen_analysis'], str) else frame['screen_analysis']
                    if analysis and 'ui_elements' in analysis:
                        all_ui_elements.extend(analysis['ui_elements'])
                except:
                    continue
            
            # Group UI elements by type/text
            ui_by_text = defaultdict(list)
            for elem in all_ui_elements:
                if 'text' in elem and 'x' in elem:
                    ui_by_text[elem['text'].lower()].append(elem)
            
            # Create patterns for common UI elements
            for ui_text, elements in ui_by_text.items():
                if len(elements) < 2:
                    continue
                
                avg_x = int(np.mean([e['x'] for e in elements]))
                avg_y = int(np.mean([e['y'] for e in elements]))
                
                pattern_name = f"Click '{ui_text}' in {scene_type}"
                
                action_template = {
                    'type': 'tap',
                    'x': avg_x,
                    'y': avg_y,
                    'target': ui_text
                }
                
                screen_conditions = {
                    'scene_type': scene_type,
                    'has_text': ui_text
                }
                
                pattern_record = await self.db_manager.execute_one(
                    """
                    INSERT INTO game_knowledge (
                        game_id, pattern_type, pattern_name, pattern_data,
                        screen_conditions, action_template,
                        times_seen, confidence_score,
                        learned_from_video, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                    """,
                    game_id,
                    'ui_interaction',
                    pattern_name,
                    json.dumps({
                        'ui_text': ui_text,
                        'scene': scene_type,
                        'count': len(elements)
                    }),
                    json.dumps(screen_conditions),
                    json.dumps(action_template),
                    len(elements),
                    0.7,
                    True,
                    json.dumps({'ui_element_type': 'button'})
                )
                pattern_id = str(pattern_record['id'])
                
                patterns.append(pattern_id)
                logger.debug(f"  Created UI pattern: {pattern_name}")
        
        return patterns
    
    async def _identify_sequences(
        self,
        frames: List[Dict],
        game_id: str
    ) -> List[str]:
        """
        Identify action sequences (multiple actions in order)
        E.g., Tap A → Wait → Tap B
        """
        patterns = []
        
        # Find consecutive touch actions
        touch_frames = [f for f in frames if f['touch_detected']]
        
        # Look for pairs of actions within 5 seconds
        for i in range(len(touch_frames) - 1):
            frame1 = touch_frames[i]
            frame2 = touch_frames[i + 1]
            
            time_diff_ms = frame2['timestamp_ms'] - frame1['timestamp_ms']
            
            # Sequence: 2 actions within 5 seconds, different scenes
            if 1000 < time_diff_ms < 5000 and frame1['scene_type'] != frame2['scene_type']:
                sequence_name = f"Navigate: {frame1['scene_type']} → {frame2['scene_type']}"
                
                action_template = {
                    'type': 'sequence',
                    'actions': [
                        {
                            'type': 'tap',
                            'x': frame1['touch_x'],
                            'y': frame1['touch_y']
                        },
                        {
                            'type': 'wait',
                            'duration': time_diff_ms / 1000.0
                        },
                        {
                            'type': 'tap',
                            'x': frame2['touch_x'],
                            'y': frame2['touch_y']
                        }
                    ]
                }
                
                screen_conditions = {
                    'scene_type': frame1['scene_type'],
                    'next_scene': frame2['scene_type']
                }
                
                # Check if this sequence already exists
                existing = await self.db_manager.execute_read(
                    """
                    SELECT id FROM game_knowledge
                    WHERE game_id = $1 
                    AND pattern_type = 'sequence'
                    AND pattern_name = $2
                    """,
                    game_id,
                    sequence_name
                )
                
                if not existing:
                    pattern_record = await self.db_manager.execute_one(
                        """
                        INSERT INTO game_knowledge (
                            game_id, pattern_type, pattern_name, pattern_data,
                            screen_conditions, action_template,
                            times_seen, confidence_score,
                            learned_from_video, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        RETURNING id
                        """,
                        game_id,
                        'sequence',
                        sequence_name,
                        json.dumps({
                            'from_scene': frame1['scene_type'],
                            'to_scene': frame2['scene_type'],
                            'time_between_ms': time_diff_ms
                        }),
                        json.dumps(screen_conditions),
                        json.dumps(action_template),
                        1,
                        0.5,
                        True,
                        json.dumps({'auto_detected': True})
                    )
                    pattern_id = str(pattern_record['id'])
                    
                    patterns.append(pattern_id)
                    logger.debug(f"  Created sequence: {sequence_name}")
        
        return patterns
    
    async def _identify_recovery_patterns(
        self,
        scenes_by_type: Dict[str, List],
        game_id: str
    ) -> List[str]:
        """
        Identify recovery patterns (getting unstuck from dialogs, popups, etc.)
        """
        patterns = []
        
        # Recovery is usually from defeat/dialog to menu/gameplay
        recovery_scenes = ['defeat', 'dialog', 'loading']
        
        for scene_type in recovery_scenes:
            frames = scenes_by_type.get(scene_type, [])
            if not frames:
                continue
            
            # Find touches in these scenes (usually dismiss/retry buttons)
            touch_frames = [f for f in frames if f['touch_detected']]
            
            if touch_frames:
                # Create general recovery pattern for this scene type
                avg_x = int(np.mean([f['touch_x'] for f in touch_frames]))
                avg_y = int(np.mean([f['touch_y'] for f in touch_frames]))
                
                pattern_name = f"Recover from {scene_type}"
                
                action_template = {
                    'type': 'tap',
                    'x': avg_x,
                    'y': avg_y,
                    'purpose': 'recovery'
                }
                
                screen_conditions = {
                    'scene_type': scene_type
                }
                
                pattern_record = await self.db_manager.execute_one(
                    """
                    INSERT INTO game_knowledge (
                        game_id, pattern_type, pattern_name, pattern_data,
                        screen_conditions, action_template,
                        times_seen, confidence_score,
                        learned_from_video, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                    """,
                    game_id,
                    'recovery',
                    pattern_name,
                    json.dumps({
                        'scene': scene_type,
                        'tap_count': len(touch_frames)
                    }),
                    json.dumps(screen_conditions),
                    json.dumps(action_template),
                    len(touch_frames),
                    0.6,
                    True,
                    json.dumps({'purpose': 'unstuck'})
                )
                pattern_id = str(pattern_record['id'])
                
                patterns.append(pattern_id)
                logger.debug(f"  Created recovery pattern: {pattern_name}")
        
        return patterns
    
    async def _analyze_screen_conditions(self, frames: List[Dict]) -> Dict[str, Any]:
        """
        Analyze common screen conditions from a group of frames
        """
        conditions = {
            'scene_types': [],
            'common_texts': [],
            'ui_elements': []
        }
        
        for frame in frames:
            conditions['scene_types'].append(frame['scene_type'])
            
            if frame.get('screen_analysis'):
                try:
                    analysis = json.loads(frame['screen_analysis']) if isinstance(frame['screen_analysis'], str) else frame['screen_analysis']
                    if analysis.get('ocr_text'):
                        conditions['common_texts'].append(analysis['ocr_text'])
                except:
                    pass
        
        # Get most common scene type
        if conditions['scene_types']:
            most_common_scene = Counter(conditions['scene_types']).most_common(1)[0][0]
            conditions['scene_type'] = most_common_scene
        
        return conditions
    
    async def query_knowledge(
        self,
        game_id: str,
        current_scene: str,
        detected_text: Optional[str] = None,
        ui_elements: Optional[List[Dict]] = None,
        pattern_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query game knowledge for matching patterns
        
        Args:
            game_id: Game UUID
            current_scene: Current scene type (menu, gameplay, etc.)
            detected_text: OCR text from current screen
            ui_elements: Detected UI elements
            pattern_types: Filter by pattern types
            
        Returns:
            List of matching patterns, sorted by confidence
        """
        query = """
            SELECT 
                id, pattern_type, pattern_name, pattern_data,
                screen_conditions, action_template,
                confidence_score, times_successful, times_failed,
                metadata
            FROM game_knowledge
            WHERE game_id = $1
        """
        params = [game_id]
        
        # Filter by pattern types if specified
        if pattern_types:
            query += " AND pattern_type = ANY($2)"
            params.append(pattern_types)
        
        # Order by confidence and usage
        query += """
            ORDER BY 
                confidence_score DESC,
                times_successful DESC,
                updated_at DESC
            LIMIT 20
        """
        
        results = await self.db_manager.execute_read(query, *params)
        
        # Filter and score matches based on screen conditions
        matches = []
        for row in results:
            try:
                conditions = json.loads(row['screen_conditions']) if isinstance(row['screen_conditions'], str) else row['screen_conditions']
                
                # Check scene match
                if conditions.get('scene_type') == current_scene:
                    match_score = row['confidence_score']
                    
                    # Bonus for text match
                    if detected_text and conditions.get('has_text'):
                        if conditions['has_text'].lower() in detected_text.lower():
                            match_score += 0.1
                    
                    matches.append({
                        'id': row['id'],
                        'pattern_type': row['pattern_type'],
                        'pattern_name': row['pattern_name'],
                        'action_template': json.loads(row['action_template']) if isinstance(row['action_template'], str) else row['action_template'],
                        'confidence': match_score,
                        'success_rate': row['times_successful'] / max(row['times_successful'] + row['times_failed'], 1)
                    })
            except Exception as e:
                logger.warning(f"Failed to process pattern {row['id']}: {e}")
                continue
        
        # Sort by match score
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches
    
    async def update_pattern_feedback(
        self,
        pattern_id: str,
        success: bool,
        reward: float = 0.0
    ):
        """
        Update pattern statistics based on execution feedback
        """
        if success:
            await self.db_manager.execute_write(
                """
                UPDATE game_knowledge
                SET times_successful = times_successful + 1,
                    avg_reward = (avg_reward * times_seen + $1) / (times_seen + 1),
                    times_seen = times_seen + 1,
                    last_used_at = NOW()
                WHERE id = $2
                """,
                reward,
                pattern_id
            )
        else:
            await self.db_manager.execute_write(
                """
                UPDATE game_knowledge
                SET times_failed = times_failed + 1,
                    times_seen = times_seen + 1,
                    last_used_at = NOW()
                WHERE id = $1
                """,
                pattern_id
            )
        
        logger.debug(f"Updated pattern {pattern_id}: success={success}, reward={reward}")
