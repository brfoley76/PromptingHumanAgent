"""
Simple Rule-Based Agent for Testing.
Provides tutoring without requiring LLM API calls.
Can be upgraded to real LLM agent later.
"""
from typing import Dict, List, Optional
from enum import Enum


class AgentResponse:
    """Structure for agent responses"""
    def __init__(self, message: str, hint_level: str = "none"):
        self.message = message
        self.hint_level = hint_level  # none, subtle, medium, explicit


class SimpleAgent:
    """
    Rule-based agent that provides tutoring for multiplication.
    Uses templates and context to generate appropriate responses.
    """
    
    def __init__(self, student_name: str, module_id: str):
        self.student_name = student_name
        self.module_id = module_id
        self.conversation_history = []
    
    def get_welcome_message(self) -> str:
        """Initial greeting when session starts"""
        return f"Hi {self.student_name}! Today we'll be studying multiplication! I'll give you 5 problems. Let's see how you do!"
    
    def get_correct_response(self, problem: Dict, is_retry: bool = False) -> AgentResponse:
        """Response when student answers correctly"""
        if is_retry:
            messages = [
                "Great work figuring that out!",
                "Excellent! You got it this time!",
                "Perfect! Nice job thinking it through!"
            ]
        else:
            messages = [
                "Excellent! That's correct!",
                "Great job! You got it!",
                "Perfect! Well done!",
                f"That's right! {problem['a']} × {problem['b']} = {problem['answer']}"
            ]
        
        # Simple rotation based on problem id
        idx = problem['id'] % len(messages)
        return AgentResponse(messages[idx])
    
    def get_error_introduction(self, problem: Dict, student_answer: int) -> AgentResponse:
        """Initial response when student makes an error"""
        return AgentResponse(
            "Hmm, I got a different answer. Let's think about this together.",
            hint_level="none"
        )
    
    def ask_for_reasoning(self, problem: Dict, student_answer: int) -> AgentResponse:
        """Socratic question - ask student to explain their thinking"""
        return AgentResponse(
            f"Can you tell me how you calculated {problem['a']} × {problem['b']} = {student_answer}?",
            hint_level="none"
        )
    
    def provide_hint(self, problem: Dict, student_answer: int, student_explanation: str) -> AgentResponse:
        """
        Provide contextual hint based on the problem and student's error.
        Uses the hint from the curriculum.
        """
        # Analyze the error
        correct_answer = problem['answer']
        diff = abs(student_answer - correct_answer)
        
        # Build hint message
        hint_intro = "I see! Let me give you a hint: "
        
        # Use curriculum hint
        hint = problem.get('hint', f"Think about {problem['a']} groups of {problem['b']}")
        
        # Add context based on error magnitude
        if diff < 10:
            context = "You're very close! "
        elif diff < 20:
            context = "You're getting there! "
        else:
            context = ""
        
        full_message = f"{context}{hint_intro}{hint}\n\nLet's try again. What is {problem['a']} × {problem['b']}?"
        
        return AgentResponse(full_message, hint_level="medium")
    
    def provide_full_explanation(self, problem: Dict) -> AgentResponse:
        """
        Provide complete explanation when student still can't get it.
        Uses the explanation from the curriculum.
        """
        explanation = problem.get('explanation', f"{problem['a']} × {problem['b']} = {problem['answer']}")
        
        message = f"Let me explain: {explanation}\n\nThe answer is {problem['answer']}. Let's move on to the next problem!"
        
        return AgentResponse(message, hint_level="explicit")
    
    def get_final_feedback(self, score: int, total: int) -> AgentResponse:
        """Final feedback based on overall performance"""
        percentage = (score / total) * 100
        
        if percentage >= 80:
            feedback = f"Excellent work, {self.student_name}! You got {score} out of {total} correct! You're really getting the hang of multiplication!"
        elif percentage >= 60:
            feedback = f"Good job, {self.student_name}! You got {score} out of {total} correct! Keep practicing and you'll master these!"
        else:
            feedback = f"Nice try, {self.student_name}! You got {score} out of {total} correct. Multiplication takes practice - keep working at it!"
        
        return AgentResponse(feedback)
    
    def record_message(self, sender: str, message: str):
        """Record message in conversation history"""
        self.conversation_history.append({
            'sender': sender,
            'message': message
        })


class TutorAgent(SimpleAgent):
    """Tutor agent for general session guidance"""
    pass


class ActivityAgent(SimpleAgent):
    """Activity-specific agent for multiplication practice"""
    pass
