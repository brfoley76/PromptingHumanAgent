"""
Database operations for the Agentic Learning Platform.
Centralized CRUD operations for all database models.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .database import get_db
from .models import Student, Session as SessionModel, ActivityAttempt, ChatMessage


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
        Get a session by ID.
        
        Args:
            session_id: Session's ID
            
        Returns:
            Session object or None if not found
        """
        db = next(get_db())
        try:
            return db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
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
