# Backend Testing Guide

Comprehensive testing documentation for the backend, including agent tests, API tests, and WebSocket tests.

## Test Structure

### Agent Tests (test_agents.py)
Unit tests for the LLM-powered agents (Tutor and Activity agents).

### API Tests (TODO)
Tests for REST API endpoints.

### WebSocket Tests (TODO)
Tests for WebSocket communication.

### Integration Tests (TODO)
End-to-end tests for complete workflows.

## Setup

Install test dependencies:
```bash
pip install -r requirements.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test file
```bash
pytest tests/test_agents.py
```

### Run specific test class
```bash
pytest tests/test_agents.py::TestTutorAgent
```

### Run specific test
```bash
pytest tests/test_agents.py::TestTutorAgent::test_tutor_greeting
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run and see print statements
```bash
pytest -s
```

## Test Structure

### TestTutorAgent
Tests for the general tutor agent that helps students outside of activities:
- `test_tutor_greeting` - Tests greeting responses
- `test_tutor_vocabulary_help` - Tests vocabulary explanations
- `test_tutor_encouragement` - Tests encouragement responses

### TestActivityAgent
Tests for the activity-specific agent that provides hints during exercises:
- `test_activity_start` - Tests welcome message when activity starts
- `test_wrong_answer_first_attempt` - Tests hint for first wrong answer
- `test_wrong_answer_second_attempt` - Tests hint for second wrong answer
- `test_correct_answer` - Tests congratulatory response
- `test_activity_chat` - Tests chat during activity
- `test_activity_end` - Tests feedback at activity completion

### TestAgentManager
Tests for the AgentManager that coordinates between agents:
- `test_agent_manager_creation` - Tests manager initialization
- `test_activity_lifecycle` - Tests complete activity flow
- `test_message_routing` - Tests routing to correct agent

## Requirements

These tests require:
- Valid ANTHROPIC_API_KEY in `.env` file
- MODEL_NAME set to a valid Claude model (e.g., `claude-3-opus-20240229`)
- LLM_PROVIDER set to `anthropic`
- AGENT_TYPE set to `llm`

## Notes

- Tests make real API calls to the LLM, so they may take a few seconds
- Tests will print agent responses when run with `-s` flag
- All tests use assertions to verify responses are valid
- Tests are organized by agent type for clarity
