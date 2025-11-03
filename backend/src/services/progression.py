"""
Progression Service - Intelligent Activity Sequencing

This service determines the optimal next activity for students based on:
- Bayesian proficiency data
- Completed activities
- Mastery thresholds
- Learning objectives

SECURITY: Server-side only. Returns actionable recommendations, not raw data.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..database.operations import DatabaseOperations
from .bayesian_proficiency import BayesianProficiencyService
from .curriculum import CurriculumService


class ProgressionService:
    """
    Service for determining optimal learning progression paths.
    Orchestrates activity sequencing based on proficiency and mastery.
    """
    
    # Activity sequence for the module
    ACTIVITY_SEQUENCE = [
        'multiple_choice',
        'fill_in_the_blank',
        'spelling',
        'bubble_pop',
        'fluent_reading'
    ]
    
    # Proficiency thresholds for unlocking next activity
    # Based purely on Bayesian mastery metrics - no attempt count requirements
    UNLOCK_THRESHOLDS = {
        'multiple_choice': 0.70,      # 70% module proficiency to unlock fill_in_the_blank
        'fill_in_the_blank': 0.75,    # 75% to unlock spelling
        'spelling': 0.80,              # 80% to unlock bubble_pop
        'bubble_pop': 0.85,            # 85% to unlock fluent_reading
        'fluent_reading': 0.90         # 90% for module completion
    }
    
    @staticmethod
    def get_next_activity(
        student_id: str,
        module_id: str,
        current_activity: Optional[str] = None
    ) -> Dict:
        """
        Determine the next recommended activity for a student.
        
        Args:
            student_id: Student's ID
            module_id: Module identifier
            current_activity: Activity just completed (optional)
            
        Returns:
            Dict with:
                - activity_type: str - Next activity to do
                - reason: str - Why this activity is recommended
                - is_new: bool - Whether this is a new activity
                - progress_percentage: float - Overall module progress
                - unlocked_new: bool - Whether a new activity was just unlocked
        """
        # Get student's progress
        progress = DatabaseOperations.get_student_progress(student_id)
        
        # Get module proficiency
        module_proficiency = BayesianProficiencyService.get_domain_ability(
            student_id, 'reading'  # TODO: Get domain from module
        )
        
        # Determine which activities are unlocked
        unlocked_activities = ProgressionService._get_unlocked_activities(
            student_id, module_id, progress, module_proficiency
        )
        
        # Check if we just unlocked a new activity
        unlocked_new = False
        if current_activity:
            current_index = ProgressionService.ACTIVITY_SEQUENCE.index(current_activity)
            if current_index < len(ProgressionService.ACTIVITY_SEQUENCE) - 1:
                next_in_sequence = ProgressionService.ACTIVITY_SEQUENCE[current_index + 1]
                if next_in_sequence in unlocked_activities:
                    # Check if this is newly unlocked
                    activity_progress = progress.get(next_in_sequence, {})
                    if activity_progress.get('attempts', 0) == 0:
                        unlocked_new = True
        
        # Determine next activity
        next_activity, reason, is_new = ProgressionService._determine_next_activity(
            student_id, module_id, unlocked_activities, progress, current_activity
        )
        
        # Calculate overall progress
        progress_percentage = ProgressionService._calculate_progress(
            unlocked_activities, progress
        )
        
        return {
            'activity_type': next_activity,
            'reason': reason,
            'is_new': is_new,
            'progress_percentage': progress_percentage,
            'unlocked_new': unlocked_new,
            'total_activities': len(ProgressionService.ACTIVITY_SEQUENCE),
            'completed_activities': len([
                a for a in ProgressionService.ACTIVITY_SEQUENCE
                if progress.get(a, {}).get('best_score')
            ])
        }
    
    @staticmethod
    def should_continue_current_activity(
        student_id: str,
        module_id: str,
        activity_type: str
    ) -> Tuple[bool, str]:
        """
        Determine if student should continue with current activity or move on.
        Based on Bayesian proficiency thresholds, not attempt counts.
        
        Args:
            student_id: Student's ID
            module_id: Module identifier
            activity_type: Current activity type
            
        Returns:
            Tuple of (should_continue: bool, reason: str)
        """
        # Get activity history
        attempts = DatabaseOperations.get_student_performance_history(
            student_id, activity_type, limit=5
        )
        
        if not attempts:
            return True, "First attempt - keep practicing!"
        
        # Get recent performance
        recent_scores = [
            (a.score / a.total * 100) if a.total > 0 else 0
            for a in attempts[:3]
        ]
        avg_recent = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        
        # Check if ready to progress based on Bayesian proficiency
        activity_index = ProgressionService.ACTIVITY_SEQUENCE.index(activity_type)
        if activity_index < len(ProgressionService.ACTIVITY_SEQUENCE) - 1:
            next_activity = ProgressionService.ACTIVITY_SEQUENCE[activity_index + 1]
            threshold = ProgressionService.UNLOCK_THRESHOLDS.get(activity_type, 0.75)
            
            meets_threshold = BayesianProficiencyService.check_mastery_threshold(
                student_id, module_id, threshold
            )
            
            if meets_threshold:
                return False, f"Great work! Ready for {next_activity.replace('_', ' ').title()}"
        
        # Check if struggling (consistently low scores)
        if avg_recent < 60:
            return True, "Keep practicing - you're building important skills!"
        
        # Making progress but not yet at threshold
        return True, "You're making progress - keep going to build mastery!"
    
    @staticmethod
    def _get_unlocked_activities(
        student_id: str,
        module_id: str,
        progress: Dict,
        module_proficiency: float
    ) -> List[str]:
        """
        Determine which activities are currently unlocked for the student.
        NEW: Requires completing hard mode with 80%+ score to unlock next activity.
        Once unlocked, activities stay unlocked (mastery doesn't regress).
        """
        unlocked = ['multiple_choice']  # First activity always unlocked
        
        for i, activity in enumerate(ProgressionService.ACTIVITY_SEQUENCE[:-1]):
            # Check if student has completed hard mode with 80%+ score
            mastery = DatabaseOperations.get_activity_mastery(
                student_id, module_id, activity
            )
            
            if mastery and mastery.completed_hard_mode:
                # Student mastered this activity on hard mode - unlock next!
                next_activity = ProgressionService.ACTIVITY_SEQUENCE[i + 1]
                if next_activity not in unlocked:
                    unlocked.append(next_activity)
                    # Persist unlock in database - once unlocked, stays unlocked
                    DatabaseOperations.unlock_exercise(student_id, next_activity, module_id)
            else:
                # Stop unlocking - need to complete hard mode first
                break
        
        return unlocked
    
    @staticmethod
    def _determine_next_activity(
        student_id: str,
        module_id: str,
        unlocked_activities: List[str],
        progress: Dict,
        current_activity: Optional[str]
    ) -> Tuple[str, str, bool]:
        """
        Determine which activity to recommend next.
        
        Returns:
            Tuple of (activity_type, reason, is_new)
        """
        # If just completed an activity, check if should continue or move on
        if current_activity and current_activity in unlocked_activities:
            should_continue, reason = ProgressionService.should_continue_current_activity(
                student_id, module_id, current_activity
            )
            
            if should_continue:
                return current_activity, reason, False
            
            # Ready to move on - find next activity
            current_index = ProgressionService.ACTIVITY_SEQUENCE.index(current_activity)
            if current_index < len(ProgressionService.ACTIVITY_SEQUENCE) - 1:
                next_activity = ProgressionService.ACTIVITY_SEQUENCE[current_index + 1]
                if next_activity in unlocked_activities:
                    return next_activity, f"🎉 {reason}", True
        
        # Find first incomplete activity
        for activity in ProgressionService.ACTIVITY_SEQUENCE:
            if activity in unlocked_activities:
                activity_progress = progress.get(activity, {})
                attempts = activity_progress.get('attempts', 0)
                
                if attempts == 0:
                    # New activity
                    return activity, f"Let's try {activity.replace('_', ' ').title()}!", True
                
                # Check if needs more practice
                best_score = activity_progress.get('best_score', {})
                if best_score:
                    percentage = best_score.get('percentage', 0)
                    if percentage < 85:
                        return activity, "Keep practicing to build mastery!", False
        
        # All unlocked activities mastered - recommend last unlocked
        last_unlocked = unlocked_activities[-1]
        return last_unlocked, "Great progress! Keep practicing to maintain your skills.", False
    
    @staticmethod
    def _calculate_progress(
        unlocked_activities: List[str],
        progress: Dict
    ) -> float:
        """
        Calculate overall module progress percentage.
        """
        total_activities = len(ProgressionService.ACTIVITY_SEQUENCE)
        
        # Count activities with good scores (70%+)
        mastered_count = 0
        for activity in ProgressionService.ACTIVITY_SEQUENCE:
            if activity in unlocked_activities:
                activity_progress = progress.get(activity, {})
                best_score = activity_progress.get('best_score', {})
                if best_score and best_score.get('percentage', 0) >= 70:
                    mastered_count += 1
        
        return (mastered_count / total_activities) * 100
    
    @staticmethod
    def get_activity_display_info(activity_type: str) -> Dict:
        """
        Get display information for an activity.
        
        Returns:
            Dict with name, icon, description
        """
        info = {
            'multiple_choice': {
                'name': 'Word Quiz',
                'icon': '🎯',
                'description': 'Match words with their definitions'
            },
            'fill_in_the_blank': {
                'name': 'Fill It In',
                'icon': '✏️',
                'description': 'Complete sentences with the right words'
            },
            'spelling': {
                'name': 'Spell It',
                'icon': '🔤',
                'description': 'Practice spelling vocabulary words'
            },
            'bubble_pop': {
                'name': 'Bubble Fun',
                'icon': '🫧',
                'description': 'Pop bubbles with correctly spelled words'
            },
            'fluent_reading': {
                'name': 'Read It',
                'icon': '📖',
                'description': 'Practice reading fluency'
            }
        }
        
        return info.get(activity_type, {
            'name': activity_type.replace('_', ' ').title(),
            'icon': '📝',
            'description': 'Learning activity'
        })
