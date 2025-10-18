"""
Database models for the Agentic Learning Platform.
Stores student performance data only - NOT curriculum content.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
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
    name = Column(String, nullable=False)
    grade_level = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="student")
    attempts = relationship("ActivityAttempt", back_populates="student")


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
