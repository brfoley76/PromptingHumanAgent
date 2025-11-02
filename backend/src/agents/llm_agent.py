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
from .activity_instructions import format_instructions_for_llm, get_activity_intro_text, normalize_difficulty
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
        
        return f"""You are a warm, supportive tutor for {self.student_name}, a {grade_level} grade student.

CURRENT MODULE: {module_title}
{module_description}

VOCABULARY:
{vocab_text}{activity_info}

YOUR COMMUNICATION STYLE:
- Be warm, encouraging, and genuinely supportive
- Use very simple words that {self.student_name} can understand
- Keep responses to maximum 3 short sentences
- Each message should have ONE clear objective (welcoming, correction, encouragement, instruction)
- Show genuine interest in their learning journey
- Celebrate their progress and efforts
- Be patient and understanding with mistakes
- Avoid idioms, metaphors, or complex phrases

IMPORTANT:
- Maximum 3 sentences per response
- One clear objective per message
- Use the simplest words possible
- Be encouraging and build confidence"""
    
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
        """
        Initial greeting when session starts.
        Context-aware: different messages for new vs returning students.
        """
        module_title = self.curriculum.get('title', 'Learning Module')
        avatar_theme = self.curriculum.get('avatar_theme', 'pirates')
        
        # Check if this is a returning student with context
        if self.student_context:
            # Returning student - acknowledge progress and suggest next step
            progress_summary = self.student_context.get('progress_summary', {})
            completed = [act.replace('_', ' ').title() for act, data in progress_summary.items() if data.get('completed')]
            
            if completed:
                # Has completed activities
                completed_str = completed[0] if len(completed) == 1 else f"{completed[0]} and others"
                prompt = f"""Welcome back {self.student_name}! You finished {completed_str}.
Now let's work on matching words to their meanings.
Maximum 3 sentences. Be warm and encouraging."""
            else:
                # Returning but hasn't completed anything yet
                prompt = f"""Welcome back {self.student_name}!
Let's continue learning words about {avatar_theme}.
Maximum 3 sentences. Be warm and encouraging."""
        else:
            # New student - introduce the module theme
            prompt = f"""Hi {self.student_name}! This is our first lesson together.
We're going to learn words about {avatar_theme}!
Maximum 3 sentences. Be warm and welcoming."""
        
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
    
    def __init__(self, student_name: str, module_id: str, 
                 activity_state: Optional[Dict] = None,
                 student_context: Optional[Dict] = None):
        """
        Initialize tutor agent with optional student context.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
            activity_state: Optional dict with activity availability info
            student_context: Optional dict with student history, proficiency, and pedagogical info
        """
        print(f"\n[TUTOR AGENT] Initializing for {student_name}")
        print(f"[TUTOR AGENT] Student context provided: {student_context is not None}")
        if student_context:
            print(f"[TUTOR AGENT] Context sections: {list(student_context.keys())}")
        
        # Store student context for use in system prompt
        self.student_context = student_context
        
        # Call parent init
        super().__init__(student_name, module_id, activity_state)
        
        # Rebuild system context with student context if provided
        if student_context:
            print(f"[TUTOR AGENT] Rebuilding system context with student info...")
            self.system_context = self._build_system_context_with_student_info()
            print(f"[TUTOR AGENT] System context length: {len(self.system_context)} chars")
            print(f"[TUTOR AGENT] System context preview:\n{self.system_context[:500]}...")
        else:
            print(f"[TUTOR AGENT] No student context - using base system context")
    
    def _build_system_context_with_student_info(self) -> str:
        """Build enhanced system context with student history and pedagogical guidance"""
        # Start with base context
        base_context = super()._build_system_context()
        
        if not self.student_context:
            return base_context
        
        # Build student background section
        student_background = ["\n" + "="*50]
        student_background.append(f"STUDENT BACKGROUND - {self.student_name.upper()}")
        student_background.append("="*50)
        student_background.append(f"\nYou are tutoring {self.student_name}, a returning student.")
        student_background.append("You have access to their complete learning history and proficiency data.")
        
        # Add completed activities
        progress_summary = self.student_context.get('progress_summary', {})
        if progress_summary:
            completed = [act.replace('_', ' ').title() for act, data in progress_summary.items() if data.get('completed')]
            if completed:
                student_background.append(f"\n✓ COMPLETED: {', '.join(completed)}")
                student_background.append(f"  (You know {self.student_name} has finished these activities)")
        
        # Add proficiency information
        proficiency_summary = self.student_context.get('proficiency_summary', {})
        if proficiency_summary and proficiency_summary.get('available', True):
            avg_ability = proficiency_summary.get('average_ability', 0)
            mastered_count = proficiency_summary.get('mastered_count', 0)
            needs_work_count = proficiency_summary.get('needs_work_count', 0)
            
            student_background.append(f"\n📊 PROFICIENCY DATA:")
            student_background.append(f"  - Overall ability: {int(avg_ability * 100)}%")
            student_background.append(f"  - Words mastered: {mastered_count}")
            student_background.append(f"  - Words needing practice: {needs_work_count}")
        
        # Add problem words
        problem_words = self.student_context.get('problem_words', [])
        if problem_words:
            student_background.append(f"\n⚠️  WORDS {self.student_name.upper()} STRUGGLES WITH:")
            student_background.append(f"  {', '.join(problem_words[:5])}")
            student_background.append(f"  (Focus on these in your teaching)")
        
        # Add recent activity
        recent_activity = self.student_context.get('recent_activity', {})
        if recent_activity:
            student_background.append(f"\n📝 RECENT ATTEMPTS:")
            for activity, attempts in list(recent_activity.items())[:2]:
                if attempts:
                    latest = attempts[0]
                    student_background.append(f"  - {activity.replace('_', ' ').title()}: {latest['percentage']:.0f}% (difficulty {latest['difficulty']})")
        
        student_background.append("="*50)
        
        # Add pedagogical guidance
        additional_context = []
        
        # Module goals and teaching strategies
        module_info = self.student_context.get('module_info', {})
        if module_info and module_info.get('available', True):
            goals = module_info.get('goals', '')
            strategies = module_info.get('teaching_strategies', [])
            word_pairs = module_info.get('word_pairs', [])
            
            if goals:
                additional_context.append(f"\nMODULE GOALS: {goals}")
            
            if strategies:
                additional_context.append(f"\nTEACHING STRATEGIES: {', '.join(strategies)}")
            
            if word_pairs:
                additional_context.append(f"\nWORD PAIRS TO PRACTICE: {', '.join(word_pairs)}")
        
        # Learning progress and question guidelines
        learning_progress = self.student_context.get('learning_progress', {})
        
        if learning_progress:
            stage = learning_progress.get('current_stage', 'early')
            spelling_intro = learning_progress.get('spelling_introduced', False)
            
            if stage == 'early' and not spelling_intro:
                additional_context.append("\nQUESTION FORMAT: Use A/B multiple choice - student hasn't practiced spelling yet")
                additional_context.append("Example: 'Does cat rhyme with: A) rat, or B) basket?'")
            else:
                additional_context.append("\nQUESTION FORMAT: Can ask for typed single words - student has practiced spelling")
                additional_context.append("Example: 'What word rhymes with cat?'")
        
        # Combine all sections
        enhanced_context = base_context
        enhanced_context += "\n".join(student_background)
        if additional_context:
            enhanced_context += "\n" + "\n".join(additional_context)
        
        return enhanced_context


class ActivityAgent(LLMAgent):
    """
    LLM activity-specific agent for vocabulary practice.
    Uses simple truncation since activities are short-lived.
    Includes activity-specific instructions in system context.
    """
    
    def __init__(self, student_name: str, module_id: str, activity_type: str = None, difficulty: str = None):
        """
        Initialize activity agent with filtered vocabulary and activity instructions.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
            activity_type: Type of activity (optional)
            difficulty: Difficulty level (optional - can be '3'/'4'/'5' or 'easy'/'medium'/'hard')
        """
        # Store activity info before calling parent init
        self.activity_type = activity_type
        # Normalize difficulty from numeric to word format
        self.difficulty = normalize_difficulty(difficulty) if difficulty else None
        self.original_difficulty = difficulty  # Keep original for logging
        
        super().__init__(student_name, module_id)
        
        # Override with activity-specific vocabulary if provided
        if activity_type and difficulty:
            self.vocabulary = CurriculumService.get_activity_vocabulary(
                module_id, activity_type, difficulty
            )
            # Rebuild system context with filtered vocabulary AND activity instructions
            self.system_context = self._build_activity_system_context()
            
            logger.info(f"ActivityAgent initialized: {activity_type} at difficulty {self.original_difficulty} (normalized to {self.difficulty})")
    
    def _build_activity_system_context(self) -> str:
        """Build system context with activity-specific instructions"""
        # Start with base context
        base_context = super()._build_system_context()
        
        # Add activity instructions if available
        if self.activity_type and self.difficulty:
            instructions_context = format_instructions_for_llm(
                self.activity_type, 
                self.difficulty, 
                self.student_name
            )
            
            # Combine contexts
            enhanced_context = base_context + "\n\n" + "="*50 + "\n"
            enhanced_context += instructions_context
            enhanced_context += "\n" + "="*50
            
            return enhanced_context
        
        return base_context
    
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
        """
        Get introduction message for starting an activity.
        Provides a brief, encouraging welcome. Detailed instructions are in system context
        for when the student asks "how does this work?"
        """
        # Normalize difficulty for lookup
        normalized_difficulty = normalize_difficulty(difficulty)
        
        # Activity names for display
        activity_names = {
            'multiple_choice': 'Word Quiz',
            'fill_in_the_blank': 'Fill It In',
            'spelling': 'Spell It',
            'bubble_pop': 'Bubble Fun',
            'fluent_reading': 'Read It'
        }
        
        activity_name = activity_names.get(activity_type, activity_type.replace('_', ' ').title())
        
        # Brief welcome prompt - don't explain all the rules, just greet warmly
        prompt = f"""Welcome {self.student_name} to {activity_name}!
Give a brief, encouraging greeting (1-2 sentences).
Don't explain all the rules - just say you're excited to do this activity together.
Keep it simple and warm."""
        
        return self._call_llm(prompt)
    
    def get_activity_feedback(self, activity_type: str, score: int, total: int, percentage: float) -> str:
        """Get feedback message after completing an activity"""
        prompt = f"""{self.student_name} got {score} out of {total} ({percentage:.0f}%).
Tell them they did good in 1 short sentence."""
        
        return self._call_llm(prompt)
