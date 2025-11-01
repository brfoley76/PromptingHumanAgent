"""
Unit tests for database operations
Run with: pytest tests/test_database_operations.py -v
"""
import pytest
from datetime import datetime
from src.database.operations import DatabaseOperations
from src.database.database import init_db, SessionLocal


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    init_db()
    session = SessionLocal()
    yield session
    session.close()


class TestStudentOperations:
    """Test suite for student CRUD operations"""
    
    def test_create_student(self, db_session):
        """Test creating a new student"""
        student = DatabaseOperations.create_or_get_student("test_student_1")
        
        assert student is not None
        assert student.name == "test_student_1"
        assert student.student_id is not None
        assert student.grade_level == 3  # Default grade level
    
    def test_get_student_by_name(self, db_session):
        """Test retrieving student by name"""
        # Create student
        created = DatabaseOperations.create_or_get_student("test_student_2")
        
        # Retrieve by name
        retrieved = DatabaseOperations.get_student_by_name("test_student_2")
        
        assert retrieved is not None
        assert retrieved.student_id == created.student_id
        assert retrieved.name == "test_student_2"
    
    def test_get_nonexistent_student(self, db_session):
        """Test retrieving non-existent student returns None"""
        student = DatabaseOperations.get_student_by_name("nonexistent_student")
        assert student is None
    
    def test_create_or_get_existing_student(self, db_session):
        """Test that create_or_get returns existing student"""
        # Create student
        student1 = DatabaseOperations.create_or_get_student("test_student_3")
        student1_id = student1.student_id
        
        # Try to create again
        student2 = DatabaseOperations.create_or_get_student("test_student_3")
        
        # Should return same student
        assert student2.student_id == student1_id
        assert student2.name == "test_student_3"


class TestSessionOperations:
    """Test suite for session CRUD operations"""
    
    def test_create_session(self, db_session):
        """Test creating a new session"""
        # Create student first
        student = DatabaseOperations.create_or_get_student("test_session_student")
        
        # Create session
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        assert session is not None
        assert session.student_id == student.student_id
        assert session.module_id == "r003.1"
        assert session.start_time is not None
        assert session.end_time is None
    
    def test_get_session(self, db_session):
        """Test retrieving a session"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_get_session")
        created_session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Retrieve session
        retrieved_session = DatabaseOperations.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.student_id == student.student_id
    
    def test_end_session(self, db_session):
        """Test ending a session"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_end_session")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # End session
        DatabaseOperations.end_session(session.session_id)
        
        # Verify session was ended
        ended_session = DatabaseOperations.get_session(session.session_id)
        assert ended_session.end_time is not None


class TestActivityAttemptOperations:
    """Test suite for activity attempt operations"""
    
    def test_record_activity_attempt(self, db_session):
        """Test recording an activity attempt"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_activity_student")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Record attempt
        attempt = DatabaseOperations.record_activity_attempt(
            session_id=session.session_id,
            student_id=student.student_id,
            module_id="r003.1",
            activity_type="multiple_choice",
            score=8,
            total=10,
            difficulty="4",
            tuning_settings={"num_questions": 10, "num_choices": 4},
            item_results=[{"question": 1, "correct": True}]
        )
        
        assert attempt is not None
        assert attempt.session_id == session.session_id
        assert attempt.student_id == student.student_id
        assert attempt.activity == "multiple_choice"
        assert attempt.score == 8
        assert attempt.total == 10
        assert attempt.difficulty == "4"
    
    def test_get_performance_history(self, db_session):
        """Test retrieving performance history"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_history_student")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Record multiple attempts
        for score in [7, 8, 9]:
            DatabaseOperations.record_activity_attempt(
                session_id=session.session_id,
                student_id=student.student_id,
                module_id="r003.1",
                activity_type="spelling",
                score=score,
                total=10,
                difficulty="easy",
                tuning_settings={},
                item_results=[]
            )
        
        # Get history
        history = DatabaseOperations.get_student_performance_history(
            student.student_id,
            "spelling",
            limit=5
        )
        
        assert len(history) == 3
        assert history[0].score == 9  # Most recent first
        assert history[1].score == 8
        assert history[2].score == 7
    
    def test_get_student_progress(self, db_session):
        """Test getting student progress"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_progress_student")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Record some attempts
        DatabaseOperations.record_activity_attempt(
            session_id=session.session_id,
            student_id=student.student_id,
            module_id="r003.1",
            activity_type="multiple_choice",
            score=8,
            total=10,
            difficulty="4",
            tuning_settings={},
            item_results=[]
        )
        
        # Get progress
        progress = DatabaseOperations.get_student_progress(student.student_id)
        
        assert progress is not None
        assert "unlocked_exercises" in progress
        assert "total_attempts" in progress
        assert progress["total_attempts"] > 0


class TestChatMessageOperations:
    """Test suite for chat message operations"""
    
    def test_save_chat_message(self, db_session):
        """Test saving a chat message"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_chat_student")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Save message
        message = DatabaseOperations.save_chat_message(
            session_id=session.session_id,
            agent_type="tutor",
            sender="student",
            message="Hello, can you help me?"
        )
        
        assert message is not None
        assert message.session_id == session.session_id
        assert message.agent_type == "tutor"
        assert message.sender == "student"
        assert message.message == "Hello, can you help me?"
    
    def test_get_chat_history(self, db_session):
        """Test retrieving chat history"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_chat_history")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Save multiple messages
        messages_data = [
            ("tutor", "student", "Hello"),
            ("tutor", "agent", "Hi! How can I help?"),
            ("tutor", "student", "What does pirate mean?")
        ]
        
        for agent_type, sender, msg in messages_data:
            DatabaseOperations.save_chat_message(
                session_id=session.session_id,
                agent_type=agent_type,
                sender=sender,
                message=msg
            )
        
        # Get history
        history = DatabaseOperations.get_chat_history(session.session_id, limit=10)
        
        assert len(history) == 3
        assert history[0].message == "Hello"  # Oldest first
        assert history[2].message == "What does pirate mean?"


class TestUnlockOperations:
    """Test suite for exercise unlock operations"""
    
    def test_unlock_exercise(self, db_session):
        """Test unlocking an exercise"""
        # Create student
        student = DatabaseOperations.create_or_get_student("test_unlock_student")
        
        # Unlock exercise
        result = DatabaseOperations.unlock_exercise(
            student.student_id,
            "fill_in_the_blank",
            "r003.1"
        )
        
        assert result is True
        
        # Verify it's unlocked in progress
        progress = DatabaseOperations.get_student_progress(student.student_id)
        assert "fill_in_the_blank" in progress["unlocked_exercises"]


class TestStudentStats:
    """Test suite for student statistics"""
    
    def test_get_student_stats(self, db_session):
        """Test getting student statistics"""
        # Create student and session
        student = DatabaseOperations.create_or_get_student("test_stats_student")
        session = DatabaseOperations.create_session(student.student_id, "r003.1")
        
        # Record some attempts
        for i in range(5):
            DatabaseOperations.record_activity_attempt(
                session_id=session.session_id,
                student_id=student.student_id,
                module_id="r003.1",
                activity_type="multiple_choice",
                score=8 + i % 2,  # Alternating 8 and 9
                total=10,
                difficulty="4",
                tuning_settings={},
                item_results=[]
            )
        
        # Get stats
        stats = DatabaseOperations.get_student_stats(student.student_id)
        
        assert stats is not None
        assert "total_attempts" in stats
        assert stats["total_attempts"] == 5
        assert "average_score" in stats
        assert stats["average_score"] > 0


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "database: marks tests as database tests"
    )
