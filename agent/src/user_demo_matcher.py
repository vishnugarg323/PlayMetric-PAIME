"""
User Demonstration Matcher
Intelligently finds and uses similar user demonstrations for AI learning
"""

import logging
import numpy as np
from typing import Dict, List, Optional
import asyncio
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class UserDemonstrationMatcher:
    """
    Finds similar user demonstrations based on screen state similarity
    Uses feature embeddings for intelligent matching
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cached_demonstrations = []
        self.cache_expiry = 300  # 5 minutes
        self.last_cache_update = 0
        
        logger.info("🎓 User Demonstration Matcher initialized")
    
    async def find_similar_demonstrations(
        self,
        current_screen_features: Dict,
        game_id: str,
        similarity_threshold: float = 0.75,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find user demonstrations similar to current screen state
        
        Args:
            current_screen_features: Features extracted from current screen
            game_id: Game ID to search within
            similarity_threshold: Minimum similarity score (0-1)
            limit: Max number of demonstrations to return
        
        Returns:
            List of similar demonstrations with similarity scores
        """
        try:
            # Get all user demonstrations for this game
            demonstrations = await self._get_user_demonstrations(game_id)
            
            if not demonstrations:
                logger.debug("No user demonstrations found")
                return []
            
            # Extract features from current screen
            current_features = self._extract_features(current_screen_features)
            
            # Calculate similarity for each demonstration
            scored_demos = []
            for demo in demonstrations:
                demo_features = self._extract_features(demo.get('screen_analysis', {}))
                similarity = self._calculate_similarity(current_features, demo_features)
                
                if similarity >= similarity_threshold:
                    scored_demos.append({
                        **demo,
                        'similarity_score': similarity
                    })
            
            # Sort by similarity (highest first)
            scored_demos.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Return top N
            top_demos = scored_demos[:limit]
            
            if top_demos:
                logger.info(f"📚 Found {len(top_demos)} similar user demonstrations (similarity > {similarity_threshold})")
                for demo in top_demos[:3]:  # Log top 3
                    logger.debug(f"  - Demo with {demo['similarity_score']:.2f} similarity: {demo.get('user_action', {}).get('type')}")
            
            return top_demos
            
        except Exception as e:
            logger.error(f"Failed to find similar demonstrations: {e}")
            return []
    
    async def _get_user_demonstrations(self, game_id: str) -> List[Dict]:
        """Get all user demonstrations for a game (with caching)"""
        import time
        
        current_time = time.time()
        
        # Check cache
        if (current_time - self.last_cache_update < self.cache_expiry and
            self.cached_demonstrations):
            return self.cached_demonstrations
        
        # Fetch from database
        query = """
            SELECT 
                id, session_id, timestamp,
                user_action, screen_analysis,
                outcome, led_to_progress,
                reward_score
            FROM user_gameplay_observations
            WHERE game_id = $1
            AND led_to_progress = true
            AND outcome = 'success'
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        try:
            results = await self.db_manager.execute(query, game_id)
            self.cached_demonstrations = [dict(row) for row in results]
            self.last_cache_update = current_time
            
            logger.info(f"📖 Loaded {len(self.cached_demonstrations)} user demonstrations from database")
            return self.cached_demonstrations
            
        except Exception as e:
            logger.error(f"Failed to load user demonstrations: {e}")
            return []
    
    def _extract_features(self, screen_data: Dict) -> np.ndarray:
        """
        Extract feature vector from screen data for similarity comparison
        
        Features include:
        - OCR text (TF-IDF or embedding)
        - UI element count and types
        - Screen layout hash
        - Color histogram
        - Visual elements presence
        """
        features = []
        
        # 1. UI Elements Features
        ui_elements = screen_data.get('ui_elements', [])
        features.append(len(ui_elements))  # Total UI elements
        
        # Count by type
        button_count = sum(1 for e in ui_elements if e.get('type') == 'button')
        text_count = sum(1 for e in ui_elements if e.get('type') == 'text')
        icon_count = sum(1 for e in ui_elements if e.get('type') == 'icon')
        
        features.extend([button_count, text_count, icon_count])
        
        # 2. OCR Text Features (simple word count for now)
        ocr_text = screen_data.get('ocr_text', '').lower()
        word_count = len(ocr_text.split())
        features.append(word_count)
        
        # Key game words presence
        game_keywords = ['level', 'score', 'play', 'start', 'menu', 'pause', 'win', 'lose']
        for keyword in game_keywords:
            features.append(1.0 if keyword in ocr_text else 0.0)
        
        # 3. Screen Stability
        screen_stability = screen_data.get('screen_stability', 0.5)
        features.append(screen_stability)
        
        # 4. Visual Features (if available)
        avg_ui_elements = screen_data.get('avg_ui_elements', 0)
        features.append(avg_ui_elements)
        
        # 5. Scene Type (one-hot encoding)
        scene_type = screen_data.get('scene_type', 'unknown')
        scene_types = ['gameplay', 'menu', 'level_selection', 'dialog', 'loading', 'unknown']
        for stype in scene_types:
            features.append(1.0 if scene_type == stype else 0.0)
        
        return np.array(features, dtype=np.float32)
    
    def _calculate_similarity(
        self,
        features1: np.ndarray,
        features2: np.ndarray
    ) -> float:
        """Calculate cosine similarity between feature vectors"""
        try:
            # Ensure same length
            max_len = max(len(features1), len(features2))
            features1 = np.pad(features1, (0, max_len - len(features1)))
            features2 = np.pad(features2, (0, max_len - len(features2)))
            
            # Calculate cosine similarity
            similarity = cosine_similarity(
                features1.reshape(1, -1),
                features2.reshape(1, -1)
            )[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    async def get_best_action_for_state(
        self,
        current_screen_features: Dict,
        game_id: str
    ) -> Optional[Dict]:
        """
        Get the best action to take based on similar user demonstrations
        
        Returns:
            Action dict with confidence score, or None if no good match
        """
        similar_demos = await self.find_similar_demonstrations(
            current_screen_features,
            game_id,
            similarity_threshold=0.7,
            limit=10
        )
        
        if not similar_demos:
            return None
        
        # Weight demonstrations by similarity and success
        weighted_actions = {}
        
        for demo in similar_demos:
            action = demo.get('user_action', {})
            action_key = f"{action.get('type')}_{action.get('x')}_{action.get('y')}"
            
            similarity = demo.get('similarity_score', 0)
            led_to_progress = demo.get('led_to_progress', False)
            reward = demo.get('reward_score', 0)
            
            # Calculate weight
            weight = similarity
            if led_to_progress:
                weight *= 1.5
            if reward > 0:
                weight *= (1 + reward / 100.0)
            
            if action_key in weighted_actions:
                weighted_actions[action_key]['weight'] += weight
                weighted_actions[action_key]['count'] += 1
            else:
                weighted_actions[action_key] = {
                    'action': action,
                    'weight': weight,
                    'count': 1,
                    'avg_similarity': similarity
                }
        
        if not weighted_actions:
            return None
        
        # Get best action
        best_action_key = max(weighted_actions.keys(), key=lambda k: weighted_actions[k]['weight'])
        best = weighted_actions[best_action_key]
        
        # Calculate confidence
        total_weight = sum(a['weight'] for a in weighted_actions.values())
        confidence = best['weight'] / total_weight if total_weight > 0 else 0.5
        
        logger.info(f"🎯 Best user-learned action: {best['action'].get('type')} "
                   f"(confidence: {confidence:.2f}, seen {best['count']} times)")
        
        return {
            **best['action'],
            'confidence': confidence,
            'source': 'user_demonstration',
            'similar_demo_count': len(similar_demos)
        }
    
    async def store_action_outcome(
        self,
        session_id: str,
        game_id: str,
        user_action: Dict,
        screen_before: Dict,
        screen_after: Dict,
        outcome: str,
        led_to_progress: bool,
        reward_score: float
    ):
        """Store a user action outcome for future learning"""
        try:
            query = """
                INSERT INTO user_gameplay_observations (
                    session_id, game_id, timestamp,
                    user_action, screen_analysis,
                    outcome, led_to_progress, reward_score
                ) VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7)
            """
            
            import json
            await self.db_manager.execute_write(
                query,
                session_id,
                game_id,
                json.dumps(user_action),
                json.dumps(screen_before),
                outcome,
                led_to_progress,
                reward_score
            )
            
            # Invalidate cache
            self.last_cache_update = 0
            
        except Exception as e:
            logger.error(f"Failed to store action outcome: {e}")
    
    def clear_cache(self):
        """Clear cached demonstrations (call when new data added)"""
        self.cached_demonstrations = []
        self.last_cache_update = 0
