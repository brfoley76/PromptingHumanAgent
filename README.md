# Agentic Learning System - README

## Overview

This is a **separate, independent agentic platform** that integrates with the learning module to provide AI-powered tutoring and adaptive difficulty services. The agentic platform maintains strict separation of concerns:

- **Learning Module Platform** (Existing): Owns and manages all curriculum, content, and game settings
- **Agentic Platform** (This Project): Provides AI tutoring, performance tracking, and adaptive recommendations

The agentic platform fetches curriculum data on-demand and stores only student performance data - never educational content.

## Features

### Core Capabilities
- **Adaptive Difficulty**: Automatically adjusts activity parameters based on student performance
- **Real-time Tutoring**: AI tutor agent provides guidance and answers questions
- **Activity-Specific Agents**: Specialized agents for each exercise type
- **Performance Tracking**: Detailed analytics on student progress and vocabulary mastery
- **WebSocket Communication**: Real-time bidirectional messaging for immediate feedback

### Agent System
- **Tutor Agent**: Persistent session companion, explains concepts, suggests activities
- **Activity Agents**: Provide hints and feedback during exercises
- **Supervisor Agent**: Routes messages between agents intelligently
- **LangGraph Orchestration**: State management and conversation flow

## Technology Stack

### Backend
- Python 3.11+
- FastAPI (REST API + WebSocket)
- LangGraph (Agent orchestration)
- SQLAlchemy (ORM)
- SQLite (Development database)
- OpenAI GPT-4 (LLM provider)

### Frontend
- Vanilla JavaScript (existing codebase)
- Native WebSocket API
- Minimal additional dependencies

## Quick Start

### Prerequisites
```bash
# Install Python 3.11+
python --version

# Install Node.js 18+ (optional, for tooling)
node --version
```

### Backend Setup

1. **Clone and navigate to project:**
```bash
cd learning_module
```

2. **Set up backend:**
```bash
# Create backend structure
mkdir -p backend/src/{api,agents,database,services,schemas}
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4-turbo-preview
DATABASE_URL=sqlite:///./learning.db
HOST=0.0.0.0
PORT=8000
DEBUG=True
CORS_ORIGINS=http://localhost:8000,http://localhost:3000

# Learning Module Platform Integration
# Option 1: Use filesystem access (simpler for demo)
LEARNING_MODULE_PATH=../learning_module/web/data

# Option 2: Use HTTP API (if Learning Module exposes endpoints)
# LEARNING_MODULE_URL=http://localhost:8001
EOF
```

4. **Initialize database:**
```bash
python init_db.py
```

5. **Start backend server:**
```bash
python -m src.main
# Or: uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend Integration

1. **Serve frontend:**
```bash
cd ../web
python3 -m http.server 8000
```

2. **Access application:**
- Open browser to `http://localhost:8000`
- New chat widget and session management will appear

## Project Structure

```
learning_module/
├── backend/                      # AGENTIC PLATFORM (This Project)
│   ├── src/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── api/
│   │   │   ├── routes.py        # REST endpoints
│   │   │   └── websocket.py     # WebSocket handler
│   │   ├── agents/
│   │   │   ├── graph.py         # LangGraph orchestration
│   │   │   ├── tutor.py         # Tutor agent
│   │   │   ├── activity.py      # Activity agents
│   │   │   └── prompts.py       # Agent prompts
│   │   ├── database/
│   │   │   ├── models.py        # SQLAlchemy models (performance data only)
│   │   │   ├── database.py      # DB connection
│   │   │   └── operations.py    # CRUD operations
│   │   ├── services/
│   │   │   ├── adaptive.py      # Adaptive difficulty
│   │   │   ├── curriculum.py    # Curriculum fetching (NOT storage)
│   │   │   └── analytics.py     # Performance analytics
│   │   └── schemas/
│   │       └── session.py       # Pydantic models
│   ├── tests/
│   ├── requirements.txt
│   ├── init_db.py
│   └── .env
└── web/                          # LEARNING MODULE PLATFORM (Existing)
    ├── index.html
    ├── js/
    │   ├── agent/               # NEW: Agent integration
    │   │   ├── SessionManager.js
    │   │   ├── ChatWidget.js
    │   │   └── WebSocketClient.js
    │   └── ...
    └── data/                     # CURRICULUM OWNERSHIP
        └── r003.1.json          # Curriculum (owned by Learning Module)
```

**Key Separation:**
- Agentic Platform (Port 8000): Performance tracking, AI agents, adaptive recommendations
- Learning Module Platform (Port 8001 or filesystem): Curriculum content, game logic, assets

## API Documentation

### REST Endpoints

#### Initialize Session
```http
POST /api/session/init
Content-Type: application/json

{
  "student_id": "optional-uuid",  // If existing student
  "name": "Student Name"          // If new student
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "student_id": "uuid",
  "student_name": "Student Name",
  "module_id": "r003.1",
  "available_activities": ["multiple_choice", "spelling"],
  "tutor_greeting": "Ahoy, Student Name! Ready for adventure?",
  "curriculum_module": {...}
}
```

#### Start Activity
```http
POST /api/activity/start
Content-Type: application/json

{
  "session_id": "uuid",
  "activity_type": "spelling"
}
```

**Response:**
```json
{
  "activity_type": "spelling",
  "recommended_tuning": {
    "difficulty": "medium",
    "num_questions": 10,
    "hint_availability": "after_2_attempts"
  },
  "agent_intro": "Let's try spelling! I've set it to medium difficulty.",
  "vocabulary_focus": ["pirate", "treasure", "ship"]
}
```

#### End Activity
```http
POST /api/activity/end
Content-Type: application/json

{
  "session_id": "uuid",
  "activity_type": "spelling",
  "results": {
    "score": 8,
    "total": 10,
    "item_results": [
      {"word": "pirate", "user_answer": "pirate", "correct": true},
      {"word": "treasure", "user_answer": "tresure", "correct": false}
    ]
  },
  "tuning_settings": {...}
}
```

### WebSocket Communication

#### Connect
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{session_id}');
```

#### Message Types

**Student Chat Message:**
```json
{
  "type": "chat",
  "sender": "student",
  "message": "What does pirate mean?"
}
```

**Agent Response:**
```json
{
  "type": "chat",
  "sender": "agent",
  "agent_type": "tutor",
  "message": "A pirate is a person who steals from ships at sea!"
}
```

**Game Event:**
```json
{
  "type": "game_event",
  "event": "wrong_answer",
  "context": {
    "question": "What is a pirate?",
    "student_answer": "A bird",
    "correct_answer": "A person who steals from ships"
  }
}
```

**Hint Request:**
```json
{
  "type": "hint_request",
  "context": {
    "current_question": {...},
    "attempts": 2
  }
}
```

## Database Schema

### Agentic Platform Database (Performance Data Only)

**Students Table:**
- `student_id` (UUID, PK)
- `name` (String)
- `grade_level` (Integer, default: 3)
- `created_at` (Timestamp)

**Sessions Table:**
- `session_id` (UUID, PK)
- `student_id` (UUID, FK)
- `start_time` (Timestamp)
- `end_time` (Timestamp, nullable)
- `module_id` (String) - References Learning Module curriculum

**Activity Attempts Table:**
- `attempt_id` (UUID, PK)
- `session_id` (UUID, FK)
- `student_id` (UUID, FK)
- `date` (Timestamp)
- `module` (String) - References Learning Module
- `activity` (String) - References Learning Module activity type
- `score` (Integer)
- `total` (Integer)
- `difficulty` (String)
- `tuning_settings` (JSON) - Activity-specific parameters
- `item_results` (JSON) - Per-item success/failure

**Chat Messages Table:**
- `message_id` (UUID, PK)
- `session_id` (UUID, FK)
- `agent_type` (String)
- `sender` (String)
- `message` (String)
- `timestamp` (Timestamp)

**Note:** No curriculum content is stored in this database. All educational content resides in the Learning Module Platform.

## Adaptive Difficulty System

### Tuning Settings

Each activity has customizable parameters stored in `tuning_settings` JSON:

**Multiple Choice:**
```json
{
  "difficulty": "easy|medium|hard",
  "num_questions": 5-20,
  "num_choices": 3-5,
  "time_limit": null|60|120
}
```

**Spelling:**
```json
{
  "difficulty": "easy|medium|hard",
  "num_questions": 5-20,
  "hint_availability": "always|after_1_attempt|after_2_attempts|never"
}
```

**Bubble Pop:**
```json
{
  "difficulty": "easy|moderate|hard",
  "bubble_speed": 0.5-2.0,
  "error_rate": 0.0-0.5,
  "game_mode": "correct_only|incorrect_only|both",
  "initial_delay": 1000-3000,
  "min_delay": 300-1000,
  "ramp_rate": 25-100
}
```

### Algorithm

The system analyzes recent performance to adjust difficulty:

1. **Collect History**: Last 5 attempts for the activity
2. **Calculate Accuracy**: Average score percentage
3. **Determine Tier**:
   - \> 85% accuracy → Hard difficulty
   - 65-85% accuracy → Moderate difficulty
   - < 65% accuracy → Easy difficulty
4. **Adjust Parameters**: Modify speed, complexity, time limits
5. **Apply Tuning**: Send recommendations to frontend

## Development

### Running Tests
```bash
cd backend
pytest tests/
```

### Code Quality
```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### API Documentation
When server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Platform Integration

### Curriculum Access Patterns

The agentic platform can access Learning Module curriculum in two ways:

**Option 1: Filesystem Access (Simpler for Demo)**
```python
# In .env
LEARNING_MODULE_PATH=../learning_module/web/data

# The CurriculumService reads JSON files directly
curriculum = CurriculumService.load_curriculum("r003.1")
# Reads from: ../learning_module/web/data/r003.1.json
```

**Option 2: HTTP API (Production-Ready)**
```python
# In .env  
LEARNING_MODULE_URL=http://localhost:8001

# The CurriculumService makes HTTP requests
curriculum = CurriculumService.load_curriculum("r003.1")
# Fetches from: http://localhost:8001/curriculum/r003.1
```

### Data Ownership

| Data Type | Owner | Storage Location |
|-----------|-------|------------------|
| Curriculum Content | Learning Module | `web/data/*.json` |
| Game Assets | Learning Module | `web/game_assets/` |
| Activity Settings | Learning Module | `web/data/*.json` |
| Student Performance | Agentic Platform | `backend/learning.db` |
| Chat History | Agentic Platform | `backend/learning.db` |
| AI Agent State | Agentic Platform | Memory/Cache |

### Integration Flow

1. **Session Init**: Agentic Platform fetches curriculum from Learning Module
2. **Activity Start**: Agentic Platform sends tuning recommendations to frontend
3. **During Activity**: Learning Module manages game logic, Agentic Platform provides hints
4. **Activity End**: Results sent to Agentic Platform for analysis, Learning Module updates progress

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `MODEL_NAME` | LLM model to use | gpt-4-turbo-preview |
| `DATABASE_URL` | Agentic Platform database | sqlite:///./learning.db |
| `HOST` | Server host | 0.0.0.0 |
| `PORT` | Agentic Platform port | 8000 |
| `DEBUG` | Debug mode | True |
| `CORS_ORIGINS` | Allowed CORS origins | localhost:8000,localhost:3000 |
| `LEARNING_MODULE_PATH` | Path to curriculum files | ../learning_module/web/data |
| `LEARNING_MODULE_URL` | Learning Module API URL | None (uses filesystem) |

### LLM Provider

To use a different LLM provider:

1. Install appropriate package:
```bash
pip install langchain-anthropic  # For Claude
# OR
pip install langchain-community  # For local models
```

2. Update `src/agents/graph.py`:
```python
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-3-opus-20240229")
```

3. Update `.env`:
```bash
ANTHROPIC_API_KEY=your_key_here
```

## Deployment

### Production Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `DEBUG=False`
- [ ] Use proper secret management (not .env)
- [ ] Enable HTTPS/WSS
- [ ] Set up Redis for session management
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Enable logging to external service
- [ ] Use load balancer for multiple instances
- [ ] Set up CI/CD pipeline
- [ ] Configure database backups

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY init_db.py .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/learning
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=pass
      - POSTGRES_USER=user
      - POSTGRES_DB=learning
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Troubleshooting

### Common Issues

**WebSocket Connection Failed:**
- Check CORS settings in backend
- Verify session_id is valid
- Ensure backend is running

**Database Errors:**
- Run `python init_db.py` to initialize
- Check DATABASE_URL in .env
- Verify file permissions for SQLite

**LLM API Errors:**
- Verify API key is correct
- Check API quota/rate limits
- Ensure model name is valid

**Slow Response Times:**
- Check network latency to LLM provider
- Review database query performance
- Consider caching responses

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style
- Follow PEP 8 for Python
- Use type hints
- Add docstrings for functions
- Write tests for new features
- Update documentation

## License

This project is part of the PromptingHumans educational initiative.

## Support

For issues, questions, or feedback:
- GitHub Issues: [repository]/issues
- Email: support@promptinghumans.example
- Documentation: See ARCHITECTURE.md and IMPLEMENTATION_PLAN.md

## Acknowledgments

- LangChain/LangGraph for agent framework
- FastAPI for web framework
- OpenAI for LLM capabilities
- Original learning module contributors
