"""
Integration tests for student data capture and persistence
Tests that data flows correctly from frontend through API to database
Run with: pytest tests/test_data_persistence.py -v
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.database.database import init_db
from src.database.operations import DatabaseOperations

client = TestClient(app)


class TestDataPersistence:
    """Test complete data persistence flow"""
    
    def test_activity_attempt_with_item_results(self):
        """Test that activity attempts are saved with complete item_results"""
        username = "data_persistence_test_user"
        
        # Step 1: Create session
        init_response = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        assert init_response.status_code == 200
        session_data = init_response.json()
        session_id = session_data["session_id"]
        student_id = session_data["student_id"]
        
        # Step 2: Start activity
        start_response = client.post(
            "/api/activity/start",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice"
            }
        )
        assert start_response.status_code == 200
        
        # Step 3: Complete activity with detailed item_results
        item_results = [
            {
                "questionNumber": 1,
                "definition": "to make something better",
                "userAnswer": "improve",
                "correctAnswer": "improve",
                "isCorrect": True,
                "timestamp": 1234567890
            },
            {
                "questionNumber": 2,
                "definition": "to make something worse",
                "userAnswer": "worsen",
                "correctAnswer": "deteriorate",
                "isCorrect": False,
                "timestamp": 1234567891
            },
            {
                "questionNumber": 3,
                "definition": "very large",
                "userAnswer": "enormous",
                "correctAnswer": "enormous",
                "isCorrect": True,
                "timestamp": 1234567892
            }
        ]
        
        end_response = client.post(
            "/api/activity/end",
            json={
                "session_id": session_id,
                "activity_type": "multiple_choice",
                "results": {
                    "score": 2,
                    "total": 3,
                    "item_results": item_results
                },
                "tuning_settings": {
                    "difficulty": "4",
                    "num_questions": 3
                }
            }
        )
        assert end_response.status_code == 200
        
        # Step 4: Verify data persisted in database
        # Check activity_attempts table
        attempts = DatabaseOperations.get_student_performance_history(
            student_id,
            "multiple_choice",
            limit=1
        )
        
        assert len(attempts) == 1
        attempt = attempts[0]
        
        # Verify basic data
        assert attempt.score == 2
        assert attempt.total == 3
        assert attempt.difficulty == "4"
        
        # Verify item_results are NOT empty
        assert attempt.item_results is not None
        assert len(attempt.item_results) == 3
        
        # Verify item_results structure
        assert attempt.item_results[0]["questionNumber"] == 1
        assert attempt.item_results[0]["isCorrect"] is True
        assert attempt.item_results[1]["isCorrect"] is False
        assert attempt.item_results[2]["isCorrect"] is True
    
    def test_proficiency_updates_after_activity(self):
        """Test that student proficiencies are updated after completing activities"""
        username = "proficiency_test_user"
        
        # Create session
        init_response = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session_id = init_response.json()["session_id"]
        student_id = init_response.json()["student_id"]
        
        # Complete activity with good performance
        client.post("/api/activity/start", json={
            "session_id": session_id,
            "activity_type": "multiple_choice"
        })
        
        item_results = [
            {"questionNumber": i, "isCorrect": i < 8}
            for i in range(10)
        ]
        
        client.post("/api/activity/end", json={
            "session_id": session_id,
            "activity_type": "multiple_choice",
            "results": {
                "score": 8,
                "total": 10,
                "item_results": item_results
            },
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        # Verify proficiencies were created/updated
        proficiencies = DatabaseOperations.get_student_proficiencies(
            student_id,
            level="module",
            module_id="r003.1"
        )
        
        # Should have at least one proficiency record
        assert len(proficiencies) > 0
        
        # Check that proficiency has been updated (not all zeros)
        module_prof = proficiencies[0]
        assert module_prof.sample_count > 0
        assert module_prof.mean_ability > 0  # Should be positive with 80% score
    
    def test_returning_user_sees_complete_history(self):
        """Test that returning users see their complete activity history"""
        username = "returning_history_user"
        
        # Session 1: Complete multiple activities
        init1 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session1_id = init1.json()["session_id"]
        student_id = init1.json()["student_id"]
        
        # Complete 3 activities with different scores
        for i, score in enumerate([7, 8, 9]):
            client.post("/api/activity/start", json={
                "session_id": session1_id,
                "activity_type": "multiple_choice"
            })
            
            item_results = [
                {"questionNumber": j, "isCorrect": j < score}
                for j in range(10)
            ]
            
            client.post("/api/activity/end", json={
                "session_id": session1_id,
                "activity_type": "multiple_choice",
                "results": {
                    "score": score,
                    "total": 10,
                    "item_results": item_results
                },
                "tuning_settings": {"difficulty": "4", "num_questions": 10}
            })
        
        # End session
        client.post("/api/session/end", json={"session_id": session1_id})
        
        # Session 2: Login again
        init2 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session2_data = init2.json()
        
        # Verify returning user status
        assert session2_data["is_returning_student"] is True
        assert session2_data["student_id"] == student_id
        
        # Verify progress shows all 3 attempts
        assert session2_data["progress"]["total_attempts"] == 3
        
        # Verify history in database
        history = DatabaseOperations.get_student_performance_history(
            student_id,
            "multiple_choice",
            limit=10
        )
        
        assert len(history) == 3
        # Verify scores are in order (most recent first)
        assert history[0].score == 9
        assert history[1].score == 8
        assert history[2].score == 7
        
        # Verify all have item_results
        for attempt in history:
            assert len(attempt.item_results) == 10
    
    def test_empty_item_results_handled_gracefully(self):
        """Test that system handles empty item_results without crashing"""
        username = "empty_results_user"
        
        init_response = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session_id = init_response.json()["session_id"]
        
        client.post("/api/activity/start", json={
            "session_id": session_id,
            "activity_type": "multiple_choice"
        })
        
        # Send empty item_results
        end_response = client.post("/api/activity/end", json={
            "session_id": session_id,
            "activity_type": "multiple_choice",
            "results": {
                "score": 5,
                "total": 10,
                "item_results": []  # Empty!
            },
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        # Should still succeed
        assert end_response.status_code == 200
        
        # But proficiency updates may be limited
        # (This is expected behavior - can't update without item data)
    
    def test_cross_session_data_consistency(self):
        """Test that data remains consistent across multiple sessions"""
        username = "consistency_test_user"
        
        # Session 1
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
        
        item_results_1 = [
            {"questionNumber": i, "isCorrect": i < 8}
            for i in range(10)
        ]
        
        client.post("/api/activity/end", json={
            "session_id": session1_id,
            "activity_type": "multiple_choice",
            "results": {
                "score": 8,
                "total": 10,
                "item_results": item_results_1
            },
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        client.post("/api/session/end", json={"session_id": session1_id})
        
        # Session 2
        init2 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        session2_id = init2.json()["session_id"]
        
        # Complete another activity
        client.post("/api/activity/start", json={
            "session_id": session2_id,
            "activity_type": "multiple_choice"
        })
        
        item_results_2 = [
            {"questionNumber": i, "isCorrect": i < 9}
            for i in range(10)
        ]
        
        client.post("/api/activity/end", json={
            "session_id": session2_id,
            "activity_type": "multiple_choice",
            "results": {
                "score": 9,
                "total": 10,
                "item_results": item_results_2
            },
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        # Verify both attempts are in database
        history = DatabaseOperations.get_student_performance_history(
            student_id,
            "multiple_choice",
            limit=10
        )
        
        assert len(history) == 2
        assert history[0].score == 9  # Most recent
        assert history[1].score == 8  # Older
        
        # Verify both have complete item_results
        assert len(history[0].item_results) == 10
        assert len(history[1].item_results) == 10
        
        # Verify student_id is consistent
        assert history[0].student_id == student_id
        assert history[1].student_id == student_id


class TestDataIntegrity:
    """Test data integrity and validation"""
    
    def test_student_id_consistency(self):
        """Test that student_id remains consistent across sessions"""
        username = "id_consistency_user"
        
        # Create first session
        init1 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        student_id_1 = init1.json()["student_id"]
        session1_id = init1.json()["session_id"]
        
        # End session
        client.post("/api/session/end", json={"session_id": session1_id})
        
        # Create second session with same username
        init2 = client.post(
            "/api/session/init",
            json={"username": username, "module_id": "r003.1"}
        )
        student_id_2 = init2.json()["student_id"]
        
        # Should be the same student_id
        assert student_id_1 == student_id_2
    
    def test_session_isolation(self):
        """Test that different users have isolated sessions"""
        user1 = "isolated_user_1"
        user2 = "isolated_user_2"
        
        # Create sessions for both users
        init1 = client.post(
            "/api/session/init",
            json={"username": user1, "module_id": "r003.1"}
        )
        init2 = client.post(
            "/api/session/init",
            json={"username": user2, "module_id": "r003.1"}
        )
        
        student_id_1 = init1.json()["student_id"]
        student_id_2 = init2.json()["student_id"]
        session_id_1 = init1.json()["session_id"]
        session_id_2 = init2.json()["session_id"]
        
        # Should have different IDs
        assert student_id_1 != student_id_2
        assert session_id_1 != session_id_2
        
        # Complete activity for user 1
        client.post("/api/activity/start", json={
            "session_id": session_id_1,
            "activity_type": "multiple_choice"
        })
        
        client.post("/api/activity/end", json={
            "session_id": session_id_1,
            "activity_type": "multiple_choice",
            "results": {
                "score": 8,
                "total": 10,
                "item_results": [{"questionNumber": i, "isCorrect": True} for i in range(10)]
            },
            "tuning_settings": {"difficulty": "4", "num_questions": 10}
        })
        
        # User 2 should have no attempts
        history_2 = DatabaseOperations.get_student_performance_history(
            student_id_2,
            "multiple_choice",
            limit=10
        )
        assert len(history_2) == 0
        
        # User 1 should have 1 attempt
        history_1 = DatabaseOperations.get_student_performance_history(
            student_id_1,
            "multiple_choice",
            limit=10
        )
        assert len(history_1) == 1


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "data_persistence: marks tests for data persistence"
    )
