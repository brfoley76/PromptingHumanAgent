"""
Integration tests for complete workflows
Tests full frontend + backend integration
Run with: pytest tests/test_integration.py -v
"""
import pytest
import asyncio
import websockets
import json
from fastapi.testclient import TestClient
from src.main import app
from src.database.database import init_db
from src.database.operations import DatabaseOperations

client = TestClient(app)


class TestCompleteUserWorkflow:
    """Test complete user journey from registration to exercise completion"""
    
    def test_new_user_registration_and_first_exercise(self):
        """Test new user registration and completing first exercise"""
        # Step 1: Initialize session (user registration)
        init_response = client.post(
            "/api/session/init",
            json={
                "username": "integration_test_user",
                "module_id": "r003.1"
            }
        )
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify session created
        assert "session_id" in init_data
        assert "student_id" in init_data
        assert init_data["student_name"] == "integration_test_user"
        assert init_data["is_returning_student"] is False
        assert "tutor_greeting" in init_data
        assert len(init_data["available_activities"]) > 0
        
        session_id = init_data["session_id"]
        student_id = init_data["student_id"]
        
        # Step 2: Start first activity (multiple choice)
        start_response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice"
            }
        )
        assert start_response.status_code == 200
        start_data = start_response.json()
        
        # Verify activity started with recommendations
        assert start_data["activity_type"] == "multiple_choice"
        assert "recommended_tuning" in start_data
        assert "agent_intro" in start_data
        assert "vocabulary_focus" in start_data
        
        tuning = start_data["recommended_tuning"]
        assert "difficulty" in tuning
        assert "num_questions" in tuning
        
        # Step 3: Complete activity with good score
        end_response = client.post(
            "/api/activity/end",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice",
                "results": {
                    "score": 9,
                    "total": 10,
                    "item_results": [
                        {"question": i, "correct": i < 9}
                        for i in range(10)
                    ]
                },
                "tuning_settings": tuning
            }
        )
        assert end_response.status_code == 200
        end_data = end_response.json()
        
        # Verify completion feedback
        assert "feedback" in end_data
        assert "profile_update" in end_data
        assert "next_recommendation" in end_data
        assert end_data["profile_update"]["overall_accuracy"] == 90.0
        
        # Step 4: Verify data persisted in database
        student = DatabaseOperations.get_student_by_name("integration_test_user")
        assert student is not None
        assert student.student_id == student_id
        
        # Verify attempt recorded
        history = DatabaseOperations.get_student_performance_history(
            student_id,
            "multiple_choice",
            limit=1
        )
        assert len(history) == 1
        assert history[0].score == 9
        assert history[0].total == 10
        
        # Step 5: End session
        session_end_response = client.post(
            "/api/session/end",
            json={"session_id": session_id}
        )
        assert session_end_response.status_code == 200
    
    def test_returning_user_with_progress(self):
        """Test returning user sees their progress"""
        username = "returning_user_test"
        
        # First session - complete an activity
        init1 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session1_id = init1.json()["session_id"]
        student_id = init1.json()["student_id"]
        
        # Complete activity
        client.post("/api/activity/start", json={
            "session_id": session1_id,
            "activity_type": "multiple_choice"
        })
        
        client.post("/api/activity/end", json={
            "session_id": session1_id,
            "activity_type": "multiple_choice",
            "results": {"score": 8, "total": 10, "item_results": []},
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        client.post("/api/session/end", json={"session_id": session1_id})
        
        # Second session - verify returning user
        init2 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        assert init2.status_code == 200
        init2_data = init2.json()
        
        # Should be marked as returning
        assert init2_data["is_returning_student"] is True
        assert init2_data["student_id"] == student_id
        
        # Should have progress
        assert "progress" in init2_data
        assert init2_data["progress"]["total_attempts"] > 0


class TestAdaptiveDifficulty:
    """Test adaptive difficulty based on performance"""
    
    def test_difficulty_increases_with_good_performance(self):
        """Test that difficulty increases after consistent good performance"""
        username = "adaptive_test_user"
        
        # Initialize session
        init_response = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session_id = init_response.json()["session_id"]
        
        # Complete 5 attempts with high scores
        for i in range(5):
            client.post("/api/activity/start", json={
                "session_id": session_id,
                "activity_type": "spelling"
            })
            
            client.post("/api/activity/end", json={
                "session_id": session_id,
                "activity_type": "spelling",
                "results": {"score": 9, "total": 10, "item_results": []},
                "tuning_settings": {"difficulty": "easy", "num_questions": 10}
            })
        
        # Next start should recommend harder difficulty
        start_response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_id,
                "activity_type": "spelling"
            }
        )
        
        tuning = start_response.json()["recommended_tuning"]
        # With 90% average, should recommend hard or medium
        assert tuning["difficulty"] in ["medium", "hard"]
    
    def test_difficulty_decreases_with_poor_performance(self):
        """Test that difficulty decreases after poor performance"""
        username = "struggling_user_test"
        
        # Initialize session
        init_response = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session_id = init_response.json()["session_id"]
        
        # Complete 5 attempts with low scores
        for i in range(5):
            client.post("/api/activity/start", json={
                "session_id": session_id,
                "activity_type": "spelling"
            })
            
            client.post("/api/activity/end", json={
                "session_id": session_id,
                "activity_type": "spelling",
                "results": {"score": 5, "total": 10, "item_results": []},
                "tuning_settings": {"difficulty": "hard", "num_questions": 10}
            })
        
        # Next start should recommend easier difficulty
        start_response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_id,
                "activity_type": "spelling"
            }
        )
        
        tuning = start_response.json()["recommended_tuning"]
        # With 50% average, should recommend easy
        assert tuning["difficulty"] == "easy"


class TestExerciseUnlocking:
    """Test exercise unlock progression"""
    
    def test_unlock_progression(self):
        """Test that exercises unlock in sequence with good performance"""
        username = "unlock_test_user"
        
        # Initialize session
        init_response = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session_id = init_response.json()["session_id"]
        student_id = init_response.json()["student_id"]
        
        # Complete multiple_choice with high score on hard difficulty
        client.post("/api/activity/start", json={
            "session_id": session_id,
            "activity_type": "multiple_choice"
        })
        
        end_response = client.post("/api/activity/end", json={
            "session_id": session_id,
            "activity_type": "multiple_choice",
            "results": {"score": 9, "total": 10, "item_results": []},
            "tuning_settings": {"difficulty": "5", "num_questions": 10}  # Hard for MC
        })
        
        # Should unlock next exercise
        assert len(end_response.json()["unlocked_activities"]) > 0
        assert "fill_in_the_blank" in end_response.json()["unlocked_activities"]
        
        # Verify unlock persisted
        progress = DatabaseOperations.get_student_progress(student_id)
        assert "fill_in_the_blank" in progress["unlocked_exercises"]


class TestCrossDeviceSync:
    """Test cross-device synchronization"""
    
    def test_progress_syncs_across_devices(self):
        """Test that progress from one device appears on another"""
        username = "multi_device_user"
        
        # Device 1: Complete an activity
        device1_init = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        device1_session = device1_init.json()["session_id"]
        student_id = device1_init.json()["student_id"]
        
        client.post("/api/activity/start", json={
            "session_id": device1_session,
            "activity_type": "multiple_choice"
        })
        
        client.post("/api/activity/end", json={
            "session_id": device1_session,
            "activity_type": "multiple_choice",
            "results": {"score": 8, "total": 10, "item_results": []},
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        client.post("/api/session/end", json={"session_id": device1_session})
        
        # Device 2: Login with same username
        device2_init = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        device2_data = device2_init.json()
        
        # Should see same student_id
        assert device2_data["student_id"] == student_id
        
        # Should see progress from device 1
        assert device2_data["is_returning_student"] is True
        assert device2_data["progress"]["total_attempts"] > 0


class TestErrorHandling:
    """Test error handling in integration scenarios"""
    
    def test_invalid_session_id(self):
        """Test handling of invalid session ID"""
        response = client.post(
            "/api/activity/start",
            json={
                "session_id": "invalid-uuid",
                "activity_type": "multiple_choice"
            }
        )
        assert response.status_code == 404
    
    def test_invalid_username(self):
        """Test handling of invalid username"""
        response = client.post(
            "/api/session/init",
            json={
                "username": "invalid user!",  # Contains invalid characters
                "module_id": "r003.1"
            }
        )
        assert response.status_code == 400
        assert "alphanumeric" in response.json()["detail"].lower()
    
    def test_invalid_module_id(self):
        """Test handling of non-existent module"""
        response = client.post(
            "/api/session/init",
            json={
                "username": "testuser",
                "module_id": "nonexistent"
            }
        )
        assert response.status_code == 404


class TestConcurrentUsers:
    """Test handling of concurrent users"""
    
    def test_multiple_concurrent_sessions(self):
        """Test that multiple users can have concurrent sessions"""
        users = ["concurrent_user_1", "concurrent_user_2", "concurrent_user_3"]
        sessions = []
        
        # Create sessions for all users
        for username in users:
            response = client.post(
                "/api/session/init",
                json={"username": username, "module_id": "r003.1"}
            )
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])
        
        # All should have unique session IDs
        assert len(set(sessions)) == len(sessions)
        
        # All should be able to start activities
        for session_id in sessions:
            response = client.post(
                "/api/activity/start",
                json={
                    "session_id": session_id,
                    "activity_type": "multiple_choice"
                }
            )
            assert response.status_code == 200


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
