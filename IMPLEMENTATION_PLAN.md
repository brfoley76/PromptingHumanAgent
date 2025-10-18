# Agentic Learning System - Implementation Plan

## Overview

This document provides a detailed, phase-by-phase implementation plan for adding the agentic layer to the learning module.

## Prerequisites

### Development Environment
- Python 3.11 or higher
- Node.js 18+ (for frontend tooling)
- Git
- Code editor (VS Code recommended)
- SQLite browser tool (DB Browser for SQLite recommended)

### Required Accounts
- OpenAI API account (or alternative LLM provider)
- GitHub account (for version control)

## Project Structure

```
learning_module/
├── web/                          # Frontend (existing)
│   ├── index.html
│   ├── css/
│   ├── js/
│   │   ├── agent/               # NEW: Agent integration
│   │   │   ├── SessionManager.js
│   │   │   ├── ChatWidget.js
│   │   │   └── WebSocketClient.js
│   │   ├── app.js               # Modified
│   │   └── ...
│   └── data/
└── backend/                      # NEW: Backend service
    ├── src/
    │   ├── main.py              # FastAPI app entry point
    │   ├── config.py            # Configuration
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── routes.py        # REST endpoints
    │   │   └── websocket.py     # WebSocket handler
    │   ├── agents/
    │   │   ├── __init__.py
    │   │   ├── graph.py         # LangGraph orchestration
    │   │   ├── tutor.py         # Tutor agent
    │   │   ├── activity.py      # Activity agents
    │   │   └── prompts.py       # Agent prompts
    │   ├── database/
    │   │   ├── __init__.py
    │   │   ├── models.py        # SQLAlchemy models
    │   │   ├── database.py      # DB connection
    │   │   └── operations.py    # CRUD operations
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── adaptive.py      # Adaptive difficulty
    │   │   ├── curriculum.py    # Curriculum management
    │   │   └── analytics.py     # Performance analytics
    │   └── schemas/
    │       ├── __init__.py
    │       ├── session.py       # Pydantic schemas
    │       ├── student.py
    │       └── activity.py
    ├── tests/
    │   ├── test_agents.py
    │   ├── test_api.py
    │   └── test_adaptive.py
    ├── requirements.txt
    ├── pyproject.toml
    └── README.md
```

---

## Phase 1: Foundation & Setup (Week 1)

### 1.1 Backend Project Setup

**Tasks:**
1. Create backend directory structure
2. Set up Python virtual environment
3. Install dependencies
4. Configure environment variables

**Commands:**
```bash
cd learning_module
mkdir -p backend/src/{api,agents,database,services,schemas}
mkdir -p backend/tests
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create requirements.txt
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-dotenv==1.0.0
langchain==0.1.0
langchain-openai==0.0.2
langgraph==0.0.20
websockets==12.0
aiosqlite==0.19.0
python-multipart==0.0.6
EOF

pip install -r requirements.txt
```

**Create `.env` file:**
```bash
cat > .env << EOF
# LLM Configuration
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4-turbo-preview

# Database
DATABASE_URL=sqlite:///./learning.db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Frontend
FRONTEND_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:8000,http://localhost:3000
EOF
```

**Deliverables:**
- [ ] Backend directory structure created
- [ ] Virtual environment configured
- [ ] Dependencies installed
- [ ] `.env` file created (excluded from git)

---

### 1.2 Database Setup

**Tasks:**
1. Create SQLAlchemy models
2. Set up database connection
3. Create initialization script
4. Test database operations

**File: `backend/src/database/models.py`**
```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Student(Base):
    __tablename__ = "students"
    
    student_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    grade_level = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sessions = relationship("Session", back_populates="student")
    attempts = relationship("ActivityAttempt", back_populates="student")

class Session(Base):
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    module_id = Column(String, nullable=False)
    
    student = relationship("Student", back_populates="sessions")
    attempts = relationship("ActivityAttempt", back_populates="session")
    messages = relationship("ChatMessage", back_populates="session")

class ActivityAttempt(Base):
    __tablename__ = "activity_attempts"
    
    attempt_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    module = Column(String, nullable=False)
    activity = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    difficulty = Column(String, nullable=False)
    tuning_settings = Column(JSON, nullable=False)
    item_results = Column(JSON, nullable=False)
    
    session = relationship("Session", back_populates="attempts")
    student = relationship("Student", back_populates="attempts")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    message_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    agent_type = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")
```

**File: `backend/src/database/database.py`**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./learning.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**File: `backend/src/database/operations.py`**
```python
from sqlalchemy.orm import Session
from . import models
from typing import List, Optional
import json

class StudentOperations:
    @staticmethod
    def create_student(db: Session, name: str, grade_level: int = 3) -> models.Student:
        student = models.Student(name=name, grade_level=grade_level)
        db.add(student)
        db.commit()
        db.refresh(student)
        return student
    
    @staticmethod
    def get_student(db: Session, student_id: str) -> Optional[models.Student]:
        return db.query(models.Student).filter(
            models.Student.student_id == student_id
        ).first()
    
    @staticmethod
    def get_student_attempts(
        db: Session, 
        student_id: str, 
        activity: Optional[str] = None,
        limit: int = 10
    ) -> List[models.ActivityAttempt]:
        query = db.query(models.ActivityAttempt).filter(
            models.ActivityAttempt.student_id == student_id
        )
        if activity:
            query = query.filter(models.ActivityAttempt.activity == activity)
        return query.order_by(models.ActivityAttempt.date.desc()).limit(limit).all()

class SessionOperations:
    @staticmethod
    def create_session(db: Session, student_id: str, module_id: str) -> models.Session:
        session = models.Session(student_id=student_id, module_id=module_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def end_session(db: Session, session_id: str):
        from datetime import datetime
        session = db.query(models.Session).filter(
            models.Session.session_id == session_id
        ).first()
        if session:
            session.end_time = datetime.utcnow()
            db.commit()

class AttemptOperations:
    @staticmethod
    def record_attempt(
        db: Session,
        session_id: str,
        student_id: str,
        module: str,
        activity: str,
        score: int,
        total: int,
        difficulty: str,
        tuning_settings: dict,
        item_results: list
    ) -> models.ActivityAttempt:
        attempt = models.ActivityAttempt(
            session_id=session_id,
            student_id=student_id,
            module=module,
            activity=activity,
            score=score,
            total=total,
            difficulty=difficulty,
            tuning_settings=json.dumps(tuning_settings),
            item_results=json.dumps(item_results)
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return attempt
```

**Test script: `backend/init_db.py`**
```python
from src.database.database import init_db

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
```

**Deliverables:**
- [ ] Database models created
- [ ] Database connection configured
- [ ] CRUD operations implemented
- [ ] Database initialized and tested

---

### 1.3 Basic FastAPI Server

**File: `backend/src/config.py`**
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # Database
    database_url: str = "sqlite:///./learning.db"
    
    # LLM
    openai_api_key: str
    model_name: str = "gpt-4-turbo-preview"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:8000", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**File: `backend/src/main.py`**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database.database import init_db

app = FastAPI(
    title="Learning Module Agent API",
    version="1.0.0",
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/")
async def root():
    return {"message": "Learning Module Agent API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
```

**Run server:**
```bash
cd backend
python -m src.main
# Or: uvicorn src.main:app --reload
```

**Test:**
```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

**Deliverables:**
- [ ] FastAPI server configured
- [ ] CORS middleware added
- [ ] Health check endpoint working
- [ ] Server runs successfully

---

## Phase 2: LangGraph Agent System (Week 2)

### 2.1 Agent Prompts

**File: `backend/src/agents/prompts.py`**
```python
from typing import Dict, List

def get_tutor_prompt(
    module_id: str,
    vocabulary: List[Dict],
    student_name: str,
    mastery_percentage: float,
    strong_words: List[str],
    weak_words: List[str],
    recent_scores: List[Dict],
    unlocked_activities: List[str]
) -> str:
    vocab_list = "\n".join([f"- {v['word']}: {v['definition']}" for v in vocabulary])
    activities_list = "\n".join([f"- {a}" for a in unlocked_activities])
    
    return f"""You are a friendly pirate-themed learning tutor helping a 3rd grade student.

CONTEXT:
- Current Module: {module_id}
- Curriculum Vocabulary:
{vocab_list}

- Student Profile:
  * Name: {student_name}
  * Overall Mastery: {mastery_percentage:.1f}%
  * Strong Words: {', '.join(strong_words) if strong_words else 'None yet'}
  * Needs Practice: {', '.join(weak_words) if weak_words else 'None yet'}
  * Recent Performance: {len(recent_scores)} activities completed

YOUR ROLE:
- Guide the student through the learning module with encouragement
- Explain vocabulary words using simple, grade-appropriate language
- Suggest activities based on their current level
- Answer questions about the pirate story and vocabulary
- Celebrate successes and provide supportive feedback on mistakes
- Use pirate-themed language occasionally but keep it fun and clear

GUIDELINES:
- Keep responses brief (2-3 sentences)
- Use simple words and short sentences
- Be encouraging and positive
- Reference the pirate story context when explaining words
- Don't give direct answers - guide students to discover

AVAILABLE ACTIVITIES:
{activities_list}

Current conversation:"""

def get_activity_agent_prompt(
    activity_type: str,
    difficulty: str,
    current_question: Dict,
    student_answer: str,
    correct_answer: str,
    recent_accuracy: float,
    mastered_words: List[str],
    struggling_words: List[str]
) -> str:
    return f"""You are an educational assistant helping with the {activity_type} exercise.

CURRENT EXERCISE:
- Activity: {activity_type}
- Difficulty: {difficulty}
- Current Question: {current_question}
- Student Answer: {student_answer}
- Correct Answer: {correct_answer}

STUDENT CONTEXT:
- Recent accuracy in this activity: {recent_accuracy:.1f}%
- Words mastered: {', '.join(mastered_words) if mastered_words else 'None yet'}
- Words needing practice: {', '.join(struggling_words) if struggling_words else 'None yet'}

YOUR TASK:
When student makes an error:
1. Identify the specific misconception
2. Provide a hint that guides without giving the answer
3. Reference the curriculum definition or story context
4. Keep it brief and encouraging

When student requests help:
1. Assess what they might be confused about
2. Provide progressively more explicit hints
3. Eventually guide to the answer if needed

Example error response:
"Hmm, that's close! Remember, a {current_question.get('word', 'word')} is {current_question.get('definition', 'definition')}. 
In the pirate story, [relevant context]. Try again!"

Be helpful, encouraging, and educational."""
```

### 2.2 LangGraph State and Nodes

**File: `backend/src/agents/graph.py`**
```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from ..config import settings

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    student_id: str
    session_id: str
    agent_type: str  # "tutor" or activity name
    context: dict
    next_action: str

def create_agent_graph():
    """Create the LangGraph agent system"""
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        temperature=0.7
    )
    
    # Define graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("tutor", tutor_node)
    workflow.add_node("activity", activity_node)
    
    # Add edges
    workflow.add_conditional_edges(
        "supervisor",
        route_agent,
        {
            "tutor": "tutor",
            "activity": "activity",
            "end": END
        }
    )
    
    workflow.add_edge("tutor", END)
    workflow.add_edge("activity", END)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    return workflow.compile()

def supervisor_node(state: AgentState) -> AgentState:
    """Route to appropriate agent"""
    # Logic to determine which agent should handle the message
    if state.get("agent_type") == "tutor":
        state["next_action"] = "tutor"
    else:
        state["next_action"] = "activity"
    return state

def tutor_node(state: AgentState) -> AgentState:
    """Tutor agent processing"""
    # TODO: Implement tutor logic
    return state

def activity_node(state: AgentState) -> AgentState:
    """Activity agent processing"""
    # TODO: Implement activity logic
    return state

def route_agent(state: AgentState) -> str:
    """Determine next node"""
    return state.get("next_action", "end")
```

**Deliverables:**
- [ ] Agent prompts created
- [ ] LangGraph state defined
- [ ] Basic graph structure implemented
- [ ] Routing logic added

---

### 2.3 Curriculum Service (Fetch from Learning Module)

**File: `backend/src/services/curriculum.py`**
```python
from typing import Dict, Optional
import json
import requests
from pathlib import Path
from ..config import settings

class CurriculumService:
    """
    Fetches curriculum data from Learning Module Platform.
    Does NOT store curriculum - only caches temporarily.
    """
    
    # Cache for session duration
    _cache: Dict[str, Dict] = {}
    
    @staticmethod
    def load_curriculum(module_id: str, use_cache: bool = True) -> Dict:
        """
        Fetch curriculum from Learning Module Platform.
        
        Args:
            module_id: Curriculum module identifier (e.g., 'r003.1')
            use_cache: Whether to use cached data
            
        Returns:
            Curriculum dictionary
        """
        if use_cache and module_id in CurriculumService._cache:
            return CurriculumService._cache[module_id]
        
        # Option 1: Fetch via HTTP API
        if hasattr(settings, 'learning_module_url'):
            curriculum = CurriculumService._fetch_via_api(module_id)
        # Option 2: Read from shared filesystem
        else:
            curriculum = CurriculumService._fetch_via_filesystem(module_id)
        
        # Cache temporarily
        CurriculumService._cache[module_id] = curriculum
        return curriculum
    
    @staticmethod
    def _fetch_via_api(module_id: str) -> Dict:
        """Fetch curriculum via Learning Module API"""
        url = f"{settings.learning_module_url}/curriculum/{module_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def _fetch_via_filesystem(module_id: str) -> Dict:
        """Read curriculum from shared filesystem"""
        # Path to Learning Module curriculum directory
        curriculum_path = Path(settings.learning_module_path) / f"{module_id}.json"
        
        if not curriculum_path.exists():
            raise FileNotFoundError(f"Curriculum {module_id} not found")
        
        with open(curriculum_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def get_vocabulary(module_id: str) -> list:
        """Get just the vocabulary list"""
        curriculum = CurriculumService.load_curriculum(module_id)
        return curriculum.get('content', {}).get('vocabulary', [])
    
    @staticmethod
    def get_narrative(module_id: str) -> dict:
        """Get the narrative content"""
        curriculum = CurriculumService.load_curriculum(module_id)
        return curriculum.get('content', {}).get('narrative', {})
    
    @staticmethod
    def get_unlocked_activities(attempts: list) -> list:
        """
        Determine which activities should be unlocked.
        Note: Unlock logic could also live in Learning Module.
        """
        # Default: all activities available
        all_activities = [
            'multiple_choice',
            'fill_in_the_blank',
            'spelling',
            'bubble_pop',
            'fluent_reading'
        ]
        
        if not attempts:
            # First time: only first activity
            return [all_activities[0]]
        
        # Check if any hard difficulty completed with >80%
        for attempt in attempts:
            if attempt.difficulty == 'hard':
                accuracy = attempt.score / attempt.total
                if accuracy >= 0.8:
                    # Could unlock more based on logic
                    pass
        
        return all_activities
    
    @staticmethod
    def clear_cache(module_id: Optional[str] = None):
        """Clear curriculum cache"""
        if module_id:
            CurriculumService._cache.pop(module_id, None)
        else:
            CurriculumService._cache.clear()
```

**Update `backend/src/config.py`:**
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Learning Module Platform integration
    learning_module_url: Optional[str] = None  # e.g., "http://localhost:8001"
    learning_module_path: str = "../learning_module/web/data"  # Filesystem fallback
```

**Deliverables:**
- [ ] Curriculum service implemented
- [ ] API fetch method configured
- [ ] Filesystem fallback implemented
- [ ] Caching mechanism working

---

### 2.4 Adaptive Difficulty Service

**File: `backend/src/services/adaptive.py`**
```python
from typing import Dict, List
from sqlalchemy.orm import Session
from ..database.operations import StudentOperations
import json

class AdaptiveService:
    @staticmethod
    def calculate_tuning_settings(
        db: Session,
        student_id: str,
        activity_type: str,
        curriculum: dict
    ) -> Dict:
        """Calculate recommended tuning settings based on student history"""
        
        # Get recent attempts
        attempts = StudentOperations.get_student_attempts(
            db, student_id, activity_type, limit=5
        )
        
        if not attempts:
            # No history, return default easy settings
            return AdaptiveService._get_default_settings(activity_type, "easy")
        
        # Calculate average accuracy
        total_score = sum(a.score for a in attempts)
        total_possible = sum(a.total for a in attempts)
        avg_accuracy = total_score / total_possible if total_possible > 0 else 0
        
        # Determine difficulty tier
        if avg_accuracy > 0.85:
            difficulty = "hard"
            speed_mult = 1.5
        elif avg_accuracy > 0.65:
            difficulty = "moderate"
            speed_mult = 1.0
        else:
            difficulty = "easy"
            speed_mult = 0.7
        
        # Generate activity-specific tuning
        return AdaptiveService._generate_activity_tuning(
            activity_type,
            difficulty,
            speed_mult,
            avg_accuracy
        )
    
    @staticmethod
    def _get_default_settings(activity_type: str, difficulty: str) -> Dict:
        """Default settings for first attempt"""
        defaults = {
            "multiple_choice": {
                "easy": {"difficulty": "easy", "num_questions": 5, "num_choices": 3},
                "moderate": {"difficulty": "moderate", "num_questions": 10, "num_choices": 4},
                "hard": {"difficulty": "hard", "num_questions": 15, "num_choices": 5}
            },
            "spelling": {
                "easy": {"difficulty": "easy", "num_questions": 5, "hint_availability": "always"},
                "moderate": {"difficulty": "medium", "num_questions": 10, "hint_availability": "after_2_attempts"},
                "hard": {"difficulty": "hard", "num_questions": 15, "hint_availability": "never"}
            },
            "bubble_pop": {
                "easy": {"difficulty": "easy", "bubble_speed": 0.8, "error_rate": 0.1, "game_mode": "easy", "initial_delay": 3000, "min_delay": 1000, "ramp_rate": 25},
                "moderate": {"difficulty": "moderate", "bubble_speed": 1.2, "error_rate": 0.2, "game_mode": "moderate", "initial_delay": 2000, "min_delay": 600, "ramp_rate": 50},
                "hard": {"difficulty": "hard", "bubble_speed": 1.8, "error_rate": 0.4, "game_mode": "hard", "initial_delay": 1500, "min_delay": 400, "ramp_rate": 75}
            },
            # Add other activities...
        }
        return defaults.get(activity_type, {}).get(difficulty, {})
    
    @staticmethod
    def _generate_activity_tuning(
        activity_type: str,
        difficulty: str,
        speed_mult: float,
        accuracy: float
    ) -> Dict:
        """Generate tuning settings based on performance"""
        base_settings = AdaptiveService._get_default_settings(activity_type, difficulty)
        
        # Adjust based on accuracy
        if activity_type == "bubble_pop":
            base_settings["bubble_speed"] *= speed_mult
            if accuracy < 0.5:
                base_settings["min_delay"] = int(base_settings["min_delay"] * 1.5)
        
        return base_settings
    
    @staticmethod
    def analyze_word_mastery(db: Session, student_id: str) -> Dict:
        """Analyze which vocabulary words student has mastered"""
        attempts = StudentOperations.get_student_attempts(db, student_id, limit=20)
        
        word_stats = {}
        for attempt in attempts:
            item_results = json.loads(attempt.item_results)
            for item in item_results:
                word = item.get("word")
                if word:
                    if word not in word_stats:
                        word_stats[word] = {"correct": 0, "total": 0}
                    word_stats[word]["total"] += 1
                    if item.get("correct"):
                        word_stats[word]["correct"] += 1
        
        # Calculate mastery percentage for each word
        mastery = {}
        for word, stats in word_stats.items():
            mastery[word] = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        return mastery
```

**Deliverables:**
- [ ] Curriculum service with fetch capability
- [ ] Adaptive service implemented
- [ ] Default settings defined for all activities
- [ ] Difficulty calculation algorithm working
- [ ] Word mastery analysis implemented

---

## Phase 3: API Endpoints (Week 3)

### 3.1 Pydantic Schemas

**File: `backend/src/schemas/session.py`**
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

class SessionInitRequest(BaseModel):
    student_id: Optional[str] = None
    name: Optional[str] = None

class SessionInitResponse(BaseModel):
    session_id: str
    student_id: str
    student_name: str
    module_id: str
    available_activities: List[str]
    tutor_greeting: str
    curriculum_module: Dict

class SessionEndRequest(BaseModel):
    session_id: str

class ActivityStartRequest(BaseModel):
    session_id: str
    activity_type: str

class ActivityStartResponse(BaseModel):
    activity_type: str
    recommended_tuning: Dict
    agent_intro: str
    vocabulary_focus: List[str]

class ActivityEndRequest(BaseModel):
    session_id: str
    activity_type: str
    results: Dict
    tuning_settings: Dict

class ActivityEndResponse(BaseModel):
    feedback: str
    profile_update: Dict
    next_recommendation: Dict
    unlocked_activities: List[str]
```

### 3.2 REST Endpoints

**File: `backend/src/api/routes.py`**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..database.operations import StudentOperations, SessionOperations, AttemptOperations
from ..services.adaptive import AdaptiveService
from ..services.curriculum import CurriculumService
from ..schemas import session as schemas
import json

router = APIRouter(prefix="/api", tags=["api"])

@router.post("/session/init", response_model=schemas.SessionInitResponse)
async def initialize_session(
    request: schemas.SessionInitRequest,
    db: Session = Depends(get_db)
):
    """Initialize a learning session"""
    
    # Get or create student
    if request.student_id:
        student = StudentOperations.get_student(db, request.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
    elif request.name:
        student = StudentOperations.create_student(db, request.name)
    else:
        raise HTTPException(status_code=400, detail="Must provide student_id or name")
    
    # Create session
    module_id = "r003.1"  # Default module
    session = SessionOperations.create_session(db, student.student_id, module_id)
    
    # Fetch curriculum from Learning Module Platform
    curriculum = CurriculumService.load_curriculum(module_id)
    
    # Determine available activities
    attempts = StudentOperations.get_student_attempts(db, student.student_id)
    available_activities = CurriculumService.get_unlocked_activities(attempts)
    
    # Generate tutor greeting
    tutor_greeting = f"Ahoy, {student.name}! Ready for some pirate adventure learning?"
    
    return schemas.SessionInitResponse(
        session_id=session.session_id,
        student_id=student.student_id,
        student_name=student.name,
        module_id=module_id,
        available_activities=available_activities,
        tutor_greeting=tutor_greeting,
        curriculum_module=curriculum
    )

@router.post("/session/end")
async def end_session(
    request: schemas.SessionEndRequest,
    db: Session = Depends(get_db)
):
    """End a learning session"""
    SessionOperations.end_session(db, request.session_id)
    return {"status": "success", "message": "Session ended"}

@router.post("/activity/start", response_model=schemas.ActivityStartResponse)
async def start_activity(
    request: schemas.ActivityStartRequest,
    db: Session = Depends(get_db)
):
    """Start an activity with agent recommendations"""
    
    # Get session to find student
    session = db.query(models.Session).filter(
        models.Session.session_id == request.session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Fetch activity-specific curriculum from Learning Module Platform
    curriculum = CurriculumService.load_curriculum(session.module_id)
    
    # Calculate recommended tuning
    tuning = AdaptiveService.calculate_tuning_settings(
        db, session.student_id, request.activity_type, curriculum
    )
    
    # Generate agent intro
    agent_intro = f"Let's try {request.activity_type}! I've set it to {tuning['difficulty']} difficulty based on your progress."
    
    # Get vocabulary focus
    word_mastery = AdaptiveService.analyze_word_mastery(db, session.student_id)
    weak_words = [w for w, score in word_mastery.items() if score < 70]
    vocab_focus = weak_words[:5] if weak_words else list(word_mastery.keys())[:5]
    
    return schemas.ActivityStartResponse(
        activity_type=request.activity_type,
        recommended_tuning=tuning,
        agent_intro=agent_intro,
        vocabulary_focus=vocab_focus
    )

@router.post("/activity/end", response_model=schemas.ActivityEndResponse)
async def end_activity(
    request: schemas.ActivityEndRequest,
    db: Session = Depends(get_db)
):
    """Submit activity results and get feedback"""
    
    # Get session
    session = db.query(models.Session).filter(
        models.Session.session_id == request.session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Record attempt
    results = request.results
    attempt = AttemptOperations.record_attempt(
        db,
        session_id=request.session_id,
        student_id=session.student_id,
        module=session.module_id,
        activity=request.activity_type,
        score=results["score"],
        total=results["total"],
        difficulty=request.tuning_settings["difficulty"],
        tuning_settings=request.tuning_settings,
        item_results=results.get("item_results", [])
