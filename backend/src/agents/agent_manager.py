"""
Agent Manager - Coordinates between persistent tutor and ephemeral activity agents.
Provides clean lifecycle management and message routing.
"""
from typing import Optional, Dict, Any
from .llm_agent import TutorAgent, ActivityAgent


class AgentManager:
    """
    Manages agent lifecycle and message routing for a session.
    
    - Maintains one persistent TutorAgent for general guidance
    - Creates/destroys ActivityAgent instances as needed
    - Routes messages to appropriate agent based on context
    """
    
    def __init__(self, student_name: str, module_id: str):
        """
        Initialize agent manager with persistent tutor.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
        """
        self.student_name = student_name
        self.module_id = module_id
        
        # Persistent tutor agent for general session guidance
        self.tutor = TutorAgent(student_name, module_id)
        
        # Ephemeral activity agent (created/destroyed per activity)
        self.current_activity_agent: Optional[ActivityAgent] = None
        self.current_activity_type: Optional[str] = None
        self.current_difficulty: Optional[str] = None
    
    def start_activity(self, activity_type: str, difficulty: str) -> str:
        """
        Start a new activity and create its agent.
        
        Args:
            activity_type: Type of activity (e.g., 'multiple_choice')
            difficulty: Difficulty level (e.g., '3', '4', '5')
            
        Returns:
            Welcome message from activity agent
        """
        # Clean up any existing activity agent
        if self.current_activity_agent:
            self.end_activity()
        
        # Create new activity agent with filtered vocabulary context
        self.current_activity_agent = ActivityAgent(
            self.student_name,
            self.module_id,
            activity_type=activity_type,
            difficulty=difficulty
        )
        self.current_activity_type = activity_type
        self.current_difficulty = difficulty
        
        # Get welcome message
        welcome = self.current_activity_agent.get_activity_intro(
            activity_type,
            difficulty
        )
        
        print(f"✅ Activity agent created: {activity_type} ({difficulty})")
        return welcome
    
    def end_activity(self, score: Optional[int] = None, total: Optional[int] = None) -> Optional[str]:
        """
        End current activity and clean up its agent.
        
        Args:
            score: Final score (optional)
            total: Total possible score (optional)
            
        Returns:
            Feedback message if score provided, None otherwise
        """
        feedback = None
        
        if self.current_activity_agent and score is not None and total is not None:
            # Get final feedback before destroying agent
            percentage = (score / total * 100) if total > 0 else 0
            feedback = self.current_activity_agent.get_activity_feedback(
                self.current_activity_type,
                score,
                total,
                percentage
            )
        
        # Clean up
        self.current_activity_agent = None
        self.current_activity_type = None
        self.current_difficulty = None
        
        print(f"🧹 Activity agent destroyed")
        return feedback
    
    def handle_wrong_answer(self, question_data: Dict[str, Any], attempt_number: int = 1) -> str:
        """
        Handle wrong answer event with contextual LLM response.
        
        Args:
            question_data: Dict with 'definition', 'correct_answer', 'user_answer', 'choices'
            attempt_number: Which attempt this is (1, 2, 3...)
            
        Returns:
            Contextual help message from LLM
        """
        if not self.current_activity_agent:
            return "Keep trying! You can do this!"
        
        # Build rich context for LLM
        definition = question_data.get('definition', '')
        correct_answer = question_data.get('correct_answer', '')
        user_answer = question_data.get('user_answer', '')
        choices = question_data.get('choices', [])
        
        # Determine hint level based on difficulty and attempt
        hint_level = self._determine_hint_level(attempt_number)
        
        # Get LLM response with full context
        prompt = self._build_wrong_answer_prompt(
            definition,
            correct_answer,
            user_answer,
            choices,
            attempt_number,
            hint_level
        )
        
        return self.current_activity_agent._call_llm(prompt)
    
    def handle_correct_answer(self, question_data: Dict[str, Any], is_retry: bool = False) -> str:
        """
        Handle correct answer with encouraging response.
        
        Args:
            question_data: Dict with question details
            is_retry: Whether this was correct after retry
            
        Returns:
            Encouraging message from LLM
        """
        if not self.current_activity_agent:
            return "Well done!"
        
        word = question_data.get('correct_answer', 'that')
        
        if is_retry:
            prompt = f"{self.student_name} got '{word}' correct after trying again. Say 'Good job' in 1 short sentence."
        else:
            prompt = f"{self.student_name} got '{word}' correct. Say 'Good' in 1 short sentence."
        
        return self.current_activity_agent._call_llm(prompt)
    
    def handle_chat_message(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Handle chat message - route to appropriate agent.
        
        Args:
            message: Student's message
            context: Optional context (activity type, etc.)
            
        Returns:
            Agent response
        """
        # If in activity, use activity agent
        if self.current_activity_agent and context and context.get('in_activity'):
            prompt = f"{self.student_name} asks: '{message}'\nAnswer in 1 short sentence."
            return self.current_activity_agent._call_llm(prompt)
        
        # Otherwise use tutor
        return self.tutor._call_llm(message)
    
    def _determine_hint_level(self, attempt_number: int) -> str:
        """Determine hint level based on difficulty and attempt number"""
        if self.current_difficulty == '3':  # Easy
            # Progressive hints
            if attempt_number == 1:
                return 'gentle'
            elif attempt_number == 2:
                return 'specific'
            else:
                return 'explicit'
        
        elif self.current_difficulty == '4':  # Medium
            # One hint only
            return 'moderate'
        
        else:  # Hard
            # No hints during activity
            return 'none'
    
    def _build_wrong_answer_prompt(
        self,
        definition: str,
        correct_answer: str,
        user_answer: str,
        choices: list,
        attempt_number: int,
        hint_level: str
    ) -> str:
        """Build contextual prompt for wrong answer"""
        
        base = f"""The student is learning vocabulary. They're trying to match definitions with words.

QUESTION: "{definition}"
CHOICES: {', '.join(choices)}
STUDENT ANSWERED: "{user_answer}"
CORRECT ANSWER: "{correct_answer}"
ATTEMPT: #{attempt_number}
DIFFICULTY: {self.current_difficulty} (3=easy, 4=medium, 5=hard)
"""
        
        if hint_level == 'gentle':
            return base + f"\nGive a gentle hint. Use 1 short sentence."
        
        elif hint_level == 'specific':
            return base + f"\nGive a clear hint. Use 1 short sentence."
        
        elif hint_level == 'explicit':
            return base + f"\nGive a very clear hint. Use 1 short sentence."
        
        elif hint_level == 'moderate':
            return base + f"\nGive one helpful hint. Use 1 short sentence."
        
        else:  # none
            return base + f"\nSay they got it wrong. Use 1 short sentence."
    
    def get_tutor(self) -> TutorAgent:
        """Get the persistent tutor agent"""
        return self.tutor
    
    def get_activity_agent(self) -> Optional[ActivityAgent]:
        """Get current activity agent if one exists"""
        return self.current_activity_agent
    
    def is_in_activity(self) -> bool:
        """Check if currently in an activity"""
        return self.current_activity_agent is not None
