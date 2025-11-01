"""
Bayesian Proficiency Service - Adaptive Learning Intelligence

SECURITY: This service is INTERNAL ONLY. Never expose raw proficiency data to frontend.
All methods return only actionable recommendations, not raw Bayesian parameters.

Uses Beta-Binomial model for Bayesian updating:
- Prior: Beta(α₀, β₀) = Beta(2, 2) - slightly informed prior at 50%
- After n successes and m failures: Beta(α₀+n, β₀+m)
- Mean ability = α / (α + β)
- Confidence increases as α + β increases
"""
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import StudentProficiency, Student
from .curriculum import CurriculumService


class BayesianProficiencyService:
    """
    Service for Bayesian proficiency tracking and adaptive recommendations.
    All methods are server-side only and never expose raw proficiency data.
    """
    
    # Default parameters (can be tuned based on empirical data)
    DEFAULT_PRIOR_ALPHA = 1.0  # Uninformative prior - faster learning
    DEFAULT_PRIOR_BETA = 1.0   # Uninformative prior - faster learning
    DEFAULT_LEARNING_RATE = 0.1
    DEFAULT_FORGETTING_RATE = 0.05  # Per day
    MASTERY_THRESHOLD = 0.85
    SKIP_THRESHOLD = 0.90
    
    @staticmethod
    def initialize_student_proficiencies(
        student_id: str,
        module_id: str,
        domain: str,
        items: List[Dict]
    ) -> None:
        """
        Initialize proficiency records for a student starting a new module.
        Creates domain-level, module-level, and item-level proficiencies.
        
        Args:
            student_id: Student's ID
            module_id: Module identifier (e.g., "r003.1")
            domain: Domain name (e.g., "reading", "math")
            items: List of items with 'word' or 'id' field
        """
        db = next(get_db())
        try:
            proficiencies = []
            
            # Domain-level proficiency
            domain_prof = BayesianProficiencyService._get_or_create_proficiency(
                db, student_id, "domain", domain=domain
            )
            proficiencies.append(domain_prof)
            
            # Module-level proficiency
            module_prof = BayesianProficiencyService._get_or_create_proficiency(
                db, student_id, "module", domain=domain, module_id=module_id
            )
            proficiencies.append(module_prof)
            
            # Item-level proficiencies
            for item in items:
                item_id = item.get('word') or item.get('id')
                if item_id:
                    item_prof = BayesianProficiencyService._get_or_create_proficiency(
                        db, student_id, "item", 
                        domain=domain, module_id=module_id, item_id=item_id
                    )
                    proficiencies.append(item_prof)
            
            db.commit()
        finally:
            db.close()
    
    @staticmethod
    def update_proficiencies(
        student_id: str,
        module_id: str,
        domain: str,
        item_results: List[Dict]
    ) -> None:
        """
        Update all proficiency levels based on activity results.
        Uses Bayesian updating with Beta distribution.
        
        Args:
            student_id: Student's ID
            module_id: Module identifier
            domain: Domain name
            item_results: List of dicts with 'item' and 'correct' fields
        """
        if not item_results:
            return
        
        db = next(get_db())
        try:
            # Count successes and failures
            total_correct = sum(1 for r in item_results if r.get('correct', False))
            total_incorrect = len(item_results) - total_correct
            
            # Update item-level proficiencies
            for result in item_results:
                item_id = result.get('item')
                correct = result.get('correct', False)
                
                if item_id:
                    item_prof = BayesianProficiencyService._get_or_create_proficiency(
                        db, student_id, "item",
                        domain=domain, module_id=module_id, item_id=item_id
                    )
                    
                    # Bayesian update: add evidence
                    if correct:
                        item_prof.alpha += 1
                    else:
                        item_prof.beta += 1
                    
                    # Update derived metrics
                    item_prof.mean_ability = item_prof.alpha / (item_prof.alpha + item_prof.beta)
                    item_prof.confidence = min(1.0, (item_prof.alpha + item_prof.beta) / 20.0)
                    item_prof.sample_count += 1
                    item_prof.last_updated = datetime.utcnow()
            
            # Update module-level proficiency (aggregate)
            module_prof = BayesianProficiencyService._get_or_create_proficiency(
                db, student_id, "module",
                domain=domain, module_id=module_id
            )
            
            # Add evidence to module proficiency
            module_prof.alpha += total_correct
            module_prof.beta += total_incorrect
            module_prof.mean_ability = module_prof.alpha / (module_prof.alpha + module_prof.beta)
            module_prof.confidence = min(1.0, (module_prof.alpha + module_prof.beta) / 50.0)
            module_prof.sample_count += len(item_results)
            module_prof.last_updated = datetime.utcnow()
            
            # Update domain-level proficiency (aggregate)
            domain_prof = BayesianProficiencyService._get_or_create_proficiency(
                db, student_id, "domain", domain=domain
            )
            
            domain_prof.alpha += total_correct
            domain_prof.beta += total_incorrect
            domain_prof.mean_ability = domain_prof.alpha / (domain_prof.alpha + domain_prof.beta)
            domain_prof.confidence = min(1.0, (domain_prof.alpha + domain_prof.beta) / 100.0)
            domain_prof.sample_count += len(item_results)
            domain_prof.last_updated = datetime.utcnow()
            
            db.commit()
        finally:
            db.close()
    
    @staticmethod
    def get_adaptive_recommendations(
        student_id: str,
        module_id: str,
        activity_type: str,
        is_optional: bool = False
    ) -> Dict:
        """
        Get adaptive recommendations for an activity.
        Returns ONLY actionable parameters, never raw proficiency data.
        
        Args:
            student_id: Student's ID
            module_id: Module identifier
            activity_type: Type of activity
            is_optional: Whether this activity is optional/bonus (can be skipped if mastered)
            
        Returns:
            Dict with recommendations: {
                'difficulty': str,
                'num_questions': int,
                'focus_items': List[str],
                'skip_activity': bool,
                'skip_reason': str (if skip_activity is True)
            }
        """
        db = next(get_db())
        try:
            # Get module proficiency
            module_prof = BayesianProficiencyService._get_proficiency(
                db, student_id, "module", module_id=module_id
            )
            
            # Get item proficiencies
            item_profs = db.query(StudentProficiency).filter(
                StudentProficiency.student_id == student_id,
                StudentProficiency.level == "item",
                StudentProficiency.module_id == module_id
            ).all()
            
            # If no history, return default recommendations
            if not module_prof or module_prof.sample_count == 0:
                return {
                    'difficulty': BayesianProficiencyService._get_default_difficulty(activity_type),
                    'num_questions': 10,
                    'focus_items': [],
                    'skip_activity': False
                }
            
            # Apply forgetting decay
            module_ability = BayesianProficiencyService._apply_forgetting(
                module_prof.mean_ability,
                module_prof.last_updated,
                module_prof.forgetting_rate
            )
            
            # Check if should offer skip (only for optional activities)
            if is_optional and module_ability >= BayesianProficiencyService.SKIP_THRESHOLD:
                return {
                    'difficulty': 'skip',
                    'num_questions': 0,
                    'focus_items': [],
                    'skip_activity': True,
                    'skip_reason': "You've mastered this content! This is a bonus activity - skip or play for fun."
                }
            
            # Determine difficulty based on ability
            difficulty = BayesianProficiencyService._ability_to_difficulty(
                module_ability, activity_type
            )
            
            # Determine number of questions (fewer if high ability)
            num_questions = BayesianProficiencyService._calculate_question_count(
                module_ability, module_prof.confidence
            )
            
            # Identify items that need focus (low ability or high uncertainty)
            focus_items = []
            if item_profs:
                # Sort by ability (ascending) and take bottom items
                sorted_items = sorted(
                    item_profs,
                    key=lambda p: BayesianProficiencyService._apply_forgetting(
                        p.mean_ability, p.last_updated, p.forgetting_rate
                    )
                )
                
                # Focus on items below 70% ability
                focus_items = [
                    p.item_id for p in sorted_items
                    if BayesianProficiencyService._apply_forgetting(
                        p.mean_ability, p.last_updated, p.forgetting_rate
                    ) < 0.70
                ][:5]  # Max 5 focus items
            
            return {
                'difficulty': difficulty,
                'num_questions': num_questions,
                'focus_items': focus_items,
                'skip_activity': False
            }
        finally:
            db.close()
    
    @staticmethod
    def check_mastery_threshold(
        student_id: str,
        module_id: str,
        threshold: float = None
    ) -> bool:
        """
        Check if student has reached mastery threshold for a module.
        
        Args:
            student_id: Student's ID
            module_id: Module identifier
            threshold: Mastery threshold (default: 0.85)
            
        Returns:
            True if mastered, False otherwise
        """
        if threshold is None:
            threshold = BayesianProficiencyService.MASTERY_THRESHOLD
        
        db = next(get_db())
        try:
            module_prof = BayesianProficiencyService._get_proficiency(
                db, student_id, "module", module_id=module_id
            )
            
            if not module_prof or module_prof.sample_count < 10:
                return False  # Need minimum sample size
            
            # Apply forgetting decay
            current_ability = BayesianProficiencyService._apply_forgetting(
                module_prof.mean_ability,
                module_prof.last_updated,
                module_prof.forgetting_rate
            )
            
            return current_ability >= threshold
        finally:
            db.close()
    
    @staticmethod
    def get_domain_ability(student_id: str, domain: str) -> float:
        """
        Get general domain ability score for a student.
        Used for personalizing new modules in the same domain.
        
        Args:
            student_id: Student's ID
            domain: Domain name
            
        Returns:
            Domain ability score (0.0 to 1.0)
        """
        db = next(get_db())
        try:
            domain_prof = BayesianProficiencyService._get_proficiency(
                db, student_id, "domain", domain=domain
            )
            
            if not domain_prof or domain_prof.sample_count == 0:
                return 0.5  # Default prior
            
            return BayesianProficiencyService._apply_forgetting(
                domain_prof.mean_ability,
                domain_prof.last_updated,
                domain_prof.forgetting_rate
            )
        finally:
            db.close()
    
    # Internal helper methods
    
    @staticmethod
    def _get_or_create_proficiency(
        db: Session,
        student_id: str,
        level: str,
        domain: str = None,
        module_id: str = None,
        item_id: str = None
    ) -> StudentProficiency:
        """Get existing proficiency or create with priors"""
        query = db.query(StudentProficiency).filter(
            StudentProficiency.student_id == student_id,
            StudentProficiency.level == level
        )
        
        if domain:
            query = query.filter(StudentProficiency.domain == domain)
        if module_id:
            query = query.filter(StudentProficiency.module_id == module_id)
        if item_id:
            query = query.filter(StudentProficiency.item_id == item_id)
        
        prof = query.first()
        
        if not prof:
            prof = StudentProficiency(
                student_id=student_id,
                level=level,
                domain=domain,
                module_id=module_id,
                item_id=item_id,
                alpha=BayesianProficiencyService.DEFAULT_PRIOR_ALPHA,
                beta=BayesianProficiencyService.DEFAULT_PRIOR_BETA,
                mean_ability=0.5,
                confidence=0.5,
                learning_rate=BayesianProficiencyService.DEFAULT_LEARNING_RATE,
                forgetting_rate=BayesianProficiencyService.DEFAULT_FORGETTING_RATE
            )
            db.add(prof)
        
        return prof
    
    @staticmethod
    def _get_proficiency(
        db: Session,
        student_id: str,
        level: str,
        domain: str = None,
        module_id: str = None,
        item_id: str = None
    ) -> Optional[StudentProficiency]:
        """Get existing proficiency (returns None if not found)"""
        query = db.query(StudentProficiency).filter(
            StudentProficiency.student_id == student_id,
            StudentProficiency.level == level
        )
        
        if domain:
            query = query.filter(StudentProficiency.domain == domain)
        if module_id:
            query = query.filter(StudentProficiency.module_id == module_id)
        if item_id:
            query = query.filter(StudentProficiency.item_id == item_id)
        
        return query.first()
    
    @staticmethod
    def _apply_forgetting(
        ability: float,
        last_updated: datetime,
        forgetting_rate: float
    ) -> float:
        """
        Apply exponential forgetting decay.
        Ability gradually reverts toward prior (0.5) over time.
        """
        days_since_update = (datetime.utcnow() - last_updated).days
        
        if days_since_update == 0:
            return ability
        
        # Exponential decay toward prior
        decay_factor = math.exp(-forgetting_rate * days_since_update)
        prior = 0.5
        
        return ability * decay_factor + prior * (1 - decay_factor)
    
    @staticmethod
    def _ability_to_difficulty(ability: float, activity_type: str) -> str:
        """
        Convert ability score to difficulty level.
        Tuned for optimal challenge zone (80-90% accuracy).
        Conservative thresholds to ensure mastery before advancing.
        """
        if activity_type == 'multiple_choice':
            if ability >= 0.80:  # Hard: requires strong proficiency
                return '5'
            elif ability >= 0.65:  # Medium: solid understanding
                return '4'
            else:
                return '3'  # Easy: building foundation
        else:
            if ability >= 0.80:  # Hard: requires strong proficiency
                return 'hard'
            elif ability >= 0.65:  # Medium: solid understanding
                return 'medium'
            else:
                return 'easy'  # Easy: building foundation
    
    @staticmethod
    def _get_default_difficulty(activity_type: str) -> str:
        """Get default difficulty for first attempt"""
        if activity_type == 'multiple_choice':
            return '3'
        else:
            return 'easy'
    
    @staticmethod
    def _calculate_question_count(ability: float, confidence: float) -> int:
        """
        Calculate adaptive question count.
        Fewer questions if high ability and high confidence.
        """
        if ability >= 0.85 and confidence >= 0.8:
            return 5  # Quick check for mastery
        elif ability >= 0.70 and confidence >= 0.6:
            return 7  # Moderate practice
        else:
            return 10  # Full practice
    
    @staticmethod
    def _get_item_difficulty(item_id: str, module_id: str, curriculum: Dict) -> float:
        """
        Get item difficulty from curriculum.
        Returns default 0.5 if not specified.
        """
        try:
            vocab = curriculum.get('content', {}).get('vocabulary', [])
            for item in vocab:
                if item.get('word') == item_id:
                    return item.get('difficulty', 0.5)
        except:
            pass
        
        return 0.5  # Default medium difficulty
