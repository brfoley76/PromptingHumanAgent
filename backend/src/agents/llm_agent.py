"""
LLM-powered agent using LangChain and OpenAI/Anthropic.
Provides dynamic, contextual tutoring with Socratic dialogue.
Implements token management and conversation summarization.
"""
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ..config import config
from ..services.curriculum import CurriculumService
from ..services.token_counter import get_token_counter
from .simple_agent import AgentResponse
import logging

logger = logging.getLogger(__name__)


class LLMAgent:
    """
    LLM-powered agent that provides intelligent tutoring.
    Uses the same interface as SimpleAgent for easy swapping.
    Implements token management and conversation history optimization.
    """
    
    def __init__(self, student_name: str, module_id: str, activity_state: Optional[Dict] = None):
        """
        Initialize LLM agent with curriculum context.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
            activity_state: Optional dict with activity availability info
        """
        self.student_name = student_name
        self.module_id = module_id
        self.activity_state = activity_state or {}
        self.conversation_history = []
        self.conversation_summary = None  # For rolling summary
        self.message_count = 0  # Track messages for summary trigger
        
        # Load lightweight curriculum (without narrative)
        self.curriculum = CurriculumService.load_curriculum_light(module_id)
        self.vocabulary = self.curriculum.get('content', {}).get('vocabulary', [])
        self.problems = self.curriculum.get('content', {}).get('problems', [])
        
        # Initialize token counter
        self.token_counter = get_token_counter()
        
        # Initialize LLM based on provider
        llm_config = config.get_llm_config()
        if llm_config['provider'] == 'anthropic':
            self.llm = ChatAnthropic(
                model=llm_config['model_name'],
                temperature=llm_config['temperature'],
                max_tokens=llm_config['max_tokens'],
                anthropic_api_key=llm_config['api_key']
            )
        else:  # default to openai
            self.llm = ChatOpenAI(
                model=llm_config['model_name'],
                temperature=llm_config['temperature'],
                max_tokens=llm_config['max_tokens'],
                api_key=llm_config['api_key']
            )
        
        # Build system context
        self.system_context = self._build_system_context()
    
    def _build_system_context(self) -> str:
        """Build system context with curriculum information"""
        # Get module info
        module_title = self.curriculum.get('title', 'Learning Module')
        module_description = self.curriculum.get('description', '')
        grade_level = self.curriculum.get('gradeLevel', '3rd')
        
        # Build vocabulary list (limit to first 15 for token efficiency)
        vocab_sample = self.vocabulary[:15] if len(self.vocabulary) > 15 else self.vocabulary
        vocab_text = "\n".join([
            f"- {v['word']}: {v['definition']}" 
            for v in vocab_sample
        ])
        
        if len(self.vocabulary) > 15:
            vocab_text += f"\n... and {len(self.vocabulary) - 15} more words"
        
        # Build activity state info if available
        activity_info = ""
        if self.activity_state:
            available = self.activity_state.get('available', [])
            unlocked = self.activity_state.get('unlocked', [])
            
            activity_names = {
                'multiple_choice': 'Word Quiz',
                'fill_in_the_blank': 'Fill It In',
                'spelling': 'Spell It',
                'bubble_pop': 'Bubble Fun',
                'fluent_reading': 'Read It'
            }
            
            activity_list = []
            for activity in available:
                name = activity_names.get(activity, activity)
                status = "ready" if activity in unlocked else "locked"
                activity_list.append(f"- {name} ({status})")
            
            if activity_list:
                activity_info = f"\n\nAVAILABLE ACTIVITIES:\n" + "\n".join(activity_list)
                activity_info += "\n\nYou can tell students which button to click, like 'Click the Word Quiz button to start.'"
        
        return f"""You are a clear, helpful tutor for {self.student_name}, a {grade_level} grade student.

CURRENT MODULE: {module_title}
{module_description}

VOCABULARY:
{vocab_text}{activity_info}

YOUR COMMUNICATION STYLE:
- Use very simple words only
- Keep every response to 1 short sentence
- Be clear and direct, not playful
- Avoid idioms, metaphors, or complex phrases
- Some students struggle with reading, so keep it simple

IMPORTANT:
- Always respond in 1 short sentence only
- Use the simplest words possible
- Be helpful but not overly cheerful"""
    
    def _summarize_conversation(self) -> str:
        """
        Generate a summary of older conversation history.
        Uses LLM to extract key information.
        """
        if not self.conversation_history:
            return ""
        
        # Get messages to summarize (all but recent ones)
        recent_count = config.TUTOR_RECENT_MESSAGES
        messages_to_summarize = self.conversation_history[:-recent_count] if len(self.conversation_history) > recent_count else self.conversation_history
        
        if not messages_to_summarize:
            return ""
        
        # Build summary prompt
        conversation_text = "\n".join([
            f"{'Student' if isinstance(msg, HumanMessage) else 'Tutor'}: {msg.content}"
            for msg in messages_to_summarize
        ])
        
        summary_prompt = f"""Summarize this tutoring conversation in 3-4 sentences. Focus on:
1. What vocabulary words the student struggled with or asked about
2. Any persistent misconceptions or questions
3. Topics they showed interest in
4. Overall engagement level

Conversation:
{conversation_text}

Summary:"""
        
        try:
            # Use LLM to generate summary
            summary_msg = self.llm.invoke([HumanMessage(content=summary_prompt)])
            logger.info(f"Generated conversation summary: {len(summary_msg.content)} chars")
            return summary_msg.content
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "Previous conversation covered vocabulary practice and student questions."
    
    def _build_messages(self, new_prompt: str) -> List:
        """
        Build message list with system context, summary, and recent history.
        Implements rolling summary for token efficiency.
        """
        messages = [SystemMessage(content=self.system_context)]
        
        # Add conversation summary if it exists
        if self.conversation_summary:
            summary_msg = SystemMessage(content=f"PREVIOUS CONVERSATION SUMMARY:\n{self.conversation_summary}")
            messages.append(summary_msg)
        
        # Add recent conversation history
        recent_count = config.TUTOR_RECENT_MESSAGES
        recent_messages = self.conversation_history[-recent_count:] if len(self.conversation_history) > recent_count else self.conversation_history
        messages.extend(recent_messages)
        
        # Add new prompt
        messages.append(HumanMessage(content=new_prompt))
        
        return messages
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM with proper context and error handling.
        Implements token counting and management.
        
        Args:
            prompt: The user prompt
            
        Returns:
            LLM response text
        """
        try:
            # Build messages
            messages = self._build_messages(prompt)
            
            # Check token count
            token_check = self.token_counter.check_token_limit(messages)
            logger.info(f"Token usage: {token_check['token_count']} tokens ({token_check['status']})")
            
            if token_check['status'] == 'error':
                logger.error(token_check['message'])
                # Emergency truncation
                messages = self.token_counter.truncate_messages(messages, config.MAX_TOKENS_LIMIT)
                logger.warning(f"Emergency truncation applied. New token count: {self.token_counter.count_messages_tokens(messages)}")
            elif token_check['status'] == 'critical':
                logger.warning(token_check['message'])
            elif token_check['status'] == 'warning':
                logger.info(token_check['message'])
            
            # Call LLM
            response = self.llm.invoke(messages)
            
            # Store in history
            self.conversation_history.append(HumanMessage(content=prompt))
            self.conversation_history.append(AIMessage(content=response.content))
            self.message_count += 2
            
            # Check if we need to summarize
            if self.message_count >= config.TUTOR_SUMMARY_THRESHOLD:
                logger.info(f"Triggering conversation summary at {self.message_count} messages")
                self.conversation_summary = self._summarize_conversation()
                # Keep only recent messages
                recent_count = config.TUTOR_RECENT_MESSAGES
                self.conversation_history = self.conversation_history[-recent_count:]
                self.message_count = len(self.conversation_history)
                logger.info(f"Summary complete. Retained {self.message_count} recent messages")
            
            return response.content
            
        except Exception as e:
            # Fallback to simple message if LLM fails
            logger.error(f"LLM Error: {e}")
            return "Let me think about that..."
    
    def get_welcome_message(self) -> str:
        """Initial greeting when session starts"""
        module_title = self.curriculum.get('title', 'Learning Module')
        
        # Get a few sample words
        sample_words = []
        if len(self.vocabulary) >= 3:
            sample_words = [v['word'] for v in self.vocabulary[:3]]
        
        words_mention = f"words like {', '.join(sample_words)}" if sample_words else "new vocabulary"
        
        prompt = f"""Greet {self.student_name} and tell them they'll learn {words_mention} today.
Use 1 short sentence only."""
        
        return self._call_llm(prompt)
    
    def get_correct_response(self, problem: Dict, is_retry: bool = False) -> AgentResponse:
        """Response when student answers correctly"""
        if is_retry:
            prompt = f"""{self.student_name} got {problem['expression']} correct after trying again.
Say 'Good job' in 1 short sentence."""
        else:
            prompt = f"""{self.student_name} got {problem['expression']} = {problem['answer']} correct.
Say 'Good' or 'Correct' in 1 short sentence."""
        
        message = self._call_llm(prompt)
        return AgentResponse(message)
    
    def get_error_introduction(self, problem: Dict, student_answer: int) -> AgentResponse:
        """Initial response when student makes an error"""
        prompt = f"""{self.student_name} answered {problem['expression']} = {student_answer}, but the answer is {problem['answer']}.
Tell them to try again in 1 short sentence."""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="none")
    
    def ask_for_reasoning(self, problem: Dict, student_answer: int) -> AgentResponse:
        """Socratic question - ask student to explain their thinking"""
        prompt = f"""Ask {self.student_name} how they got {student_answer} for {problem['expression']}.
Use 1 short sentence."""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="none")
    
    def provide_hint(self, problem: Dict, student_answer: int, student_explanation: str) -> AgentResponse:
        """
        Provide contextual hint based on the problem and student's error.
        Uses curriculum hint but delivers it through LLM for natural language.
        """
        curriculum_hint = problem.get('hint', f"Think about {problem['a']} groups of {problem['b']}")
        
        prompt = f"""The problem is {problem['expression']}.
Give this hint: {curriculum_hint}
Use 1 short sentence."""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="medium")
    
    def provide_full_explanation(self, problem: Dict) -> AgentResponse:
        """
        Provide complete explanation when student still can't get it.
        """
        explanation = problem.get('explanation', f"{problem['a']} × {problem['b']} = {problem['answer']}")
        
        prompt = f"""Explain: {explanation}
Use 1 short sentence with simple words."""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="explicit")
    
    def get_final_feedback(self, score: int, total: int) -> AgentResponse:
        """Final feedback based on overall performance"""
        percentage = (score / total) * 100
        
        prompt = f"""{self.student_name} got {score} out of {total} ({percentage:.0f}%).
Tell them they did well in 1 short sentence."""
        
        message = self._call_llm(prompt)
        return AgentResponse(message)
    
    def record_message(self, sender: str, message: str):
        """Record message in conversation history"""
        # Already handled in _call_llm
        pass


class TutorAgent(LLMAgent):
    """
    LLM tutor agent for general session guidance.
    Implements rolling summary for long conversations.
    """
    pass


class ActivityAgent(LLMAgent):
    """
    LLM activity-specific agent for vocabulary practice.
    Uses simple truncation since activities are short-lived.
    """
    
    def __init__(self, student_name: str, module_id: str, activity_type: str = None, difficulty: str = None):
        """
        Initialize activity agent with filtered vocabulary.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
            activity_type: Type of activity (optional)
            difficulty: Difficulty level (optional)
        """
        super().__init__(student_name, module_id)
        
        # Override with activity-specific vocabulary if provided
        if activity_type and difficulty:
            self.vocabulary = CurriculumService.get_activity_vocabulary(
                module_id, activity_type, difficulty
            )
            # Rebuild system context with filtered vocabulary
            self.system_context = self._build_system_context()
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with simple truncation for activity agents.
        Activities are short-lived, so no summary needed.
        """
        try:
            # Build messages with simple truncation
            messages = [SystemMessage(content=self.system_context)]
            
            # Keep only last N messages
            message_limit = config.ACTIVITY_MESSAGE_LIMIT
            recent_messages = self.conversation_history[-message_limit:] if len(self.conversation_history) > message_limit else self.conversation_history
            messages.extend(recent_messages)
            messages.append(HumanMessage(content=prompt))
            
            # Check token count
            token_check = self.token_counter.check_token_limit(messages)
            logger.info(f"Activity agent token usage: {token_check['token_count']} tokens")
            
            if token_check['status'] in ['critical', 'error']:
                logger.warning(f"Activity agent: {token_check['message']}")
                messages = self.token_counter.truncate_messages(messages, config.MAX_TOKENS_LIMIT)
            
            # Call LLM
            response = self.llm.invoke(messages)
            
            # Store in history (will be auto-truncated next call)
            self.conversation_history.append(HumanMessage(content=prompt))
            self.conversation_history.append(AIMessage(content=response.content))
            
            return response.content
            
        except Exception as e:
            logger.error(f"Activity Agent LLM Error: {e}")
            return "Keep trying! You can do this!"
    
    def get_activity_intro(self, activity_type: str, difficulty: str) -> str:
        """Get introduction message for starting an activity"""
        activity_names = {
            'multiple_choice': 'Multiple Choice',
            'fill_in_the_blank': 'Fill in the Blank',
            'spelling': 'Spelling',
            'bubble_pop': 'Bubble Pop',
            'fluent_reading': 'Fluent Reading'
        }
        
        activity_name = activity_names.get(activity_type, activity_type)
        
        prompt = f"""Tell {self.student_name} they will do {activity_name} at level {difficulty}.
Use 1 short sentence."""
        
        return self._call_llm(prompt)
    
    def get_activity_feedback(self, activity_type: str, score: int, total: int, percentage: float) -> str:
        """Get feedback message after completing an activity"""
        prompt = f"""{self.student_name} got {score} out of {total} ({percentage:.0f}%).
Tell them they did good in 1 short sentence."""
        
        return self._call_llm(prompt)
