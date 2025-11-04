"""
Retention Estimator - Estimates user retention from gameplay metrics
"""
import json
import logging
from typing import Dict, List
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


class RetentionEstimator:
    """Estimates player retention based on gameplay patterns"""
    
    def __init__(self):
        self.session_data = []
        self.engagement_metrics = {
            'total_playtime': 0,
            'session_count': 0,
            'crash_count': 0,
            'level_completions': 0,
            'difficulty_frustration': 0
        }
        
    def add_session(self, session_data: Dict):
        """Add session data for analysis"""
        self.session_data.append(session_data)
        
        # Update engagement metrics
        self.engagement_metrics['total_playtime'] += session_data.get('duration', 0)
        self.engagement_metrics['session_count'] += 1
        self.engagement_metrics['crash_count'] += session_data.get('crashes', 0)
        self.engagement_metrics['level_completions'] += session_data.get('levels_completed', 0)
    
    def calculate_engagement_score(self) -> float:
        """Calculate overall engagement score (0-1)"""
        if self.engagement_metrics['session_count'] == 0:
            return 0.0
        
        # Positive factors
        avg_session_length = self.engagement_metrics['total_playtime'] / self.engagement_metrics['session_count']
        session_length_score = min(avg_session_length / 1800, 1.0)  # 30 min max
        
        completion_rate = self.engagement_metrics['level_completions'] / max(self.engagement_metrics['session_count'], 1)
        completion_score = min(completion_rate / 5, 1.0)  # 5 levels per session ideal
        
        # Negative factors
        crash_penalty = min(self.engagement_metrics['crash_count'] * 0.1, 0.5)
        
        engagement = (
            0.4 * session_length_score +
            0.4 * completion_score -
            0.2 * crash_penalty
        )
        
        return max(0.0, min(engagement, 1.0))
    
    def estimate_day1_retention(self) -> float:
        """Estimate Day 1 retention rate"""
        engagement = self.calculate_engagement_score()
        
        # Base retention curve (typical mobile game)
        base_d1 = 0.40  # 40% industry average
        
        # Adjust based on engagement
        if engagement > 0.7:
            retention = base_d1 + 0.15  # Strong engagement
        elif engagement > 0.5:
            retention = base_d1 + 0.05  # Good engagement
        elif engagement < 0.3:
            retention = base_d1 - 0.15  # Poor engagement
        else:
            retention = base_d1
        
        # Crash penalty
        if self.engagement_metrics['crash_count'] > 2:
            retention *= 0.8
        
        return max(0.1, min(retention, 0.9))
    
    def estimate_day7_retention(self) -> float:
        """Estimate Day 7 retention rate"""
        d1_retention = self.estimate_day1_retention()
        
        # D7 is typically 15-25% of D1
        engagement = self.calculate_engagement_score()
        
        if engagement > 0.7:
            multiplier = 0.30
        elif engagement > 0.5:
            multiplier = 0.22
        else:
            multiplier = 0.15
        
        return d1_retention * multiplier
    
    def estimate_day30_retention(self) -> float:
        """Estimate Day 30 retention rate"""
        d7_retention = self.estimate_day7_retention()
        
        # D30 is typically 10-15% of D7
        engagement = self.calculate_engagement_score()
        
        if engagement > 0.7:
            multiplier = 0.15
        elif engagement > 0.5:
            multiplier = 0.12
        else:
            multiplier = 0.08
        
        return d7_retention * multiplier
    
    def identify_churn_risks(self) -> List[Dict]:
        """Identify factors that may cause player churn"""
        risks = []
        
        # High crash rate
        if self.engagement_metrics['crash_count'] > 2:
            risks.append({
                'factor': 'High Crash Rate',
                'severity': 'high',
                'description': f"{self.engagement_metrics['crash_count']} crashes detected",
                'impact': 'Reduces retention by ~20-30%'
            })
        
        # Low engagement
        engagement = self.calculate_engagement_score()
        if engagement < 0.3:
            risks.append({
                'factor': 'Low Engagement',
                'severity': 'high',
                'description': 'Players not engaging deeply with content',
                'impact': 'Reduces retention by ~15-25%'
            })
        
        # Short sessions
        if self.engagement_metrics['session_count'] > 0:
            avg_session = self.engagement_metrics['total_playtime'] / self.engagement_metrics['session_count']
            if avg_session < 300:  # Less than 5 minutes
                risks.append({
                    'factor': 'Short Session Length',
                    'severity': 'medium',
                    'description': f'Average session: {avg_session/60:.1f} minutes',
                    'impact': 'Reduces retention by ~10-15%'
                })
        
        # Low completion rate
        if self.engagement_metrics['level_completions'] < 2:
            risks.append({
                'factor': 'Low Level Completion',
                'severity': 'medium',
                'description': 'Players not progressing through levels',
                'impact': 'Reduces retention by ~10-20%'
            })
        
        return risks
    
    def get_retention_estimate(self) -> Dict:
        """Generate comprehensive retention estimate"""
        d1 = self.estimate_day1_retention()
        d7 = self.estimate_day7_retention()
        d30 = self.estimate_day30_retention()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'engagement_score': self.calculate_engagement_score(),
            'retention_estimates': {
                'day_1': {
                    'rate': d1,
                    'percentage': f"{d1*100:.1f}%",
                    'confidence': 'medium'
                },
                'day_7': {
                    'rate': d7,
                    'percentage': f"{d7*100:.1f}%",
                    'confidence': 'low'
                },
                'day_30': {
                    'rate': d30,
                    'percentage': f"{d30*100:.1f}%",
                    'confidence': 'low'
                }
            },
            'churn_risks': self.identify_churn_risks(),
            'recommendations': self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations to improve retention"""
        recommendations = []
        
        engagement = self.calculate_engagement_score()
        
        if engagement < 0.4:
            recommendations.append("Improve early game experience and tutorial")
            recommendations.append("Add more rewarding progression mechanics")
        
        if self.engagement_metrics['crash_count'] > 1:
            recommendations.append("Fix critical stability issues immediately")
        
        if self.engagement_metrics['level_completions'] < 3:
            recommendations.append("Adjust difficulty curve for early levels")
            recommendations.append("Add more guidance and hints")
        
        if not recommendations:
            recommendations.append("Continue monitoring player behavior")
            recommendations.append("A/B test new features to improve engagement")
        
        return recommendations
    
    def save_report(self, output_path: str):
        """Save retention estimate to file"""
        try:
            report = self.get_retention_estimate()
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Retention report saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving retention report: {e}")
