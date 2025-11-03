# Learning Module ↔ Agentic Platform Integration Interface

## Overview

This document defines the integration interface between the **Learning Module Platform** (owns curriculum and content) and the **Agentic Platform** (provides AI tutoring and analytics).

## Design Principles

1. **Strict Separation**: Each platform owns its data domain
2. **Curriculum Ownership**: Learning Module is the single source of truth for all educational content
3. **Performance Ownership**: Agentic Platform is the single source of truth for student performance data
4. **Loose Coupling**: Platforms can evolve independently
5. **Multiple Integration Options**: Support both filesystem and API-based integration

---

## Integration Options

### Option 1: Filesystem-Based (Development/Demo)

**Use Case**: Single-server deployment, simpler setup

**Configuration**:
```env
LEARNING_MODULE_PATH=../learning_module/web/data
```

**Access Pattern**:
- Agentic Platform reads curriculum JSON files directly from filesystem
- No HTTP server required for Learning Module
- Suitable for development and single-machine demos

**Pros**: Simple, no network overhead
**Cons**: Requires shared filesystem, not suitable for distributed deployment

---

### Option 2: HTTP API-Based (Production)

**Use Case**: Distributed deployment, microservices architecture

**Configuration**:
```env
LEARNING_MODULE_URL=http://learning-module:8001
```

**Access Pattern**:
- Learning Module exposes REST API for curriculum access
- Agentic Platform makes HTTP requests
- Supports distributed deployment

**Pros**: Scalable, supports microservices, better security
**Cons**: Requires Learning Module to expose API, network latency

---

## Data Ownership Matrix

| Data Domain | Owner | Storage Location | Access Pattern |
|-------------|-------|------------------|----------------|
| **Curriculum Content** | Learning Module | `web/data/*.json` | Agentic fetches read-only |
| **Vocabulary** | Learning Module | `web/data/*.json` | Agentic fetches read-only |
| **Narrative Text** | Learning Module | `web/data/*.json` | Agentic fetches read-only |
| **Exercise Definitions** | Learning Module | `web/data/*.json` | Agentic fetches read-only |
| **Game Assets** | Learning Module | `web/game_assets/` | Agentic never accesses |
| **Activity Settings** | Learning Module | `web/data/*.json` | Agentic fetches read-only |
| **Student Profiles** | Agentic Platform | `backend/learning.db` | Learning Module never accesses |
| **Performance History** | Agentic Platform | `backend/learning.db` | Learning Module never accesses |
| **Chat Logs** | Agentic Platform | `backend/learning.db` | Learning Module never accesses |
| **Tuning Recommendations** | Agentic Platform | Generated on-demand | Sent to frontend, never persisted |

---

## Learning Module Platform API Specification

### Curriculum Endpoints

If Learning Module exposes HTTP API, it should implement these endpoints:

#### Get Full Curriculum Module
```http
GET /curriculum/{module_id}

Response: 200 OK
{
  "description": "string",
  "id": "string",
  "dependencies": "string | null",
  "subject": "string",
  "exercises": ["string"],
  "content": {
    "vocabulary": [...],
    "narrative": {...}
  }
}
```

**Example**:
```bash
GET /curriculum/r003.1
```

#### Get Vocabulary Only
```http
GET /curriculum/{module_id}/vocabulary

Response: 200 OK
[
  {
    "word": "pirate",
    "definition": "a person who steals from ships at sea",
    "fitb": "A {blank} is "
  },
  ...
]
```

#### Get Narrative Only
```http
GET /curriculum/{module_id}/narrative

Response: 200 OK
{
  "0": {"text": "It was Lucy's first day...", "flag": "{checkpoint}"},
  "1": {"text": "new job on a {pirate} ship.", "vocab": "parrot"},
  ...
}
```

#### Get Exercise Settings
```http
GET /curriculum/{module_id}/exercise-settings

Response: 200 OK
{
  "multiple_choice": {
    "available_difficulties": ["easy", "medium", "hard"],
    "question_counts": [5, 10, 15, 20],
    "choice_counts": [3, 4, 5]
  },
  "spelling": {
    "available_difficulties": ["easy", "medium", "hard"],
    "question_counts": [5, 10, 15, 20]
  },
  ...
}
```

### Error Responses
```http
404 Not Found
{
  "error": "Curriculum module not found",
  "module_id": "r003.1"
}

500 Internal Server Error
{
  "error": "Failed to load curriculum"
}
```

---

## Agentic Platform API Specification

### Session Management

#### Initialize Session
```http
POST /api/session/init
Content-Type: application/json

Request:
{
  "student_id": "uuid | null",  // Existing student
  "name": "string | null"        // New student
}

Response: 200 OK
{
  "session_id": "uuid",
  "student_id": "uuid",
  "student_name": "string",
  "module_id": "string",
  "available_activities": ["string"],
  "tutor_greeting": "string",
  "curriculum_module": {...}     // Fetched from Learning Module
}
```

#### End Session
```http
POST /api/session/end
Content-Type: application/json

Request:
{
  "session_id": "uuid"
}

Response: 200 OK
{
  "status": "success",
  "message": "Session ended"
}
```

### Activity Management

#### Start Activity
```http
POST /api/activity/start
Content-Type: application/json

Request:
{
  "session_id": "uuid",
  "activity_type": "string"  // e.g., "spelling", "bubble_pop"
}

Response: 200 OK
{
  "activity_type": "string",
  "recommended_tuning": {
    "difficulty": "string",
    "num_questions": "number",
    ... // Activity-specific parameters
  },
  "agent_intro": "string",
  "vocabulary_focus": ["string"]  // Words to emphasize
}
```

#### End Activity
```http
POST /api/activity/end
Content-Type: application/json

Request:
{
  "session_id": "uuid",
  "activity_type": "string",
  "results": {
    "score": "number",
    "total": "number",
    "item_results": [
      {
        "word": "string",
        "user_answer": "string",
        "correct": "boolean"
      }
    ]
  },
  "tuning_settings": {...}  // Settings that were used
}

Response: 200 OK
{
  "feedback": "string",          // Agent feedback on performance
  "profile_update": {
    "overall_accuracy": "number",
    "mastery_improved": ["string"]
  },
  "next_recommendation": {
    "suggested_activity": "string",
    "suggested_difficulty": "string",
    "reason": "string"
  },
  "unlocked_activities": ["string"]  // May have unlocked new activities
}
```

### WebSocket Communication

#### Connect
```
ws://localhost:8000/ws/{session_id}
```

#### Message Types

**Chat Message (Student → Agent)**:
```json
{
  "type": "chat",
  "sender": "student",
  "message": "What does pirate mean?"
}
```

**Chat Response (Agent → Student)**:
```json
{
  "type": "chat",
  "sender": "agent",
  "agent_type": "tutor",
  "message": "A pirate is a person who steals from ships at sea!"
}
```

**Game Event (Learning Module → Agent)**:
```json
{
  "type": "game_event",
  "event": "wrong_answer",
  "context": {
    "activity": "spelling",
    "word": "pirate",
    "user_answer": "pirat",
    "correct_answer": "pirate",
    "attempts": 1
  }
}
```

**Hint Request (Student → Agent)**:
```json
{
  "type": "hint_request",
  "context": {
    "activity": "spelling",
    "word": "treasure",
    "attempts": 2
  }
}
```

**Hint Response (Agent → Student)**:
```json
{
  "type": "hint",
  "hint": "Remember, treasure has two 'e's! Think about the word 'measure'.",
  "hint_level": "medium"  // subtle, medium, explicit
}
```

---

## Frontend Integration Pattern

The frontend acts as the coordinator between both platforms:

```javascript
// Session initialization
async function initSession(studentName) {
  // 1. Call Agentic Platform to init session
  const response = await fetch('http://localhost:8000/api/session/init', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: studentName})
  });
  
  const session = await response.json();
  
  // 2. Store session data locally
  this.sessionId = session.session_id;
  this.curriculum = session.curriculum_module;  // From Learning Module
  
  // 3. Connect WebSocket to Agentic Platform
  this.ws = new WebSocket(`ws://localhost:8000/ws/${this.sessionId}`);
  
  // 4. Display tutor greeting
  this.displayMessage(session.tutor_greeting);
}

// Activity start
async function startActivity(activityType) {
  // 1. Get tuning recommendations from Agentic Platform
  const response = await fetch('http://localhost:8000/api/activity/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      session_id: this.sessionId,
      activity_type: activityType
    })
  });
  
  const config = await response.json();
  
  // 2. Apply tuning to Learning Module activity
  this.activityManager.startActivity(activityType, config.recommended_tuning);
  
  // 3. Display agent intro
  this.displayMessage(config.agent_intro);
}

// During activity - send game events
function onStudentError(word, userAnswer, correctAnswer) {
  // Send to Agentic Platform via WebSocket
  this.ws.send(JSON.stringify({
    type: 'game_event',
    event: 'wrong_answer',
    context: {
      activity: this.currentActivity,
      word: word,
      user_answer: userAnswer,
      correct_answer: correctAnswer
    }
  }));
}

// Activity end
async function endActivity(results) {
  // 1. Submit results to Agentic Platform
  const response = await fetch('http://localhost:8000/api/activity/end', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      session_id: this.sessionId,
      activity_type: this.currentActivity,
      results: results,
      tuning_settings: this.currentTuning
    })
  });
  
  const feedback = await response.json();
  
  // 2. Update UI with feedback
  this.displayFeedback(feedback.feedback);
  
  // 3. Update local progress (Learning Module manages unlock state)
  this.scoreManager.updateProgress(results);
}
```

---

## Curriculum Data Format

### Standard Module Structure

```json
{
  "description": "string",
  "id": "string",
  "dependencies": "string | null",
  "subject": "string",
  "exercises": ["string"],  // Available exercise types
  "content": {
    "vocabulary": [
      {
        "word": "string",
        "definition": "string",
        "fitb": "string"  // Fill-in-the-blank template
      }
    ],
    "narrative": {
      "0": {
        "text": "string",
        "flag": "string | undefined",      // e.g., "{checkpoint}"
        "vocab": "string | undefined",     // Vocabulary variant
        "spelling": "string | undefined"   // Spelling variant
      }
    }
  }
}
```

### Vocabulary Entry Requirements

Each vocabulary entry must include:
- `word`: The target vocabulary word
- `definition`: Clear, grade-appropriate definition
- `fitb`: Fill-in-the-blank sentence template with `{blank}` placeholder

### Narrative Entry Options

Each narrative fragment can include:
- `text`: The narrative text (required)
- `flag`: Special markers like `{checkpoint}`
- `vocab`: Alternative word for vocabulary variant
- `spelling`: Misspelled word for spelling variant
- `variant`: Canonical marker for base text

---

## Caching Strategy

### Agentic Platform Caching

The Agentic Platform implements a session-scoped cache:

```python
class CurriculumService:
    _cache: Dict[str, Dict] = {}  # In-memory cache
    
    @staticmethod
    def load_curriculum(module_id: str, use_cache: bool = True) -> Dict:
        # Check cache first
        if use_cache and module_id in CurriculumService._cache:
            return CurriculumService._cache[module_id]
        
        # Fetch from Learning Module
        curriculum = fetch_from_learning_module(module_id)
        
        # Cache for session duration
        CurriculumService._cache[module_id] = curriculum
        return curriculum
    
    @staticmethod
    def clear_cache(module_id: Optional[str] = None):
        # Clear on session end or module update
        if module_id:
            CurriculumService._cache.pop(module_id, None)
        else:
            CurriculumService._cache.clear()
```

**Cache Invalidation**:
- Session end: Clear session-specific cached data
- Module update: Learning Module notifies or Agentic Platform polls for changes
- Memory limits: Implement LRU eviction if needed

---

## Error Handling

### Curriculum Not Found

```python
# Agentic Platform behavior
try:
    curriculum = CurriculumService.load_curriculum(module_id)
except FileNotFoundError:
    return {
        "error": "Curriculum module not found",
        "module_id": module_id,
        "fallback": "use_default_content"
    }
```

### Learning Module Unavailable

```python
# Agentic Platform behavior
try:
    curriculum = fetch_via_api(module_id)
except requests.exceptions.ConnectionError:
    # Fall back to cached version if available
    if module_id in CurriculumService._cache:
        return CurriculumService._cache[module_id]
    # Or return error
    raise ServiceUnavailableError("Learning Module platform unavailable")
```

---

## Security Considerations

### Cross-Platform Access

1. **Authentication**: Frontend authenticates with Agentic Platform only
2. **Authorization**: Agentic Platform validates all requests
3. **CORS**: Both platforms configure appropriate CORS headers
4. **API Keys**: If using HTTP API, implement API key authentication

### Data Privacy

1. **Student Data**: Only Agentic Platform stores student information
2. **Curriculum Access**: Read-only, no modification allowed
3. **Logging**: Sensitive student data never logged by Learning Module

---

## Deployment Scenarios

### Scenario 1: Local Development
```
┌─────────────────────────────────────┐
│  Laptop                             │
│  ┌──────────────┐  ┌──────────────┐│
│  │ Learning     │  │ Agentic      ││
│  │ Module       │◄─┤ Platform     ││
│  │ (filesystem) │  │ (Port 8000)  ││
│  └──────────────┘  └──────────────┘│
│         ▲                           │
│         │                           │
│    ┌────┴─────┐                    │
│    │ Browser  │                    │
│    └──────────┘                    │
└─────────────────────────────────────┘
```

### Scenario 2: Production Deployment
```
┌─────────────────────────────────────────────┐
│  Cloud Infrastructure                       │
│  ┌──────────────┐        ┌──────────────┐  │
│  │ Learning     │◄───────┤ Agentic      │  │
│  │ Module       │  HTTP  │ Platform     │  │
│  │ (Port 8001)  │        │ (Port 8000)  │  │
│  └──────────────┘        └──────────────┘  │
│         ▲                        ▲          │
│         │                        │          │
│         └────────────┬───────────┘          │
│                      │                      │
└──────────────────────┼──────────────────────┘
                       │
                  ┌────┴─────┐
                  │  CDN /   │
                  │  Load    │
                  │  Balancer│
                  └──────────┘
                       ▲
                       │
                  ┌────┴─────┐
                  │ Browsers │
                  └──────────┘
```

---

## Testing Integration

### Unit Tests

**Learning Module**:
- Test curriculum JSON validation
- Test API endpoint responses (if applicable)
- Mock Agentic Platform requests

**Agentic Platform**:
- Mock Learning Module responses
- Test cache behavior
- Test fallback mechanisms

### Integration Tests

```python
# Test curriculum fetching
def test_curriculum_integration():
    # Setup: Create test curriculum file
    test_curriculum = {
        "id": "test_module",
        "content": {"vocabulary": [...]}
    }
    
    # Test: Fetch via filesystem
    curriculum = CurriculumService.load_curriculum("test_module")
    assert curriculum["id"] == "test_module"
    
    # Test: Verify caching
    curriculum2 = CurriculumService.load_curriculum("test_module")
    assert curriculum is curriculum2  # Same object

# Test API integration (if using HTTP)
def test_api_integration():
    # Setup: Mock Learning Module API
    responses.add(
        responses.GET,
        "http://localhost:8001/curriculum/r003.1",
        json=test_curriculum,
        status=200
    )
    
    # Test: Fetch via API
    curriculum = CurriculumService.load_curriculum("r003.1")
    assert curriculum["id"] == "r003.1"
```

---

## Migration Path

### Adding HTTP API to Learning Module

If migrating from filesystem to API:

1. **Implement API endpoints** in Learning Module
2. **Add feature flag** in Agentic Platform:
   ```env
   USE_API=false  # Start with filesystem
   ```
3. **Test both modes** in parallel
4. **Switch flag** to enable API mode:
   ```env
   USE_API=true
   LEARNING_MODULE_URL=http://localhost:8001
   ```
5. **Monitor and validate** behavior matches

---

## Summary

This integration interface ensures:

✅ **Clear Boundaries**: Each platform owns its domain  
✅ **Flexible Integration**: Support multiple deployment patterns  
✅ **Read-Only Access**: Agentic Platform never modifies curriculum  
✅ **Loose Coupling**: Platforms can evolve independently  
✅ **Scalability**: Designed for production deployment  
✅ **Testability**: Clear contracts enable comprehensive testing  

The key principle: **Learning Module owns content, Agentic Platform provides intelligence**.
