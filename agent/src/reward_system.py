"""
Advanced Reward System for Game AI Learning
Provides intelligent reward signals based on multiple factors
"""

import logging
from typing import Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class RewardSystem:
    """
    Intelligent reward calculation for game AI
    Combines multiple signals to provide meaningful learning feedback
    """
    
    def __init__(self):
        # Reward weights
        self.weights = {
            'level_progress': 100.0,
            'screen_change': 10.0,
            'new_discovery': 20.0,
            'stuck_penalty': -15.0,
            'repeat_action_penalty': -5.0,
            'ui_interaction': 5.0,
            'collectible_obtained': 30.0,
            'enemy_defeated': 40.0,
            'death_penalty': -50.0,
            'level_complete': 200.0,
            'game_over': -100.0
        }
        
        # Track recent actions to detect loops
        self.recent_actions = []
        self.max_recent_actions = 10
        
        # Track screen states to detect being stuck
        self.recent_screens = []
        self.max_recent_screens = 5
        
        logger.info("🎯 Advanced Reward System initialized")
    
    def calculate_reward(
        self,
        before_state: Dict,
        action: Dict,
        after_state: Dict,
        vision_analysis: Optional[Dict] = None,
        ocr_data: Optional[Dict] = None
    ) -> float:
        """
        Calculate comprehensive reward for an action
        
        Args:
            before_state: Game state before action
            action: Action that was taken
            after_state: Game state after action
            vision_analysis: Vision AI analysis of outcome
            ocr_data: OCR text detection data
        
        Returns:
            Reward score (can be negative)
        """
        reward = 0.0
        reward_breakdown = {}
        
        # 1. Screen Change Detection
        screen_change_reward = self._reward_screen_change(before_state, after_state)
        reward += screen_change_reward
        reward_breakdown['screen_change'] = screen_change_reward
        
        # 2. Level Progress Detection
        progress_reward = self._reward_progress(before_state, after_state, vision_analysis, ocr_data)
        reward += progress_reward
        reward_breakdown['progress'] = progress_reward
        
        # 3. Stuck Detection Penalty
        stuck_penalty = self._penalty_stuck(after_state)
        reward += stuck_penalty
        reward_breakdown['stuck'] = stuck_penalty
        
        # 4. Repeat Action Penalty
        repeat_penalty = self._penalty_repeat_action(action)
        reward += repeat_penalty
        reward_breakdown['repeat_action'] = repeat_penalty
        
        # 5. UI Interaction Reward
        ui_reward = self._reward_ui_interaction(action, before_state, after_state)
        reward += ui_reward
        reward_breakdown['ui_interaction'] = ui_reward
        
        # 6. Game Event Rewards (from vision analysis)
        if vision_analysis:
            event_reward = self._reward_game_events(vision_analysis)
            reward += event_reward
            reward_breakdown['game_events'] = event_reward
        
        # 7. OCR-based Rewards
        if ocr_data:
            ocr_reward = self._reward_ocr_progress(before_state, after_state, ocr_data)
            reward += ocr_reward
            reward_breakdown['ocr_based'] = ocr_reward
        
        # Log significant rewards/penalties
        if abs(reward) > 20:
            logger.info(f"💰 Reward: {reward:.1f} | Breakdown: {reward_breakdown}")
        
        return reward
    
    def _reward_screen_change(self, before: Dict, after: Dict) -> float:
        """Reward for causing screen to change"""
        before_screenshot = before.get('screenshot_hash')
        after_screenshot = after.get('screenshot_hash')
        
        if before_screenshot and after_screenshot:
            if before_screenshot != after_screenshot:
                return self.weights['screen_change']
        
        # Fallback: check if pixels changed significantly
        diff_percent = after.get('screen_diff_percent', 0)
        if diff_percent > 5.0:
            return self.weights['screen_change'] * (diff_percent / 100.0)
        
        return 0.0
    
    def _reward_progress(
        self,
        before: Dict,
        after: Dict,
        vision_analysis: Optional[Dict],
        ocr_data: Optional[Dict]
    ) -> float:
        """Reward for making progress in the game"""
        reward = 0.0
        
        # Check level number
        before_level = before.get('level', 0)
        after_level = after.get('level', 0)
        
        if after_level > before_level:
            reward += self.weights['level_progress']
            logger.info(f"🎉 Level increased: {before_level} → {after_level}")
        
        # Check score
        before_score = before.get('score', 0)
        after_score = after.get('score', 0)
        
        if after_score > before_score:
            score_increase = after_score - before_score
            reward += min(score_increase / 10.0, 50.0)  # Cap at 50
        
        # Vision AI detected progress
        if vision_analysis:
            if vision_analysis.get('progress_made'):
                reward += 15.0
            
            # Level complete
            if vision_analysis.get('change_type') == 'level_complete':
                reward += self.weights['level_complete']
                logger.info("🏆 LEVEL COMPLETE DETECTED!")
            
            # Game over
            if vision_analysis.get('game_state') == 'lost':
                reward += self.weights['game_over']
                logger.warning("💀 Game Over detected")
        
        # Check progress percentage
        before_progress = before.get('progress_percent', 0)
        after_progress = after.get('progress_percent', 0)
        
        if after_progress > before_progress:
            reward += (after_progress - before_progress) * 2.0
        
        return reward
    
    def _penalty_stuck(self, after_state: Dict) -> float:
        """Penalty for being stuck (same screen repeatedly)"""
        screen_hash = after_state.get('screenshot_hash')
        
        if not screen_hash:
            return 0.0
        
        # Add to recent screens
        self.recent_screens.append(screen_hash)
        if len(self.recent_screens) > self.max_recent_screens:
            self.recent_screens.pop(0)
        
        # Count how many times we've seen this exact screen
        stuck_count = self.recent_screens.count(screen_hash)
        
        if stuck_count >= 3:
            penalty = self.weights['stuck_penalty'] * stuck_count
            logger.warning(f"⚠️  Stuck detected! Same screen {stuck_count} times")
            return penalty
        
        return 0.0
    
    def _penalty_repeat_action(self, action: Dict) -> float:
        """Penalty for repeating same action too much"""
        action_signature = f"{action.get('type')}_{action.get('x')}_{action.get('y')}"
        
        # Add to recent actions
        self.recent_actions.append(action_signature)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions.pop(0)
        
        # Count repeats
        repeat_count = self.recent_actions.count(action_signature)
        
        if repeat_count >= 3:
            penalty = self.weights['repeat_action_penalty'] * repeat_count
            return penalty
        
        return 0.0
    
    def _reward_ui_interaction(
        self,
        action: Dict,
        before: Dict,
        after: Dict
    ) -> float:
        """Reward for interacting with UI elements"""
        # Check if action hit a UI element
        ui_elements_before = before.get('ui_elements', [])
        ui_elements_after = after.get('ui_elements', [])
        
        action_x = action.get('x', 0)
        action_y = action.get('y', 0)
        
        # Check if tap was on a button
        for element in ui_elements_before:
            elem_x = element.get('x', 0)
            elem_y = element.get('y', 0)
            elem_w = element.get('width', 0)
            elem_h = element.get('height', 0)
            
            if (elem_x <= action_x <= elem_x + elem_w and
                elem_y <= action_y <= elem_y + elem_h):
                
                # Hit a UI element!
                if element.get('type') == 'button':
                    return self.weights['ui_interaction']
        
        return 0.0
    
    def _reward_game_events(self, vision_analysis: Dict) -> float:
        """Reward based on game events detected by vision AI"""
        reward = 0.0
        
        game_elements = vision_analysis.get('game_elements', {})
        
        # Collectibles obtained
        collectibles = game_elements.get('collectibles', [])
        if collectibles:
            reward += len(collectibles) * (self.weights['collectible_obtained'] / 5.0)
        
        # Enemies defeated
        enemies = game_elements.get('enemies', [])
        before_enemies = vision_analysis.get('before_enemies', [])
        if len(enemies) < len(before_enemies):
            defeated = len(before_enemies) - len(enemies)
            reward += defeated * self.weights['enemy_defeated']
            logger.info(f"⚔️  Defeated {defeated} enemies!")
        
        # New area discovered
        scene_type = vision_analysis.get('scene_type')
        if scene_type and scene_type != vision_analysis.get('before_scene_type'):
            reward += self.weights['new_discovery']
            logger.info(f"🗺️  Discovered new area: {scene_type}")
        
        return reward
    
    def _reward_ocr_progress(
        self,
        before: Dict,
        after: Dict,
        ocr_data: Dict
    ) -> float:
        """Use OCR text to detect progress"""
        reward = 0.0
        
        current_text = ocr_data.get('text', '').lower()
        before_text = before.get('ocr_text', '').lower()
        
        # Positive indicators
        positive_keywords = [
            'success', 'complete', 'win', 'victory', 'next level',
            'congratulations', 'well done', 'perfect', 'excellent'
        ]
        
        # Negative indicators
        negative_keywords = [
            'fail', 'game over', 'try again', 'defeat', 'lost'
        ]
        
        # Check for positive outcomes
        for keyword in positive_keywords:
            if keyword in current_text and keyword not in before_text:
                reward += 30.0
                logger.info(f"✨ Positive outcome detected: '{keyword}'")
                break
        
        # Check for negative outcomes
        for keyword in negative_keywords:
            if keyword in current_text and keyword not in before_text:
                reward -= 40.0
                logger.warning(f"❌ Negative outcome detected: '{keyword}'")
                break
        
        return reward
    
    def reset_tracking(self):
        """Reset stuck/repeat detection (call when starting new level)"""
        self.recent_actions.clear()
        self.recent_screens.clear()
        logger.info("🔄 Reward tracking reset")
    
    def get_reward_explanation(self, reward: float, breakdown: Dict) -> str:
        """Generate human-readable explanation of reward"""
        if reward > 50:
            return f"Excellent! Major progress made (+{reward:.0f})"
        elif reward > 10:
            return f"Good move (+{reward:.0f})"
        elif reward > 0:
            return f"Small progress (+{reward:.0f})"
        elif reward == 0:
            return "Neutral action (0)"
        elif reward > -10:
            return f"Slight penalty ({reward:.0f})"
        else:
            return f"Poor action ({reward:.0f})"
