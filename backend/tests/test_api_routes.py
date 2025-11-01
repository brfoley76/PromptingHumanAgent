"""
Unit tests for API routes
Run with: pytest tests/test_api_routes.py -v
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.database.database import init_db, get_db
from src.database.operations import DatabaseOperations

client = TestClient(app)


class TestHealthEndpoints:
    """Test suite for health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Agentic Learning Platform" in data["message"]
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestSessionEndpoints:
    """Test suite for session management endpoints"""
    
    def test_session_init_new_student(self):
        """Test initializing session for new student"""
        response = client.post(
            "/api/session/init",
            json={
                "username": "test_student_new",
                "module_id": "r003.1"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "student_id" in data
        assert "student_name" in data
        assert data["student_name"] == "test_student_new"
        assert "module_id" in data
        assert data["module_id"] == "r003.1"
        assert "available_activities" in data
        assert "tutor_greeting" in data
        assert "curriculum_module" in data
        assert "progress" in data
        assert "is_returning_student" in data
        
        # New student should not be returning
        assert data["is_returning_student"] is False
    
    def test_session_init_returning_student(self):
        """Test initializing session for returning student"""
        # First create a student
        response1 = client.post(
            "/api/session/init",
            json={
                "username": "test_returning",
                "module_id": "r003.1"
            }
        )
        assert response1.status_code == 200
        
        # Then initialize another session for same student
        response2 = client.post(
            "/api/session/init",
            json={
                "username": "test_returning",
                "module_id": "r003.1"
            }
        )
        assert response2.status_code == 200
        data = response2.json()
        
        # Should be marked as returning student
        assert data["is_returning_student"] is True
        assert data["student_name"] == "test_returning"
    
    def test_session_init_invalid_username(self):
        """Test session init with invalid username"""
        response = client.post(
            "/api/session/init",
            json={
                "username": "test user!",  # Invalid: contains space and special char
                "module_id": "r003.1"
            }
        )
        assert response.status_code == 400
        assert "alphanumeric" in response.json()["detail"].lower()
    
    def test_session_init_invalid_module(self):
        """Test session init with non-existent module"""
        response = client.post(
            "/api/session/init",
            json={
                "username": "testuser",
                "module_id": "nonexistent_module"
            }
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_session_end(self):
        """Test ending a session"""
        # First create a session
        init_response = client.post(
            "/api/session/init",
            json={
                "username": "test_end_session",
                "module_id": "r003.1"
            }
        )
        assert init_response.status_code == 200
        session_id = init_response.json()["session_id"]
        
        # Then end it
        end_response = client.post(
            "/api/session/end",
            json={"session_id": session_id}
        )
        assert end_response.status_code == 200
        data = end_response.json()
        assert data["status"] == "success"
        assert data["session_id"] == session_id
    
    def test_session_end_invalid_id(self):
        """Test ending session with invalid ID"""
        response = client.post(
            "/api/session/end",
            json={"session_id": "invalid-session-id"}
        )
        assert response.status_code == 404


class TestActivityEndpoints:
    """Test suite for activity management endpoints"""
    
    @pytest.fixture
    def session_id(self):
        """Create a session for testing"""
        response = client.post(
            "/api/session/init",
            json={
                "username": "test_activity_user",
                "module_id": "r003.1"
            }
        )
        return response.json()["session_id"]
    
    def test_activity_start(self, session_id):
        """Test starting an activity"""
        response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "activity_type" in data
        assert data["activity_type"] == "multiple_choice"
        assert "recommended_tuning" in data
        assert "agent_intro" in data
        assert "vocabulary_focus" in data
        
        # Check tuning has expected fields
        tuning = data["recommended_tuning"]
        assert "difficulty" in tuning
        assert "num_questions" in tuning
    
    def test_activity_start_invalid_session(self):
        """Test starting activity with invalid session"""
        response = client.post(
            "/api/activity/start",
            json={
                "session_id": "invalid-session",
                "activity_type": "multiple_choice"
            }
        )
        assert response.status_code == 404
    
    def test_activity_end(self, session_id):
        """Test ending an activity"""
        # First start an activity
        start_response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice"
            }
        )
        assert start_response.status_code == 200
        
        # Then end it
        end_response = client.post(
            "/api/activity/end",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice",
                "results": {
                    "score": 8,
                    "total": 10,
                    "item_results": []
                },
                "tuning_settings": {
                    "difficulty": "4",
                    "num_questions": 10
                }
            }
        )
        assert end_response.status_code == 200
        data = end_response.json()
        
        # Verify response structure
        assert "feedback" in data
        assert "profile_update" in data
        assert "next_recommendation" in data
        assert "unlocked_activities" in data
        
        # Check profile update
        assert "overall_accuracy" in data["profile_update"]
        assert data["profile_update"]["overall_accuracy"] == 80.0
    
    def test_activity_end_with_unlock(self, session_id):
        """Test ending activity with high score triggers unlock"""
        # End activity with high score on hard difficulty
        response = client.post(
            "/api/activity/end",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice",
                "results": {
                    "score": 9,
                    "total": 10,
                    "item_results": []
                },
                "tuning_settings": {
                    "difficulty": "5",  # Hard difficulty for multiple choice
                    "num_questions": 10
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should unlock next activity
        assert len(data["unlocked_activities"]) > 0
        assert "fill_in_the_blank" in data["unlocked_activities"]
    
    def test_activity_end_no_unlock(self, session_id):
        """Test ending activity with low score doesn't unlock"""
        response = client.post(
            "/api/activity/end",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice",
                "results": {
                    "score": 5,
                    "total": 10,
                    "item_results": []
                },
                "tuning_settings": {
                    "difficulty": "3",
                    "num_questions": 10
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should not unlock
        assert len(data["unlocked_activities"]) == 0


class TestAdaptiveDifficulty:
    """Test suite for adaptive difficulty tuning"""
    
    @pytest.fixture
    def session_with_history(self):
        """Create a session and record some attempts"""
        # Create session
        init_response = client.post(
            "/api/session/init",
            json={
                "username": "test_adaptive_user",
                "module_id": "r003.1"
            }
        )
        session_id = init_response.json()["session_id"]
        
        # Record some attempts with varying scores
        for score in [7, 8, 9, 8, 9]:  # Average ~82%
            client.post(
                "/api/activity/end",
                json={
                    "session_id": session_id,
                    "activity_type": "spelling",
                    "results": {
                        "score": score,
                        "total": 10,
                        "item_results": []
                    },
                    "tuning_settings": {
                        "difficulty": "easy",
                        "num_questions": 10
                    }
                }
            )
        
        return session_id
    
    def test_difficulty_increases_with_performance(self, session_with_history):
        """Test that difficulty increases after good performance"""
        response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_with_history,
                "activity_type": "spelling"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # With ~82% average, should recommend medium or hard
        tuning = data["recommended_tuning"]
        assert tuning["difficulty"] in ["medium", "hard"]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
