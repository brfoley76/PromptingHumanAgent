"""
REST API routes for session and activity management.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database.operations import DatabaseOperations
from ..services.curriculum import CurriculumService
from ..services.bayesian_proficiency import BayesianProficiencyService
from ..services.progression import ProgressionService
from ..agents.agent_factory import AgentFactory

router = APIRouter()


# Request/Response Models
class SessionInitRequest(BaseModel):
    """Request to initialize a new session"""
    username: str  # Username is now required
    module_id: str = "r003.1"


class SessionInitResponse(BaseModel):
    """Response from session initialization"""
    session_id: str
    student_id: str
    student_name: str
    module_id: str
    available_activities: List[str]
    tutor_greeting: str
    curriculum_module: Dict[str, Any]
    progress: Dict[str, Any]  # Student's progress data
    is_returning_student: bool
    student_context: Optional[Dict[str, Any]] = None  # Activity history + proficiency for LLM


class ActivityStartRequest(BaseModel):
    """Request to start an activity"""
    session_id: str
    activity_type: str


class ActivityStartResponse(BaseModel):
    """Response from activity start"""
    activity_type: str
    recommended_tuning: Dict[str, Any]
    agent_intro: str
    vocabulary_focus: Optional[List[str]] = None


class ActivityEndRequest(BaseModel):
    """Request to end an activity"""
    session_id: str
    activity_type: str
    results: Dict[str, Any]
    tuning_settings: Dict[str, Any]


class ActivityEndResponse(BaseModel):
    """Response from activity end"""
    feedback: str
    profile_update: Dict[str, Any]
    next_recommendation: Dict[str, Any]
    unlocked_activities: List[str]


class SessionEndRequest(BaseModel):
    """Request to end a session"""
    session_id: str


class NextActivityRequest(BaseModel):
    """Request to get next recommended activity"""
    session_id: str
    current_activity: Optional[str] = None


class NextActivityResponse(BaseModel):
    """Response with next activity recommendation"""
    activity_type: str
    reason: str
    is_new: bool
    progress_percentage: float
    unlocked_new: bool
    total_activities: int
    completed_activities: int
    display_info: Dict[str, Any]


# Routes
@router.post("/session/init", response_model=SessionInitResponse)
async def initialize_session(request: SessionInitRequest):
    """
    Initialize a new learning session using username.
    Finds existing student or creates new one, loads their progress.
    """
    try:
        # Validate username (alphanumeric only)
        if not request.username or not request.username.isalnum():
            raise HTTPException(
                status_code=400, 
                detail="Username must contain only letters and numbers"
            )
        
        # Get or create student by username
        existing_student = DatabaseOperations.get_student_by_name(request.username)
        is_returning = existing_student is not None
        
        student = DatabaseOperations.create_or_get_student(request.username)
        
        # Create session
        session = DatabaseOperations.create_session(student.student_id, request.module_id)
        
        # Load curriculum
        try:
            curriculum = CurriculumService.load_curriculum(request.module_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, 
                detail=f"Curriculum module '{request.module_id}' not found"
            )
        
        # Get available activities from curriculum
        available_activities = curriculum.get('exercises', [])
        
        # Initialize Bayesian proficiencies for new students
        if not is_returning:
            vocab = curriculum.get('content', {}).get('vocabulary', [])
            domain = curriculum.get('subject', 'reading')
            BayesianProficiencyService.initialize_student_proficiencies(
                student.student_id,
                request.module_id,
                domain,
                vocab
            )
        
        # Get student's progress
        progress = DatabaseOperations.get_student_progress(student.student_id)
        
        # Build comprehensive student context for LLM (only for returning students)
        student_context = None
        if is_returning:
            student_context = _build_student_context(student.student_id, request.module_id, progress)
        
        # Build activity state for tutor agent
        unlocked_activities = []
        for activity, data in progress.items():
            if data.get('unlocked', False):
                unlocked_activities.append(activity)
        
        activity_state = {
            'available': available_activities,
            'unlocked': unlocked_activities if unlocked_activities else [available_activities[0]] if available_activities else []
        }
        
        # Get tutor agent greeting with activity state context and student history
        agent = AgentFactory.create_tutor_agent(
            student.name, 
            request.module_id, 
            activity_state=activity_state,
            student_context=student_context
        )
        tutor_greeting = agent.get_welcome_message()
        
        return SessionInitResponse(
            session_id=session.session_id,
            student_id=student.student_id,
            student_name=student.name,
            module_id=request.module_id,
            available_activities=available_activities,
            tutor_greeting=tutor_greeting,
            curriculum_module=curriculum,
            progress=progress,
            is_returning_student=is_returning,
            student_context=student_context
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")


@router.post("/session/end")
async def end_session(request: SessionEndRequest):
    """End a learning session"""
    try:
        session = DatabaseOperations.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        DatabaseOperations.end_session(request.session_id)
        
        return {
            "status": "success",
            "message": "Session ended",
            "session_id": request.session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.post("/progression/next", response_model=NextActivityResponse)
async def get_next_activity(request: NextActivityRequest):
    """
    Get the next recommended activity based on student's progress and proficiency.
    Uses ProgressionService to intelligently determine optimal learning path.
    """
    try:
        # Verify session exists
        session = DatabaseOperations.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get next activity recommendation from ProgressionService
        recommendation = ProgressionService.get_next_activity(
            session.student_id,
            session.module_id,
            request.current_activity
        )
        
        # Get display info for the recommended activity
        display_info = ProgressionService.get_activity_display_info(
            recommendation['activity_type']
        )
        
        return NextActivityResponse(
            activity_type=recommendation['activity_type'],
            reason=recommendation['reason'],
            is_new=recommendation['is_new'],
            progress_percentage=recommendation['progress_percentage'],
            unlocked_new=recommendation['unlocked_new'],
            total_activities=recommendation['total_activities'],
            completed_activities=recommendation['completed_activities'],
            display_info=display_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get next activity: {str(e)}")


@router.post("/activity/start", response_model=ActivityStartResponse)
async def start_activity(request: ActivityStartRequest):
    """
    Start an activity and get Bayesian-based adaptive recommendations.
    """
    try:
        # Verify session exists
        session = DatabaseOperations.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if activity is optional
        curriculum = CurriculumService.load_curriculum(session.module_id)
        optional_exercises = curriculum.get('optional_exercises', [])
        is_optional = request.activity_type in optional_exercises
        
        # Get Bayesian adaptive recommendations
        recommendations = BayesianProficiencyService.get_adaptive_recommendations(
            session.student_id,
            session.module_id,
            request.activity_type,
            is_optional=is_optional
        )
        
        # Check if should skip activity (only for optional activities)
        if recommendations.get('skip_activity', False):
            skip_reason = recommendations.get('skip_reason', 'This is a bonus activity!')
            return ActivityStartResponse(
                activity_type=request.activity_type,
                recommended_tuning={
                    'difficulty': 'skip',
                    'skip': True,
                    'is_optional': True
                },
                agent_intro=skip_reason,
                vocabulary_focus=[]
            )
        
        # Build recommended tuning from Bayesian recommendations
        recommended_tuning = _build_tuning_from_recommendations(
            request.activity_type,
            recommendations
        )
        
        # Get agent intro message
        agent = AgentFactory.create_activity_agent(session.student_id, session.module_id)
        agent_intro = agent.get_activity_intro(
            request.activity_type,
            recommended_tuning.get('difficulty', 'medium')
        )
        
        # Use Bayesian focus items if available, otherwise use defaults
        vocabulary_focus = recommendations.get('focus_items', [])
        if not vocabulary_focus and request.activity_type in ['multiple_choice', 'spelling', 'fill_in_the_blank']:
            curriculum = CurriculumService.load_curriculum(session.module_id)
            vocab = curriculum.get('content', {}).get('vocabulary', [])
            vocabulary_focus = [v['word'] for v in vocab[:5]]
        
        return ActivityStartResponse(
            activity_type=request.activity_type,
            recommended_tuning=recommended_tuning,
            agent_intro=agent_intro,
            vocabulary_focus=vocabulary_focus
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start activity: {str(e)}")


@router.post("/activity/end", response_model=ActivityEndResponse)
async def end_activity(request: ActivityEndRequest):
    """
    End an activity and record results.
    Returns feedback and next recommendations.
    """
    try:
        # Verify session exists
        session = DatabaseOperations.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Record the activity attempt
        attempt = DatabaseOperations.record_activity_attempt(
            session_id=request.session_id,
            student_id=session.student_id,
            module_id=session.module_id,
            activity_type=request.activity_type,
            score=request.results.get('score', 0),
            total=request.results.get('total', 0),
            difficulty=request.tuning_settings.get('difficulty', 'medium'),
            tuning_settings=request.tuning_settings,
            item_results=request.results.get('item_results', [])
        )
        
        # Update Bayesian proficiencies with new evidence
        curriculum = CurriculumService.load_curriculum(session.module_id)
        domain = curriculum.get('subject', 'reading')
        BayesianProficiencyService.update_proficiencies(
            student_id=session.student_id,
            module_id=session.module_id,
            domain=domain,
            item_results=request.results.get('item_results', [])
        )
        
        # Calculate percentage
        percentage = (request.results['score'] / request.results['total'] * 100) if request.results['total'] > 0 else 0
        
        # Get agent feedback
        agent = AgentFactory.create_activity_agent(session.student_id, session.module_id)
        feedback = agent.get_activity_feedback(
            request.activity_type,
            request.results['score'],
            request.results['total'],
            percentage
        )
        
        # Check for unlocks using Bayesian mastery threshold
        unlocked = []
        module_mastered = BayesianProficiencyService.check_mastery_threshold(
            session.student_id,
            session.module_id,
            threshold=0.85
        )
        
        if module_mastered or (percentage >= 80 and _is_hard_difficulty(request.activity_type, request.tuning_settings.get('difficulty'))):
            next_activity = _get_next_activity(request.activity_type)
            if next_activity:
                DatabaseOperations.unlock_exercise(session.student_id, next_activity, session.module_id)
                unlocked.append(next_activity)
        
        # Get next recommendation
        next_recommendation = _get_next_recommendation(
            session.student_id,
            request.activity_type,
            percentage,
            unlocked
        )
        
        return ActivityEndResponse(
            feedback=feedback,
            profile_update={
                "overall_accuracy": percentage,
                "attempts": attempt.attempt_id
            },
            next_recommendation=next_recommendation,
            unlocked_activities=unlocked
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end activity: {str(e)}")


# Helper functions
def _build_student_context(student_id: str, module_id: str, progress: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build comprehensive student context for LLM awareness.
    Includes activity history, proficiency summary, pedagogical guidance, and overall stats.
    """
    print(f"\n{'='*60}")
    print(f"[CONTEXT] Building student context for: {student_id}")
    print(f"[CONTEXT] Module: {module_id}")
    print(f"[CONTEXT] Progress keys: {list(progress.keys())}")
    print(f"{'='*60}\n")
    
    context = {
        'module_info': {},
        'learning_progress': {},
        'progress_summary': {},
        'recent_activity': {},
        'proficiency_summary': {},
        'problem_words': [],
        'question_guidelines': {},
        'overall_stats': {}
    }
    
    # Load curriculum for module info
    try:
        print("[CONTEXT] Loading curriculum...")
        curriculum = CurriculumService.load_curriculum(module_id)
        print(f"[CONTEXT] Curriculum loaded successfully, type: {type(curriculum)}")
        print(f"[CONTEXT] Curriculum keys: {list(curriculum.keys()) if isinstance(curriculum, dict) else 'not a dict'}")
        
        # 1. Module pedagogical information
        goals = curriculum.get('goals', '')
        subject = curriculum.get('subject', 'reading')
        print(f"[CONTEXT] Extracted - goals: {goals[:50]}..., subject: {subject}")
        
        context['module_info'] = {
            'goals': goals,
            'subject': subject,
            'teaching_strategies': [
                'phonics',
                'rhyming', 
                'close pairs (e.g., money vs monkey)',
                'starting letters',
                'multiple meanings'
            ],
            'word_pairs': [
                'ship-shape',
                'money-monkey', 
                'deck-dock',
                'cat-rat',
                'pirate-parrot'
            ]
        }
        print(f"[CONTEXT] ✓ Module info loaded: {context['module_info']['subject']}")
    except Exception as e:
        print(f"[CONTEXT] ✗ Module info failed with exception: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[CONTEXT] Traceback:\n{traceback.format_exc()}")
        context['module_info'] = {'available': False}
    
    # 2. Learning progress and question guidelines
    # Determine current learning stage based on unlocked activities
    unlocked_activities = [act for act, data in progress.items() if data.get('unlocked', False)]
    spelling_unlocked = 'spelling' in unlocked_activities
    
    context['learning_progress'] = {
        'unlocked_activities': unlocked_activities,
        'spelling_introduced': spelling_unlocked,
        'current_stage': 'early' if not spelling_unlocked else 'advanced'
    }
    
    # Question format guidelines based on learning stage
    context['question_guidelines'] = {
        'format': 'single word answers preferred',
        'early_stage_guidance': 'Use A/B multiple choice format - student has not practiced spelling yet',
        'advanced_stage_guidance': 'Can ask for typed single words - student has practiced spelling',
        'example_early': 'Does cat rhyme with: A) rat, or B) basket?',
        'example_advanced': 'What word rhymes with cat?'
    }
    
    # 3. Progress summary from the progress dict
    for activity, data in progress.items():
        if data.get('best_score'):
            context['progress_summary'][activity] = {
                'completed': True,
                'best_percentage': data['best_score']['percentage'],
                'attempts': data.get('attempts', 0),
                'highest_difficulty': data.get('highest_difficulty', 'unknown')
            }
        elif data.get('unlocked'):
            context['progress_summary'][activity] = {
                'completed': False,
                'unlocked': True,
                'attempts': 0
            }
    
    # 2. Get recent activity attempts (last 3 per activity)
    activity_types = ['multiple_choice', 'fill_in_the_blank', 'spelling', 'bubble_pop', 'fluent_reading']
    for activity_type in activity_types:
        recent = DatabaseOperations.get_student_performance_history(student_id, activity_type, limit=3)
        if recent:
            context['recent_activity'][activity_type] = [
                {
                    'score': attempt.score,
                    'total': attempt.total,
                    'percentage': round((attempt.score / attempt.total * 100) if attempt.total > 0 else 0, 1),
                    'difficulty': attempt.difficulty,
                    'date': attempt.date.isoformat() if attempt.date else None
                }
                for attempt in recent
            ]
    
    # 3. Get proficiency summary (aggregated, not raw alpha/beta)
    try:
        proficiencies = DatabaseOperations.get_student_proficiencies(
            student_id, 
            level='item',
            module_id=module_id
        )
        
        if proficiencies:
            # Calculate average proficiency and identify weak/strong areas
            total_ability = sum(p.mean_ability for p in proficiencies)
            avg_ability = total_ability / len(proficiencies) if proficiencies else 0.5
            
            # Find items needing work (below 0.6) and mastered items (above 0.8)
            needs_work = [p.item_id for p in proficiencies if p.mean_ability < 0.6]
            mastered = [p.item_id for p in proficiencies if p.mean_ability > 0.8]
            
            context['proficiency_summary'] = {
                'average_ability': round(avg_ability, 2),
                'total_items': len(proficiencies),
                'mastered_count': len(mastered),
                'needs_work_count': len(needs_work),
                'mastered_items': mastered[:5],  # Top 5
                'needs_work_items': needs_work[:5]  # Bottom 5
            }
            
            # Extract problem words for targeted practice
            context['problem_words'] = needs_work[:5] if needs_work else []
    except Exception as e:
        # If proficiency data not available, skip it
        context['proficiency_summary'] = {'available': False}
        context['problem_words'] = []
    
    # 4. Get overall stats
    try:
        stats = DatabaseOperations.get_student_stats(student_id)
        context['overall_stats'] = {
            'total_attempts': stats.get('total_attempts', 0),
            'average_score': stats.get('average_score', 0),
            'activities_tried': len(stats.get('activity_breakdown', {}))
        }
        print(f"[CONTEXT] ✓ Overall stats loaded: {context['overall_stats']['total_attempts']} attempts")
    except Exception as e:
        print(f"[CONTEXT] ✗ Overall stats failed: {e}")
        context['overall_stats'] = {'available': False}
    
    print(f"\n[CONTEXT] ===== CONTEXT BUILD COMPLETE =====")
    print(f"[CONTEXT] Sections populated: {[k for k, v in context.items() if v]}")
    print(f"[CONTEXT] Returning context with {len(context)} sections")
    print(f"{'='*60}\n")
    
    return context


def _get_activity_display_name(activity_type: str) -> str:
    """Get child-friendly display name for activity"""
    names = {
        'multiple_choice': 'Word Quiz',
        'fill_in_the_blank': 'Fill It In',
        'spelling': 'Spell It',
        'bubble_pop': 'Bubble Fun',
        'fluent_reading': 'Read It'
    }
    return names.get(activity_type, activity_type.replace('_', ' ').title())


def _get_activity_icon(activity_type: str) -> str:
    """Get emoji icon for activity"""
    icons = {
        'multiple_choice': '🎯',
        'fill_in_the_blank': '✏️',
        'spelling': '🔤',
        'bubble_pop': '🫧',
        'fluent_reading': '📖'
    }
    return icons.get(activity_type, '📝')


def _build_tuning_from_recommendations(activity_type: str, recommendations: Dict) -> Dict[str, Any]:
    """Build activity-specific tuning from Bayesian recommendations"""
    difficulty = recommendations.get('difficulty', 'medium')
    num_questions = recommendations.get('num_questions', 10)
    
    # For multiple choice easy level, test all vocabulary words (24 in r003.1)
    if activity_type == 'multiple_choice' and difficulty == '3':
        num_questions = 24  # Test all words at easy level
    
    base_tuning = {
        'difficulty': difficulty,
        'num_questions': num_questions
    }
    
    if activity_type == 'multiple_choice':
        base_tuning['num_choices'] = 4
    elif activity_type == 'bubble_pop':
        speed_map = {'easy': 1.0, 'medium': 1.5, 'hard': 2.0, '3': 1.0, '4': 1.5, '5': 2.0}
        base_tuning['bubble_speed'] = speed_map.get(difficulty, 1.0)
        base_tuning['error_rate'] = 0.2 if difficulty in ['easy', '3'] else 0.3
    elif activity_type == 'fluent_reading':
        speed_map = {'easy': 100, 'medium': 150, 'hard': 200, '3': 100, '4': 150, '5': 200}
        base_tuning['target_speed'] = speed_map.get(difficulty, 100)
    
    return base_tuning


def _get_recommended_tuning(activity_type: str, history: List) -> Dict[str, Any]:
    """Get recommended tuning based on performance history"""
    if not history:
        # Default settings for first attempt
        defaults = {
            'multiple_choice': {'difficulty': '3', 'num_questions': 10, 'num_choices': 4},
            'fill_in_the_blank': {'difficulty': 'easy', 'num_questions': 10},
            'spelling': {'difficulty': 'easy', 'num_questions': 10},
            'bubble_pop': {'difficulty': 'easy', 'bubble_speed': 1.0, 'error_rate': 0.2},
            'fluent_reading': {'target_speed': 100}
        }
        return defaults.get(activity_type, {'difficulty': 'medium'})
    
    # Calculate average performance
    total_percentage = sum(
        (attempt.score / attempt.total * 100) if attempt.total > 0 else 0
        for attempt in history
    )
    avg_percentage = total_percentage / len(history)
    
    # Adjust difficulty based on performance
    if avg_percentage >= 85:
        difficulty = 'hard' if activity_type != 'multiple_choice' else '5'
    elif avg_percentage >= 65:
        difficulty = 'medium' if activity_type != 'multiple_choice' else '4'
    else:
        difficulty = 'easy' if activity_type != 'multiple_choice' else '3'
    
    # Return activity-specific tuning
    base_tuning = {'difficulty': difficulty}
    
    if activity_type == 'multiple_choice':
        base_tuning['num_questions'] = 10
        base_tuning['num_choices'] = 4
    elif activity_type in ['fill_in_the_blank', 'spelling']:
        base_tuning['num_questions'] = 10
    elif activity_type == 'bubble_pop':
        speed_map = {'easy': 1.0, 'medium': 1.5, 'hard': 2.0}
        base_tuning['bubble_speed'] = speed_map.get(difficulty, 1.0)
        base_tuning['error_rate'] = 0.2 if difficulty == 'easy' else 0.3
    elif activity_type == 'fluent_reading':
        speed_map = {'easy': 100, 'medium': 150, 'hard': 200}
        base_tuning['target_speed'] = speed_map.get(difficulty, 100)
    
    return base_tuning


def _is_hard_difficulty(activity_type: str, difficulty: str) -> bool:
    """Check if difficulty is considered 'hard' for unlock purposes"""
    if activity_type == 'multiple_choice':
        return difficulty == '5'
    elif activity_type == 'fill_in_the_blank':
        return difficulty == 'moderate'
    else:
        return difficulty == 'hard'


def _get_next_activity(current_activity: str) -> Optional[str]:
    """Get the next activity in sequence"""
    sequence = [
        'multiple_choice',
        'fill_in_the_blank',
        'spelling',
        'bubble_pop',
        'fluent_reading'
    ]
    try:
        current_index = sequence.index(current_activity)
        if current_index < len(sequence) - 1:
            return sequence[current_index + 1]
    except ValueError:
        pass
    return None


def _get_next_recommendation(student_id: str, current_activity: str, percentage: float, unlocked: List[str]) -> Dict[str, Any]:
    """Get recommendation for next activity"""
    if unlocked:
        return {
            "suggested_activity": unlocked[0],
            "suggested_difficulty": "easy",
            "reason": f"Great job! You've unlocked {unlocked[0]}!"
        }
    elif percentage >= 80:
        return {
            "suggested_activity": current_activity,
            "suggested_difficulty": "hard",
            "reason": "You're doing great! Try a harder difficulty."
        }
    elif percentage >= 65:
        return {
            "suggested_activity": current_activity,
            "suggested_difficulty": "medium",
            "reason": "Good progress! Keep practicing at this level."
        }
    else:
        return {
            "suggested_activity": current_activity,
            "suggested_difficulty": "easy",
            "reason": "Let's practice more at an easier level."
        }
