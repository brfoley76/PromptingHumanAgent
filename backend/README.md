# Agentic Learning Platform - Backend

This is the backend implementation of the Agentic Learning Platform, featuring a terminal-based test client for the multiplication quiz.

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run Terminal Test

```bash
python test_terminal.py
```

This will:
- Initialize the database (`learning.db`)
- Prompt for your name
- Present 5 multiplication problems
- Use Socratic dialogue when you make mistakes
- Save your results to the database

## Features

### Terminal Test Client
- **Interactive Quiz**: 5 multiplication problems with varying difficulty
- **Socratic Dialogue**: When you make an error, the agent:
  1. Acknowledges the mistake
  2. Asks you to explain your reasoning
  3. Provides a context-aware hint
  4. Allows one retry per question
  5. Provides full explanation if still incorrect
- **Real Database**: Stores student profiles, sessions, and performance data
- **Real Services**: Uses the actual CurriculumService and activity logic

### Components Built

#### Database Layer (`src/database/`)
- `models.py`: SQLAlchemy models for Student, Session, ActivityAttempt, ChatMessage
- `database.py`: Database connection and initialization
- Uses SQLite for development (production-ready for PostgreSQL)

#### Services (`src/services/`)
- `curriculum.py`: CurriculumService - fetches curriculum from Learning Module
- `activity.py`: MultiplicationActivity - handles quiz logic and scoring

#### Agents (`src/agents/`)
- `simple_agent.py`: Rule-based agent (no LLM API required)
  - Provides contextual hints from curriculum
  - Socratic questioning
  - Adaptive responses based on error magnitude
- `llm_agent.py`: LLM-powered agent (OpenAI GPT-4 or Anthropic Claude)
  - Dynamic, natural language responses
  - Curriculum-aware context
  - Intelligent error analysis
  - See [LLM_SETUP.md](LLM_SETUP.md) for setup instructions
- `agent_factory.py`: Factory for creating agents with automatic fallback

#### Test Data (`test_data/`)
- `multiplication_module.json`: Sample curriculum in Learning Module format
  - 5 multiplication problems
  - Mix of 1-digit × 1-digit and 1-digit × 2-digit
  - Includes hints and explanations

## Architecture

### Separation of Concerns

This backend follows the documented architecture with strict separation:

```
┌─────────────────────────────────────┐
│ Terminal Client (test_terminal.py) │  ← Thin UI layer
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ Backend Services                    │  ← Business logic
│ - CurriculumService                 │
│ - ActivityService                   │
│ - Database                          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ Learning Module (test_data/)       │  ← Curriculum content
│ - multiplication_module.json       │
└─────────────────────────────────────┘
```

### Database Schema

```sql
students
  - student_id (UUID, PK)
  - name
  - grade_level
  - created_at

sessions
  - session_id (UUID, PK)
  - student_id (FK)
  - module_id (references curriculum)
  - start_time, end_time

activity_attempts
  - attempt_id (UUID, PK)
  - session_id (FK)
  - student_id (FK)
  - activity, module
  - score, total
  - tuning_settings (JSON)
  - item_results (JSON)

chat_messages
  - message_id (UUID, PK)
  - session_id (FK)
  - agent_type, sender
  - message, timestamp
```

## Example Session

```
$ python test_terminal.py

Initializing database...
Database initialized at: .../backend/learning.db

============================================================
Multiplication Practice
============================================================

Welcome! What's your name? Alice

Nice to meet you, Alice!

🤖 Agent: Hi Alice! Today we'll be studying multiplication! 
I'll give you 5 problems. Let's see how you do!

Press Enter to start...

────────────────────────────────────────────────────────────

Question 1 of 5

What is 3 × 4? 12
✓ Excellent! That's correct!

Score: 1/1

────────────────────────────────────────────────────────────

Question 2 of 5

What is 7 × 8? 54

🤖 Agent: Hmm, I got a different answer. Let's think about this together.

🤖 Agent: Can you tell me how you calculated 7 × 8 = 54?
> I multiplied them

🤖 Agent: I see! Let me give you a hint: Try 7 × 10 and subtract 7 × 2

Let's try again. What is 7 × 8? 56
✓ Great work figuring that out!

Score: 2/2

[... continues for 5 problems ...]

────────────────────────────────────────────────────────────
============================================================
Final Results
============================================================

You got 4 out of 5 correct!
That's 80.0%!

🤖 Agent: Excellent work, Alice! You got 4 out of 5 correct! 
You're really getting the hang of multiplication!

Results saved to database!
```

## Testing the System

### Run the Terminal Quiz
```bash
python test_terminal.py
```

### View the Database
```bash
sqlite3 learning.db
.tables
.schema
SELECT * FROM students;
SELECT * FROM activity_attempts;
```

### Test CurriculumService
```python
from src.services.curriculum import CurriculumService

# Load curriculum
curriculum = CurriculumService.load_curriculum("math_mult_001")
print(curriculum['description'])

# Get problems
problems = CurriculumService.get_problems("math_mult_001")
print(f"Found {len(problems)} problems")
```

## Extending the System

### Add New Curriculum
1. Create a new JSON file in `test_data/`
2. Follow the Learning Module format
3. Use CurriculumService to load it

### Upgrade to Real LLM Agent
Replace `simple_agent.py` with:
```python
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

# Build LangGraph agent
# Keep same interface as SimpleAgent
```

### Add REST API
Add FastAPI routes in `src/api/routes.py` to expose:
- `POST /api/session/init`
- `POST /api/activity/start`
- `POST /api/activity/end`

This allows the web UI to use the same backend.

## Next Steps

1. ✅ Terminal test client working
2. ⏳ Add FastAPI REST endpoints
3. ⏳ Add WebSocket for real-time chat
4. ⏳ Integrate with web UI
5. ⏳ Add more curriculum modules
6. ⏳ Implement adaptive difficulty based on history
7. ⏳ Upgrade to full LangGraph + LLM

## Files Created

```
backend/
├── test_data/
│   └── multiplication_module.json    # Test curriculum
├── src/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                 # Database models
│   │   └── database.py               # DB connection
│   ├── services/
│   │   ├── __init__.py
│   │   ├── curriculum.py             # Curriculum fetching
│   │   └── activity.py               # Activity logic
│   └── agents/
│       └── simple_agent.py           # Rule-based agent
├── test_terminal.py                  # Terminal UI
├── requirements.txt                  # Dependencies
└── learning.db                       # Database (created on first run)
```

## Design Principles Validated

✅ **Separation of Concerns**: Learning Module owns content, Backend provides intelligence
✅ **Modular**: Clean service separation, easy to extend
✅ **Scalable**: Works with any curriculum in Learning Module format
✅ **Production-Ready**: Real database, proper models, clean architecture
✅ **Testable**: Terminal client tests the real system

This implementation follows the documented architecture and can scale to the full web-based system!
