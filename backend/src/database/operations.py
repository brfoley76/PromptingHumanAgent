"""
Database operations for the Agentic Learning Platform.
Centralized CRUD operations for all database models.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .database import get_db
from .models import Student, Session as SessionModel, ActivityAttempt, ChatMessage, StudentProficiency


class DatabaseOperations:
    """Centralized database operations"""
    
    @staticmethod
    def create_student(name: str, grade_level: int = 3) -> Student:
        """
        Create a new student.
        
        Args:
            name: Student's name
            grade_level: Grade level (default: 3)
            
        Returns:
            Created Student object
        """
        db = next(get_db())
        try:
            student = Student(
                name=name,
                grade_level=grade_level
            )
            db.add(student)
            db.commit()
            db.refresh(student)
            return student
        finally:
            db.close()
    
    @staticmethod
    def get_student(student_id: str) -> Optional[Student]:
        """
        Get a student by ID.
        
        Args:
            student_id: Student's ID
            
        Returns:
            Student object or None if not found
        """
        db = next(get_db())
        try:
            return db.query(Student).filter(Student.student_id == student_id).first()
        finally:
            db.close()
    
    @staticmethod
    def get_student_by_name(name: str) -> Optional[Student]:
        """
        Get a student by username.
        
        Args:
            name: Student's username
            
        Returns:
            Student object or None if not found
        """
        db = next(get_db())
        try:
            return db.query(Student).filter(Student.name == name).first()
        finally:
            db.close()
    
    @staticmethod
    def create_or_get_student(name: str, grade_level: int = 3) -> Student:
        """
        Find existing student by username or create new one.
        
        Args:
            name: Student's username
            grade_level: Grade level (default: 3)
            
        Returns:
            Student object (existing or newly created)
        """
        db = next(get_db())
        try:
            # Try to find existing student
            student = db.query(Student).filter(Student.name == name).first()
            
            if student:
                return student
            
            # Create new student
            student = Student(
                name=name,
                grade_level=grade_level
            )
            db.add(student)
            db.commit()
            db.refresh(student)
            return student
        finally:
            db.close()
    
    @staticmethod
    def create_session(student_id: str, module_id: str) -> SessionModel:
        """
        Create a new learning session.
        
        Args:
            student_id: Student's ID
            module_id: Curriculum module ID
            
        Returns:
            Created Session object
        """
        db = next(get_db())
        try:
            session = SessionModel(
                student_id=student_id,
                module_id=module_id
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        finally:
            db.close()
    
    @staticmethod
    def get_session(session_id: str) -> Optional[SessionModel]:
        """
        Get a session by ID with eagerly loaded student relationship.
        
        Args:
            session_id: Session's ID
            
        Returns:
            Session object or None if not found
        """
        from sqlalchemy.orm import joinedload
        
        db = next(get_db())
        try:
            session = db.query(SessionModel)\
                .options(joinedload(SessionModel.student))\
                .filter(SessionModel.session_id == session_id)\
                .first()
            
            # If session found, access student.name to load it before detaching
            if session and session.student:
                _ = session.student.name  # Force load
            
            return session
        finally:
            db.close()
    
    @staticmethod
    def end_session(session_id: str) -> bool:
        """
        End a learning session.
        
        Args:
            session_id: Session's ID
            
        Returns:
            True if successful, False otherwise
        """
        db = next(get_db())
        try:
            session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            if session:
                session.end_time = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    @staticmethod
    def record_activity_attempt(
        session_id: str,
        student_id: str,
        module_id: str,
        activity_type: str,
        score: int,
        total: int,
        difficulty: str,
        tuning_settings: Dict[str, Any],
        item_results: List[Dict[str, Any]]
    ) -> ActivityAttempt:
        """
        Record an activity attempt.
        
        Args:
            session_id: Session ID
            student_id: Student ID
            module_id: Module ID
            activity_type: Type of activity
            score: Score achieved
            total: Total possible score
            difficulty: Difficulty level
            tuning_settings: Activity-specific settings
            item_results: Per-item results
            
        Returns:
            Created ActivityAttempt object
        """
        db = next(get_db())
        try:
            attempt = ActivityAttempt(
                session_id=session_id,
                student_id=student_id,
                module=module_id,
                activity=activity_type,
                score=score,
                total=total,
                difficulty=difficulty,
                tuning_settings=tuning_settings,
                item_results=item_results
            )
            db.add(attempt)
            db.commit()
            db.refresh(attempt)
            return attempt
        finally:
            db.close()
    
    @staticmethod
    def get_student_performance_history(
        student_id: str,
        activity_type: str,
        limit: int = 10
    ) -> List[ActivityAttempt]:
        """
        Get recent performance history for a student and activity.
        
        Args:
            student_id: Student's ID
            activity_type: Type of activity
            limit: Maximum number of attempts to return
            
        Returns:
            List of ActivityAttempt objects
        """
        db = next(get_db())
        try:
            return db.query(ActivityAttempt)\
                .filter(ActivityAttempt.student_id == student_id)\
                .filter(ActivityAttempt.activity == activity_type)\
                .order_by(ActivityAttempt.date.desc())\
                .limit(limit)\
                .all()
        finally:
            db.close()
    
    @staticmethod
    def save_chat_message(
        session_id: str,
        agent_type: str,
        sender: str,
        message: str
    ) -> ChatMessage:
        """
        Save a chat message.
        
        Args:
            session_id: Session ID
            agent_type: Type of agent ('tutor' or activity name)
            sender: 'student' or 'agent'
            message: Message content
            
        Returns:
            Created ChatMessage object
        """
        db = next(get_db())
        try:
            chat_message = ChatMessage(
                session_id=session_id,
                agent_type=agent_type,
                sender=sender,
                message=message
            )
            db.add(chat_message)
            db.commit()
            db.refresh(chat_message)
            return chat_message
        finally:
            db.close()
    
    @staticmethod
    def get_chat_history(session_id: str, limit: int = 50) -> List[ChatMessage]:
        """
        Get chat history for a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of ChatMessage objects
        """
        db = next(get_db())
        try:
            return db.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_id)\
                .order_by(ChatMessage.timestamp.asc())\
                .limit(limit)\
                .all()
        finally:
            db.close()
    
    @staticmethod
    def unlock_exercise(student_id: str, exercise_type: str, module_id: str) -> bool:
        """
        Unlock an exercise for a student.
        Note: This is a placeholder. In a full implementation, you'd have
        an ExerciseUnlock table to track this.
        
        Args:
            student_id: Student's ID
            exercise_type: Type of exercise to unlock
            module_id: Module ID
            
        Returns:
            True if successful
        """
        # For now, this is a no-op since we don't have the ExerciseUnlock table yet
        # The frontend will manage unlock state via the backend's activity/end response
        return True
    
    @staticmethod
    def get_student_progress(student_id: str) -> Dict[str, Any]:
        """
        Get detailed progress for a student including unlock states.
        
        Args:
            student_id: Student's ID
            
        Returns:
            Dictionary with progress data for each activity
        """
        db = next(get_db())
        try:
            attempts = db.query(ActivityAttempt)\
                .filter(ActivityAttempt.student_id == student_id)\
                .all()
            
            # Define activity order for unlock logic
            activity_order = [
                'multiple_choice',
                'fill_in_the_blank', 
                'spelling',
                'bubble_pop',
                'fluent_reading'
            ]
            
            progress = {}
            
            for activity in activity_order:
                activity_attempts = [a for a in attempts if a.activity == activity]
                
                if not activity_attempts:
                    # No attempts yet
                    progress[activity] = {
                        "unlocked": activity == 'multiple_choice',  # Only first is unlocked
                        "best_score": None,
                        "highest_difficulty": None,
                        "attempts": 0
                    }
                else:
                    # Find best score and highest difficulty
                    best_attempt = max(activity_attempts, 
                                     key=lambda a: (a.score / a.total) if a.total > 0 else 0)
                    
                    # Determine highest difficulty completed
                    difficulties = [a.difficulty for a in activity_attempts]
                    highest_diff = max(difficulties, key=lambda d: DatabaseOperations._difficulty_value(activity, d))
                    
                    progress[activity] = {
                        "unlocked": True,  # Has attempts, so it's unlocked
                        "best_score": {
                            "score": best_attempt.score,
                            "total": best_attempt.total,
                            "difficulty": best_attempt.difficulty,
                            "percentage": round((best_attempt.score / best_attempt.total * 100) if best_attempt.total > 0 else 0, 1)
                        },
                        "highest_difficulty": highest_diff,
                        "attempts": len(activity_attempts)
                    }
                    
                    # Check if next activity should be unlocked
                    current_index = activity_order.index(activity)
                    if current_index < len(activity_order) - 1:
                        # Check if hard difficulty completed with 80%+
                        hard_attempts = [a for a in activity_attempts 
                                       if DatabaseOperations._is_hard_difficulty(activity, a.difficulty)
                                       and (a.score / a.total * 100) >= 80]
                        
                        if hard_attempts:
                            next_activity = activity_order[current_index + 1]
                            if next_activity not in progress:
                                progress[next_activity] = {
                                    "unlocked": True,
                                    "best_score": None,
                                    "highest_difficulty": None,
                                    "attempts": 0
                                }
                            else:
                                progress[next_activity]["unlocked"] = True
            
            return progress
        finally:
            db.close()
    
    @staticmethod
    def _difficulty_value(activity: str, difficulty: str) -> int:
        """Helper to convert difficulty to numeric value for comparison"""
        if activity == 'multiple_choice':
            return int(difficulty) if difficulty.isdigit() else 3
        elif activity in ['fill_in_the_blank', 'spelling', 'bubble_pop']:
            difficulty_map = {'easy': 1, 'moderate': 2, 'medium': 2, 'hard': 3}
            return difficulty_map.get(difficulty.lower(), 1)
        else:  # fluent_reading uses WPM
            return int(difficulty) if difficulty.isdigit() else 150
    
    @staticmethod
    def _is_hard_difficulty(activity: str, difficulty: str) -> bool:
        """Helper to check if difficulty is 'hard' for unlock purposes"""
        if activity == 'multiple_choice':
            return difficulty == '5'
        elif activity == 'fill_in_the_blank':
            return difficulty.lower() == 'moderate'
        else:
            return difficulty.lower() == 'hard'
    
    @staticmethod
    def get_or_create_proficiency(
        student_id: str,
        level: str,
        domain: str = None,
        module_id: str = None,
        item_id: str = None
    ) -> StudentProficiency:
        """
        Get existing proficiency or create with default priors.
        
        Args:
            student_id: Student's ID
            level: "domain", "module", or "item"
            domain: Domain name (optional)
            module_id: Module ID (optional)
            item_id: Item ID (optional)
            
        Returns:
            StudentProficiency object
        """
        db = next(get_db())
        try:
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
                    item_id=item_id
                )
                db.add(prof)
                db.commit()
                db.refresh(prof)
            
            return prof
        finally:
            db.close()
    
    @staticmethod
    def get_student_proficiencies(
        student_id: str,
        level: str = None,
        module_id: str = None
    ) -> List[StudentProficiency]:
        """
        Get proficiency records for a student.
        INTERNAL USE ONLY - never expose via API.
        
        Args:
            student_id: Student's ID
            level: Filter by level (optional)
            module_id: Filter by module (optional)
            
        Returns:
            List of StudentProficiency objects
        """
        db = next(get_db())
        try:
            query = db.query(StudentProficiency).filter(
                StudentProficiency.student_id == student_id
            )
            
            if level:
                query = query.filter(StudentProficiency.level == level)
            if module_id:
                query = query.filter(StudentProficiency.module_id == module_id)
            
            return query.all()
        finally:
            db.close()
    
    @staticmethod
    def update_proficiency_estimate(
        proficiency_id: str,
        alpha: float,
        beta: float,
        mean_ability: float,
        confidence: float,
        sample_count: int = None
    ) -> StudentProficiency:
        """
        Update a proficiency record with new estimates.
        
        Args:
            proficiency_id: Proficiency ID
            alpha: Beta distribution alpha parameter
            beta: Beta distribution beta parameter
            mean_ability: Calculated mean ability
            confidence: Confidence score
            sample_count: Number of samples (optional)
            
        Returns:
            Updated StudentProficiency object
        """
        db = next(get_db())
        try:
            prof = db.query(StudentProficiency).filter(
                StudentProficiency.proficiency_id == proficiency_id
            ).first()
            
            if prof:
                prof.alpha = alpha
                prof.beta = beta
                prof.mean_ability = mean_ability
                prof.confidence = confidence
                if sample_count is not None:
                    prof.sample_count = sample_count
                prof.last_updated = datetime.utcnow()
                db.commit()
                db.refresh(prof)
            
            return prof
        finally:
            db.close()
    
    @staticmethod
    def bulk_create_proficiencies(
        proficiency_list: List[Dict[str, Any]]
    ) -> List[StudentProficiency]:
        """
        Bulk create proficiency records for efficiency.
        
        Args:
            proficiency_list: List of proficiency dicts with keys:
                student_id, level, domain, module_id, item_id
                
        Returns:
            List of created StudentProficiency objects
        """
        db = next(get_db())
        try:
            proficiencies = []
            for prof_data in proficiency_list:
                prof = StudentProficiency(**prof_data)
                db.add(prof)
                proficiencies.append(prof)
            
            db.commit()
            for prof in proficiencies:
                db.refresh(prof)
            
            return proficiencies
        finally:
            db.close()
    
    @staticmethod
    def get_student_stats(student_id: str) -> Dict[str, Any]:
        """
        Get overall statistics for a student.
        
        Args:
            student_id: Student's ID
            
        Returns:
            Dictionary with statistics
        """
        db = next(get_db())
        try:
            student = db.query(Student).filter(Student.student_id == student_id).first()
            if not student:
                return {}
            
            attempts = db.query(ActivityAttempt)\
                .filter(ActivityAttempt.student_id == student_id)\
                .all()
            
            if not attempts:
                return {
                    "student_id": student_id,
                    "name": student.name,
                    "total_attempts": 0,
                    "average_score": 0
                }
            
            total_score = sum(a.score for a in attempts)
            total_possible = sum(a.total for a in attempts)
            avg_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
            
            # Group by activity
            activity_stats = {}
            for attempt in attempts:
                if attempt.activity not in activity_stats:
                    activity_stats[attempt.activity] = {
                        "attempts": 0,
                        "total_score": 0,
                        "total_possible": 0
                    }
                activity_stats[attempt.activity]["attempts"] += 1
                activity_stats[attempt.activity]["total_score"] += attempt.score
                activity_stats[attempt.activity]["total_possible"] += attempt.total
            
            # Calculate percentages
            for activity, stats in activity_stats.items():
                stats["average_percentage"] = (
                    stats["total_score"] / stats["total_possible"] * 100
                ) if stats["total_possible"] > 0 else 0
            
            return {
                "student_id": student_id,
                "name": student.name,
                "total_attempts": len(attempts),
                "average_score": round(avg_percentage, 1),
                "activity_breakdown": activity_stats
            }
        finally:
            db.close()
