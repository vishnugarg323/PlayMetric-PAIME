"""
Learning Recorder - Records all gameplay data for AI training
Stores both AI gameplay and user gameplay for building comprehensive training datasets
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


class LearningRecorder:
    """Records gameplay data to learning_data table"""
    
    def __init__(self, db_manager):
        """
        Initialize learning recorder
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.buffer = []  # Buffer for batch inserts
        self.buffer_size = 10  # Flush after 10 records
        
    async def record_action(
        self,
        session_id: str,
        game_id: str,
        game_version_id: str,
        action_type: str,
        action_params: Dict[str, Any],
        screenshot_before: Optional[str] = None,
        screenshot_after: Optional[str] = None,
        is_user_action: bool = False,
        learning_mode: str = 'auto_play',
        game_state: Optional[Dict[str, Any]] = None,
        level_identifier: Optional[str] = None,
        reward: Optional[float] = None,
        success: Optional[bool] = None,
        led_to_progress: Optional[bool] = None,
        led_to_crash: bool = False,
        device_type: str = 'emulator',
        agent_mode: str = 'heuristic',
        ui_elements: Optional[List[Dict]] = None,
        detected_text: Optional[str] = None,
        state_features: Optional[List[float]] = None,
        visual_features: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a single gameplay action to the learning dataset
        
        Args:
            session_id: Current session ID
            game_id: Game UUID
            game_version_id: Game version UUID
            action_type: Type of action (tap, swipe_up, etc.)
            action_params: Full action parameters as dict
            screenshot_before: Path to screenshot before action
            screenshot_after: Path to screenshot after action
            is_user_action: True if user performed action, False if AI
            learning_mode: 'auto_play' or 'user_guided'
            game_state: Extracted game state (score, level, etc.)
            level_identifier: Level/screen identifier
            reward: Calculated reward
            success: Whether action succeeded
            led_to_progress: Whether action led to game progress
            led_to_crash: Whether action caused crash
            device_type: 'emulator' or 'physical'
            agent_mode: Agent mode used
            ui_elements: Detected UI elements
            detected_text: OCR extracted text
            state_features: Encoded state features for ML
            visual_features: Visual features from screenshots
            metadata: Additional metadata
        """
        try:
            # Extract tap coordinates
            tap_x = action_params.get('x')
            tap_y = action_params.get('y')
            
            # Calculate screenshot hashes if paths provided
            screenshot_before_hash = self._hash_file(screenshot_before) if screenshot_before else None
            screenshot_after_hash = self._hash_file(screenshot_after) if screenshot_after else None
            
            # Prepare data for insertion
            record = {
                'session_id': session_id,
                'game_id': game_id,
                'game_version_id': game_version_id,
                'screenshot_before_path': screenshot_before,
                'screenshot_before_hash': screenshot_before_hash,
                'screenshot_after_path': screenshot_after,
                'screenshot_after_hash': screenshot_after_hash,
                'action_type': action_type,
                'action_params': json.dumps(action_params),
                'tap_x': tap_x,
                'tap_y': tap_y,
                'is_user_action': is_user_action,
                'learning_mode': learning_mode,
                'game_state': json.dumps(game_state) if game_state else None,
                'level_identifier': level_identifier,
                'detected_text': detected_text,
                'ui_elements': json.dumps(ui_elements) if ui_elements else None,
                'reward': reward,
                'success': success,
                'led_to_progress': led_to_progress,
                'led_to_crash': led_to_crash,
                'state_features': state_features,
                'visual_features': visual_features,
                'device_type': device_type,
                'agent_mode': agent_mode,
                'metadata': json.dumps(metadata) if metadata else '{}'
            }
            
            # Add to buffer
            self.buffer.append(record)
            
            # Flush if buffer full
            if len(self.buffer) >= self.buffer_size:
                await self.flush()
                
            logger.debug(f"📝 Recorded learning data: {action_type} ({'USER' if is_user_action else 'AI'}) at ({tap_x}, {tap_y})")
            
        except Exception as e:
            logger.error(f"❌ Failed to record learning data: {e}", exc_info=True)
    
    async def flush(self):
        """Flush buffered records to database"""
        if not self.buffer:
            return
            
        try:
            # Batch insert all buffered records
            query = """
                INSERT INTO learning_data (
                    session_id, game_id, game_version_id,
                    screenshot_before_path, screenshot_before_hash,
                    screenshot_after_path, screenshot_after_hash,
                    action_type, action_params, tap_x, tap_y,
                    is_user_action, learning_mode,
                    game_state, level_identifier, detected_text, ui_elements,
                    reward, success, led_to_progress, led_to_crash,
                    state_features, visual_features,
                    device_type, agent_mode, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $19, $20, $21,
                    $22, $23, $24, $25, $26
                )
            """
            
            for record in self.buffer:
                await self.db_manager.execute_write(
                    query,
                    record['session_id'],
                    record['game_id'],
                    record['game_version_id'],
                    record['screenshot_before_path'],
                    record['screenshot_before_hash'],
                    record['screenshot_after_path'],
                    record['screenshot_after_hash'],
                    record['action_type'],
                    record['action_params'],
                    record['tap_x'],
                    record['tap_y'],
                    record['is_user_action'],
                    record['learning_mode'],
                    record['game_state'],
                    record['level_identifier'],
                    record['detected_text'],
                    record['ui_elements'],
                    record['reward'],
                    record['success'],
                    record['led_to_progress'],
                    record['led_to_crash'],
                    record['state_features'],
                    record['visual_features'],
                    record['device_type'],
                    record['agent_mode'],
                    record['metadata']
                )
            
            logger.info(f"💾 Flushed {len(self.buffer)} learning records to database")
            self.buffer.clear()
            
        except Exception as e:
            logger.error(f"❌ Failed to flush learning data: {e}", exc_info=True)
    
    async def get_learning_data(
        self,
        game_id: Optional[str] = None,
        game_version_id: Optional[str] = None,
        level_identifier: Optional[str] = None,
        is_user_action: Optional[bool] = None,
        learning_mode: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve learning data for training
        
        Args:
            game_id: Filter by game ID
            game_version_id: Filter by game version ID
            level_identifier: Filter by level
            is_user_action: Filter by user vs AI actions
            learning_mode: Filter by learning mode
            limit: Maximum records to return
            offset: Offset for pagination
            
        Returns:
            List of learning data records
        """
        try:
            conditions = []
            params = []
            param_count = 1
            
            if game_id:
                conditions.append(f"game_id = ${param_count}")
                params.append(game_id)
                param_count += 1
                
            if game_version_id:
                conditions.append(f"game_version_id = ${param_count}")
                params.append(game_version_id)
                param_count += 1
                
            if level_identifier:
                conditions.append(f"level_identifier = ${param_count}")
                params.append(level_identifier)
                param_count += 1
                
            if is_user_action is not None:
                conditions.append(f"is_user_action = ${param_count}")
                params.append(is_user_action)
                param_count += 1
                
            if learning_mode:
                conditions.append(f"learning_mode = ${param_count}")
                params.append(learning_mode)
                param_count += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT 
                    id, session_id, game_id, game_version_id, timestamp,
                    screenshot_before_path, screenshot_after_path,
                    action_type, action_params, tap_x, tap_y,
                    is_user_action, learning_mode,
                    game_state, level_identifier, ui_elements, detected_text,
                    reward, success, led_to_progress, led_to_crash,
                    state_features, visual_features,
                    device_type, agent_mode, metadata
                FROM learning_data
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_count}
                OFFSET ${param_count + 1}
            """
            
            params.extend([limit, offset])
            
            rows = await self.db_manager.fetch_all(query, *params)
            
            logger.info(f"📚 Retrieved {len(rows)} learning records (game={game_id}, level={level_identifier})")
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve learning data: {e}", exc_info=True)
            return []
    
    async def get_statistics(
        self,
        game_id: Optional[str] = None,
        game_version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about collected learning data
        
        Args:
            game_id: Filter by game ID
            game_version_id: Filter by game version ID
            
        Returns:
            Dictionary with statistics
        """
        try:
            conditions = []
            params = []
            param_count = 1
            
            if game_id:
                conditions.append(f"game_id = ${param_count}")
                params.append(game_id)
                param_count += 1
                
            if game_version_id:
                conditions.append(f"game_version_id = ${param_count}")
                params.append(game_version_id)
                param_count += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT level_identifier) as unique_levels,
                    SUM(CASE WHEN is_user_action = true THEN 1 ELSE 0 END) as user_actions,
                    SUM(CASE WHEN is_user_action = false THEN 1 ELSE 0 END) as ai_actions,
                    AVG(reward) as avg_reward,
                    SUM(CASE WHEN led_to_progress = true THEN 1 ELSE 0 END) as progress_actions,
                    MIN(timestamp) as earliest_record,
                    MAX(timestamp) as latest_record
                FROM learning_data
                WHERE {where_clause}
            """
            
            row = await self.db_manager.fetch_one(query, *params)
            
            return dict(row) if row else {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get learning statistics: {e}", exc_info=True)
            return {}
    
    def _hash_file(self, file_path: str) -> Optional[str]:
        """Calculate SHA-256 hash of file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.debug(f"Could not hash file {file_path}: {e}")
            return None
