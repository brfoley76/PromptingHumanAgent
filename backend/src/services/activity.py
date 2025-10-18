"""
Activity service for managing multiplication quiz logic.
Handles question sequencing, scoring, and retry logic.
"""
from typing import Dict, List, Optional, Tuple
import json
from ..database.models import ActivityAttempt
from .curriculum import CurriculumService


class MultiplicationActivity:
    """Handles multiplication quiz game logic"""
    
    def __init__(self, module_id: str, num_problems: int = 5):
        """
        Initialize multiplication activity.
        
        Args:
            module_id: Curriculum module ID
            num_problems: Number of problems to present
        """
        self.module_id = module_id
        self.num_problems = num_problems
        
        # Load problems from curriculum
        self.problems = CurriculumService.get_problems(module_id)[:num_problems]
        
        # Track state
        self.current_problem_index = 0
        self.score = 0
        self.attempts_log = []
        self.has_had_retry = {}  # Track if student used retry for each problem
    
    def get_current_problem(self) -> Optional[Dict]:
        """Get the current problem"""
        if self.current_problem_index < len(self.problems):
            return self.problems[self.current_problem_index]
        return None
    
    def get_problem_number(self) -> int:
        """Get current problem number (1-indexed)"""
        return self.current_problem_index + 1
    
    def get_total_problems(self) -> int:
        """Get total number of problems"""
        return len(self.problems)
    
    def check_answer(self, answer: int) -> bool:
        """
        Check if answer is correct for current problem.
        
        Args:
            answer: Student's answer
            
        Returns:
            True if correct, False otherwise
        """
        problem = self.get_current_problem()
        if not problem:
            return False
        
        return answer == problem['answer']
    
    def submit_answer(self, answer: int, is_retry: bool = False) -> Tuple[bool, str]:
        """
        Submit an answer for the current problem.
        
        Args:
            answer: Student's answer
            is_retry: Whether this is a retry attempt
            
        Returns:
            Tuple of (is_correct, feedback_type)
            feedback_type: 'correct', 'incorrect_first', 'incorrect_retry'
        """
        problem = self.get_current_problem()
        if not problem:
            raise ValueError("No current problem")
        
        is_correct = self.check_answer(answer)
        
        # Log the attempt
        attempt_record = {
            'problem_id': problem['id'],
            'expression': problem['expression'],
            'correct_answer': problem['answer'],
            'student_answer': answer,
            'is_correct': is_correct,
            'is_retry': is_retry
        }
        self.attempts_log.append(attempt_record)
        
        # Determine feedback type
        if is_correct:
            if not is_retry:
                self.score += 1
                feedback_type = 'correct'
            else:
                self.score += 1  # Still count it if they get it on retry
                feedback_type = 'correct'
            
            # Mark that they've used their retry for this problem
            self.has_had_retry[problem['id']] = True
            
        else:
            if is_retry:
                feedback_type = 'incorrect_retry'
                # They've exhausted their retry, mark as done
                self.has_had_retry[problem['id']] = True
            else:
                feedback_type = 'incorrect_first'
        
        return is_correct, feedback_type
    
    def can_retry(self) -> bool:
        """Check if student can retry current problem"""
        problem = self.get_current_problem()
        if not problem:
            return False
        return not self.has_had_retry.get(problem['id'], False)
    
    def next_problem(self):
        """Move to next problem"""
        self.current_problem_index += 1
    
    def is_complete(self) -> bool:
        """Check if activity is complete"""
        return self.current_problem_index >= len(self.problems)
    
    def get_score(self) -> Tuple[int, int]:
        """
        Get current score.
        
        Returns:
            Tuple of (score, total)
        """
        return self.score, len(self.problems)
    
    def get_results(self) -> Dict:
        """
        Get final results for database storage.
        
        Returns:
            Results dictionary with score, item_results, etc.
        """
        score, total = self.get_score()
        percentage = (score / total * 100) if total > 0 else 0
        
        # Build item_results for database
        item_results = []
        for attempt in self.attempts_log:
            # Only include final attempt per problem
            problem_id = attempt['problem_id']
            existing = [r for r in item_results if r['problem_id'] == problem_id]
            if not existing or attempt['is_retry']:
                if existing:
                    item_results.remove(existing[0])
                item_results.append({
                    'problem_id': attempt['problem_id'],
                    'expression': attempt['expression'],
                    'correct_answer': attempt['correct_answer'],
                    'student_answer': attempt['student_answer'],
                    'correct': attempt['is_correct'],
                    'used_retry': attempt['is_retry']
                })
        
        return {
            'score': score,
            'total': total,
            'percentage': round(percentage, 1),
            'item_results': item_results,
            'attempts_log': self.attempts_log
        }
    
    def get_tuning_settings(self) -> Dict:
        """Get tuning settings used for this activity"""
        return {
            'difficulty': 'easy',  # Fixed for now, could be adaptive
            'num_problems': self.num_problems,
            'allow_retry': True,
            'retries_per_problem': 1
        }
