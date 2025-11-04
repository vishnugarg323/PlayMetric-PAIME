"""
Difficulty Analyzer - Analyzes game difficulty from gameplay data
"""
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import cv2
import pytesseract
import numpy as np

logger = logging.getLogger(__name__)


class DifficultyAnalyzer:
    """Analyzes level difficulty from gameplay"""
    
    def __init__(self, screenshots_dir: str = "/data/screenshots"):
        self.screenshots_dir = screenshots_dir
        self.level_data = defaultdict(lambda: {
            'attempts': 0,
            'failures': 0,
            'time_spent': 0,
            'screenshots': []
        })
        self.current_level = None
        
    def detect_level_from_screenshot(self, screenshot_path: str) -> Optional[str]:
        """Detect level number from screenshot using OCR"""
        try:
            if not os.path.exists(screenshot_path):
                return None
            
            img = cv2.imread(screenshot_path)
            if img is None:
                return None
            
            # Focus on top portion (where level indicators usually are)
            height, width = img.shape[:2]
            top_region = img[0:int(height*0.2), :]
            
            # Convert to grayscale
            gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)
            
            # OCR
            text = pytesseract.image_to_string(gray, config='--psm 6')
            
            # Look for level indicators
            level_keywords = os.getenv('LEVEL_KEYWORDS', 'Level,Stage,Round,Wave').split(',')
            
            for keyword in level_keywords:
                if keyword.lower() in text.lower():
                    # Extract number after keyword
                    import re
                    match = re.search(rf'{keyword}\s*(\d+)', text, re.IGNORECASE)
                    if match:
                        level_num = match.group(1)
                        return f"{keyword}_{level_num}"
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting level: {e}")
            return None
    
    def track_level_attempt(self, level: str, success: bool, time_spent: float):
        """Track a level attempt"""
        self.level_data[level]['attempts'] += 1
        if not success:
            self.level_data[level]['failures'] += 1
        self.level_data[level]['time_spent'] += time_spent
        
        logger.info(f"Level {level}: attempt recorded (success={success})")
    
    def calculate_difficulty_score(self, level: str) -> float:
        """Calculate difficulty score for a level (0-1, higher = harder)"""
        data = self.level_data.get(level)
        if not data or data['attempts'] == 0:
            return 0.5  # Unknown difficulty
        
        # Factors:
        # 1. Failure rate (weight: 0.5)
        failure_rate = data['failures'] / data['attempts']
        
        # 2. Average time per attempt (weight: 0.3)
        avg_time = data['time_spent'] / data['attempts']
        time_score = min(avg_time / 300, 1.0)  # Normalize to 5 minutes
        
        # 3. Number of retries (weight: 0.2)
        retry_score = min(data['attempts'] / 10, 1.0)  # Normalize to 10 attempts
        
        difficulty = (
            0.5 * failure_rate +
            0.3 * time_score +
            0.2 * retry_score
        )
        
        return min(difficulty, 1.0)
    
    def get_difficulty_report(self) -> Dict:
        """Generate difficulty report for all levels"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_levels': len(self.level_data),
            'levels': {}
        }
        
        for level, data in self.level_data.items():
            difficulty_score = self.calculate_difficulty_score(level)
            
            # Classify difficulty
            if difficulty_score < 0.3:
                difficulty_label = "Easy"
            elif difficulty_score < 0.6:
                difficulty_label = "Medium"
            else:
                difficulty_label = "Hard"
            
            report['levels'][level] = {
                'attempts': data['attempts'],
                'failures': data['failures'],
                'success_rate': 1 - (data['failures'] / max(data['attempts'], 1)),
                'total_time': data['time_spent'],
                'avg_time_per_attempt': data['time_spent'] / max(data['attempts'], 1),
                'difficulty_score': difficulty_score,
                'difficulty_label': difficulty_label
            }
        
        # Find hardest levels
        sorted_levels = sorted(
            report['levels'].items(),
            key=lambda x: x[1]['difficulty_score'],
            reverse=True
        )
        report['hardest_levels'] = [
            {'level': level, 'score': data['difficulty_score']}
            for level, data in sorted_levels[:5]
        ]
        
        return report
    
    def save_report(self, output_path: str):
        """Save difficulty report to file"""
        try:
            report = self.get_difficulty_report()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Difficulty report saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving difficulty report: {e}")
