"""
Unit tests for LLM agents (Tutor and Activity agents)
Run with: pytest tests/test_agents.py -v
"""
import pytest
from src.agents.agent_manager import AgentManager


class TestTutorAgent:
    """Test suite for the Tutor Agent"""
    
    @pytest.fixture
    def agent_manager(self):
        """Create an AgentManager instance for testing"""
        return AgentManager(student_name="TestStudent", module_id="r003.1")
    
    def test_tutor_greeting(self, agent_manager):
        """Test that tutor responds to greetings"""
        response = agent_manager.handle_chat_message(
            "Hello!",
            context={'in_activity': False}
        )
        
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)
        print(f"\n[TUTOR GREETING] {response}")
    
    def test_tutor_vocabulary_help(self, agent_manager):
        """Test that tutor can explain vocabulary"""
        response = agent_manager.handle_chat_message(
            "Can you help me understand what 'benevolent' means?",
            context={'in_activity': False}
        )
        
        assert response is not None
        assert len(response) > 0
        # Should mention the word or provide explanation
        assert any(word in response.lower() for word in ['benevolent', 'kind', 'good', 'help'])
        print(f"\n[TUTOR VOCABULARY] {response}")
    
    def test_tutor_encouragement(self, agent_manager):
        """Test that tutor provides encouragement"""
        response = agent_manager.handle_chat_message(
            "I'm finding this difficult",
            context={'in_activity': False}
        )
        
        assert response is not None
        assert len(response) > 0
        # Should be encouraging
        print(f"\n[TUTOR ENCOURAGEMENT] {response}")


class TestActivityAgent:
    """Test suite for the Activity Agent"""
    
    @pytest.fixture
    def agent_manager(self):
        """Create an AgentManager instance for testing"""
        return AgentManager(student_name="TestStudent", module_id="r003.1")
    
    def test_activity_start(self, agent_manager):
        """Test activity agent welcome message"""
        welcome = agent_manager.start_activity("multiple_choice", "4")
        
        assert welcome is not None
        assert len(welcome) > 0
        assert isinstance(welcome, str)
        print(f"\n[ACTIVITY START] {welcome}")
    
    def test_wrong_answer_first_attempt(self, agent_manager):
        """Test activity agent response to first wrong answer"""
        # Start activity first
        agent_manager.start_activity("multiple_choice", "4")
        
        question_data = {
            'definition': 'Showing kindness and goodwill',
            'correct_answer': 'benevolent',
            'user_answer': 'malevolent',
            'choices': ['benevolent', 'malevolent', 'indifferent', 'hostile']
        }
        
        response = agent_manager.handle_wrong_answer(question_data, attempt_number=1)
        
        assert response is not None
        assert len(response) > 0
        # Should provide a hint
        print(f"\n[WRONG ANSWER - ATTEMPT 1] {response}")
    
    def test_wrong_answer_second_attempt(self, agent_manager):
        """Test activity agent response to second wrong answer"""
        # Start activity first
        agent_manager.start_activity("multiple_choice", "4")
        
        question_data = {
            'definition': 'Showing kindness and goodwill',
            'correct_answer': 'benevolent',
            'user_answer': 'malevolent',
            'choices': ['benevolent', 'malevolent', 'indifferent', 'hostile']
        }
        
        response = agent_manager.handle_wrong_answer(question_data, attempt_number=2)
        
        assert response is not None
        assert len(response) > 0
        # Should provide more direct hint
        print(f"\n[WRONG ANSWER - ATTEMPT 2] {response}")
    
    def test_correct_answer(self, agent_manager):
        """Test activity agent response to correct answer"""
        # Start activity first
        agent_manager.start_activity("multiple_choice", "4")
        
        correct_data = {
            'correct_answer': 'benevolent'
        }
        
        response = agent_manager.handle_correct_answer(correct_data, is_retry=True)
        
        assert response is not None
        assert len(response) > 0
        # Should be congratulatory
        print(f"\n[CORRECT ANSWER] {response}")
    
    def test_activity_chat(self, agent_manager):
        """Test activity agent chat during activity"""
        # Start activity first
        agent_manager.start_activity("multiple_choice", "4")
        
        response = agent_manager.handle_chat_message(
            "What does benevolent mean again?",
            context={'in_activity': True}
        )
        
        assert response is not None
        assert len(response) > 0
        # Should route to activity agent
        print(f"\n[ACTIVITY CHAT] {response}")
    
    def test_activity_end(self, agent_manager):
        """Test activity agent feedback at end"""
        # Start activity first
        agent_manager.start_activity("multiple_choice", "4")
        
        feedback = agent_manager.end_activity(score=8, total=10)
        
        assert feedback is not None
        assert len(feedback) > 0
        # Should provide feedback on performance
        print(f"\n[ACTIVITY END] {feedback}")


class TestAgentManager:
    """Test suite for AgentManager coordination"""
    
    def test_agent_manager_creation(self):
        """Test that AgentManager can be created"""
        manager = AgentManager(student_name="TestStudent", module_id="r003.1")
        
        assert manager is not None
        assert manager.student_name == "TestStudent"
        assert manager.module_id == "r003.1"
    
    def test_activity_lifecycle(self):
        """Test complete activity lifecycle"""
        manager = AgentManager(student_name="TestStudent", module_id="r003.1")
        
        # Start activity
        welcome = manager.start_activity("multiple_choice", "4")
        assert welcome is not None
        assert manager.is_in_activity()
        
        # End activity
        feedback = manager.end_activity(score=7, total=10)
        assert feedback is not None
        assert not manager.is_in_activity()
    
    def test_message_routing(self):
        """Test that messages route to correct agent"""
        manager = AgentManager(student_name="TestStudent", module_id="r003.1")
        
        # Before activity - should route to tutor
        response1 = manager.handle_chat_message(
            "Hello",
            context={'in_activity': False}
        )
        assert response1 is not None
        
        # Start activity
        manager.start_activity("multiple_choice", "4")
        
        # During activity - should route to activity agent
        response2 = manager.handle_chat_message(
            "Help me",
            context={'in_activity': True}
        )
        assert response2 is not None
        
        # End activity
        manager.end_activity(score=5, total=10)
        
        # After activity - should route back to tutor
        response3 = manager.handle_chat_message(
            "Thanks",
            context={'in_activity': False}
        )
        assert response3 is not None


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
