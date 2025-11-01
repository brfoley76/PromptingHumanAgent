"""
Tests for token management and conversation summarization.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.services.token_counter import TokenCounter, get_token_counter
from src.services.curriculum import CurriculumService
from src.agents.llm_agent import TutorAgent, ActivityAgent
from src.config import config


class TestTokenCounter:
    """Test token counting functionality"""
    
    def test_count_tokens_basic(self):
        """Test basic token counting"""
        counter = TokenCounter()
        
        # Simple text
        text = "Hello world"
        tokens = counter.count_tokens(text)
        assert tokens > 0
        assert tokens < 10  # Should be around 2-3 tokens
    
    def test_count_tokens_empty(self):
        """Test counting empty string"""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0
        assert counter.count_tokens(None) == 0
    
    def test_count_message_tokens(self):
        """Test counting tokens in messages"""
        counter = TokenCounter()
        
        msg = HumanMessage(content="Hello, how are you?")
        tokens = counter.count_message_tokens(msg)
        
        # Should include content + overhead
        assert tokens > 4  # At least content tokens + overhead
    
    def test_count_messages_tokens(self):
        """Test counting tokens in message list"""
        counter = TokenCounter()
        
        messages = [
            SystemMessage(content="You are a helpful tutor."),
            HumanMessage(content="What is 2+2?"),
            AIMessage(content="2+2 equals 4!")
        ]
        
        total_tokens = counter.count_messages_tokens(messages)
        assert total_tokens > 10  # Should have reasonable token count
    
    def test_check_token_limit_ok(self):
        """Test token limit check with normal usage"""
        counter = TokenCounter()
        
        messages = [
            SystemMessage(content="You are a tutor."),
            HumanMessage(content="Hello")
        ]
        
        result = counter.check_token_limit(messages)
        assert result['status'] == 'ok'
        assert result['token_count'] > 0
        assert result['message'] is None
    
    def test_check_token_limit_warning(self):
        """Test token limit check with warning threshold"""
        counter = TokenCounter()
        counter.MAX_TOKENS_WARNING = 10  # Set low threshold for testing
        
        # Create message with lots of content
        long_content = "word " * 1000
        messages = [SystemMessage(content=long_content)]
        
        result = counter.check_token_limit(messages)
        assert result['status'] in ['warning', 'critical', 'error']
        assert result['token_count'] > 10
    
    def test_truncate_messages(self):
        """Test message truncation"""
        counter = TokenCounter()
        
        messages = [
            SystemMessage(content="System message"),
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
            AIMessage(content="Response 2"),
            HumanMessage(content="Message 3"),
            AIMessage(content="Response 3"),
        ]
        
        # Truncate to very small size
        truncated = counter.truncate_messages(messages, max_tokens=50)
        
        # Should keep system message
        assert isinstance(truncated[0], SystemMessage)
        # Should have fewer messages
        assert len(truncated) < len(messages)
    
    def test_get_token_counter_singleton(self):
        """Test that get_token_counter returns singleton"""
        counter1 = get_token_counter()
        counter2 = get_token_counter()
        assert counter1 is counter2


class TestCurriculumLightLoading:
    """Test lightweight curriculum loading"""
    
    def test_load_curriculum_light(self):
        """Test loading curriculum without narrative"""
        # Load full curriculum
        full = CurriculumService.load_curriculum('r003.1')
        
        # Load light curriculum
        light = CurriculumService.load_curriculum_light('r003.1')
        
        # Light should have vocabulary
        assert 'content' in light
        assert 'vocabulary' in light['content']
        assert len(light['content']['vocabulary']) > 0
        
        # Light should NOT have narrative
        assert 'narrative' not in light.get('content', {})
        
        # Full should have narrative
        assert 'narrative' in full.get('content', {})
    
    def test_get_activity_vocabulary(self):
        """Test filtering vocabulary by difficulty"""
        # Get vocabulary for easy difficulty
        easy_vocab = CurriculumService.get_activity_vocabulary('r003.1', 'multiple_choice', '3')
        
        # Get vocabulary for hard difficulty
        hard_vocab = CurriculumService.get_activity_vocabulary('r003.1', 'multiple_choice', '5')
        
        # Easy should have fewer or equal words
        assert len(easy_vocab) <= len(hard_vocab)
        
        # All should be valid vocabulary items
        for vocab in easy_vocab:
            assert 'word' in vocab
            assert 'definition' in vocab


class TestAgentTokenManagement:
    """Test agent token management"""
    
    @patch('src.agents.llm_agent.ChatAnthropic')
    def test_tutor_agent_uses_light_curriculum(self, mock_llm):
        """Test that TutorAgent loads lightweight curriculum"""
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        agent = TutorAgent("TestStudent", "r003.1")
        
        # Should have vocabulary
        assert len(agent.vocabulary) > 0
        
        # System context should not be excessively long
        # (narrative would make it very long)
        assert len(agent.system_context) < 5000  # Reasonable limit
    
    @patch('src.agents.llm_agent.ChatAnthropic')
    def test_activity_agent_filters_vocabulary(self, mock_llm):
        """Test that ActivityAgent filters vocabulary by difficulty"""
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Create agent with easy difficulty
        agent = ActivityAgent("TestStudent", "r003.1", "multiple_choice", "3")
        
        # Should have filtered vocabulary
        assert len(agent.vocabulary) > 0
        
        # Vocabulary should be filtered (not all 24 words)
        full_vocab = CurriculumService.get_vocabulary("r003.1")
        assert len(agent.vocabulary) <= len(full_vocab)
    
    @patch('src.agents.llm_agent.ChatAnthropic')
    def test_tutor_agent_conversation_summary(self, mock_llm):
        """Test that TutorAgent creates conversation summaries"""
        # Mock LLM responses
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "This is a summary of the conversation."
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance
        
        agent = TutorAgent("TestStudent", "r003.1")
        
        # Simulate many messages to trigger summary
        original_threshold = config.TUTOR_SUMMARY_THRESHOLD
        config.TUTOR_SUMMARY_THRESHOLD = 4  # Lower threshold for testing
        
        try:
            # Add messages
            for i in range(3):
                agent._call_llm(f"Test message {i}")
            
            # Should have triggered summary
            assert agent.conversation_summary is not None
            assert len(agent.conversation_history) <= config.TUTOR_RECENT_MESSAGES
        finally:
            config.TUTOR_SUMMARY_THRESHOLD = original_threshold
    
    @patch('src.agents.llm_agent.ChatAnthropic')
    def test_activity_agent_simple_truncation(self, mock_llm):
        """Test that ActivityAgent uses simple truncation"""
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "Response"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance
        
        agent = ActivityAgent("TestStudent", "r003.1", "multiple_choice", "3")
        
        # Add many messages
        for i in range(15):
            agent._call_llm(f"Message {i}")
        
        # Should have truncated to limit
        assert len(agent.conversation_history) <= config.ACTIVITY_MESSAGE_LIMIT
        
        # Should NOT have summary (ActivityAgent doesn't use it)
        assert agent.conversation_summary is None
    
    @patch('src.agents.llm_agent.ChatAnthropic')
    def test_token_limit_logging(self, mock_llm, caplog):
        """Test that token limits are logged"""
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "Response"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance
        
        agent = TutorAgent("TestStudent", "r003.1")
        
        # Make a call
        agent._call_llm("Test message")
        
        # Should have logged token usage
        # (Check that logging occurred - exact message may vary)
        assert len(caplog.records) > 0


class TestIntegration:
    """Integration tests for token management"""
    
    @patch('src.agents.llm_agent.ChatAnthropic')
    def test_long_conversation_doesnt_exceed_limit(self, mock_llm):
        """Test that long conversations stay within token limits"""
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "I understand. Let's continue learning!"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance
        
        agent = TutorAgent("TestStudent", "r003.1")
        counter = get_token_counter()
        
        # Simulate long conversation
        for i in range(30):
            agent._call_llm(f"This is test message number {i}. Can you help me understand vocabulary?")
        
        # Build final message list
        messages = agent._build_messages("Final message")
        
        # Check token count
        token_check = counter.check_token_limit(messages)
        
        # Should not exceed hard limit
        assert token_check['token_count'] < config.MAX_TOKENS_HARD_LIMIT
        
        # Should have created summary
        assert agent.conversation_summary is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
