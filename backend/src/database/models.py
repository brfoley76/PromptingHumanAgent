"""
Database models for the Agentic Learning Platform.
Stores student performance data only - NOT curriculum content.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, Float, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


class Student(Base):
    """Student profile - basic info only"""
    __tablename__ = "students"
    
    student_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True, index=True)  # Username is unique
    grade_level = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="student")
    attempts = relationship("ActivityAttempt", back_populates="student")
    proficiencies = relationship("StudentProficiency", back_populates="student")


class Session(Base):
    """Learning session - tracks a single study session"""
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    module_id = Column(String, nullable=False)  # References Learning Module curriculum
    
    # Relationships
    student = relationship("Student", back_populates="sessions")
    attempts = relationship("ActivityAttempt", back_populates="session")
    messages = relationship("ChatMessage", back_populates="session")


class ActivityAttempt(Base):
    """Performance data for a single activity attempt"""
    __tablename__ = "activity_attempts"
    
    attempt_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    module = Column(String, nullable=False)  # References Learning Module
    activity = Column(String, nullable=False)  # Activity type
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    difficulty = Column(String, nullable=False)
    tuning_settings = Column(JSON, nullable=False)  # Activity-specific parameters
    item_results = Column(JSON, nullable=False)  # Per-item success/failure
    
    # Relationships
    session = relationship("Session", back_populates="attempts")
    student = relationship("Student", back_populates="attempts")


class ChatMessage(Base):
    """Chat message history between student and agent"""
    __tablename__ = "chat_messages"
    
    message_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    agent_type = Column(String, nullable=False)  # 'tutor' or activity name
    sender = Column(String, nullable=False)  # 'student' or 'agent'
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="messages")


class ActivityMastery(Base):
    """
    Tracks highest difficulty completed per activity per student.
    Used to enforce hard-mode completion before unlocking next activity.
    """
    __tablename__ = "activity_mastery"
    
    mastery_id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    module_id = Column(String, nullable=False, index=True)
    activity_type = Column(String, nullable=False, index=True)
    
    # Difficulty tracking
    highest_difficulty = Column(String, nullable=False)  # 'easy', 'medium', 'hard' or '3', '4', '5'
    highest_difficulty_score = Column(Float, nullable=False)  # Best score on that difficulty (percentage)
    highest_difficulty_date = Column(DateTime, nullable=False)
    
    # Completion flag - True if scored 80%+ on hard mode
    completed_hard_mode = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_student_module_activity', 'student_id', 'module_id', 'activity_type', unique=True),
    )


class StudentProficiency(Base):
    """
    PRIVATE: Never exposed to frontend
    Bayesian proficiency estimates for adaptive learning
    
    Uses Beta distribution for Bayesian updating:
    - Prior: Beta(α₀, β₀) = Beta(2, 2) - slightly informed prior at 50%
    - After n successes and m failures: Beta(α₀+n, β₀+m)
    - Mean ability = α / (α + β)
    - Confidence increases as α + β increases
    """
    __tablename__ = "student_proficiencies"
    
    proficiency_id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    
    # Granularity levels: "domain" (e.g., verbal), "module" (e.g., r003.1), "item" (e.g., pirate)
    level = Column(String, nullable=False, index=True)
    
    # Identifiers
    domain = Column(String, nullable=True)  # "reading", "math", etc.
    module_id = Column(String, nullable=True, index=True)  # "r003.1", etc.
    item_id = Column(String, nullable=True, index=True)  # "pirate", "3x4", etc.
    
    # Beta distribution parameters (for Bayesian updating)
    alpha = Column(Float, default=2.0)  # Success count + prior
    beta = Column(Float, default=2.0)   # Failure count + prior
    
    # Derived metrics (cached for performance)
    mean_ability = Column(Float, default=0.5)  # alpha / (alpha + beta)
    confidence = Column(Float, default=0.5)    # Related to alpha + beta
    
    # Learning dynamics
    learning_rate = Column(Float, default=0.1)  # Student-specific adjustment
    forgetting_rate = Column(Float, default=0.05)  # Per day
    
    # Metadata
    sample_count = Column(Integer, default=0)  # Number of observations
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="proficiencies")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_student_level_module', 'student_id', 'level', 'module_id'),
        Index('idx_student_module_item', 'student_id', 'module_id', 'item_id'),
    )
