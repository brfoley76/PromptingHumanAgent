"""
Simple Rule-Based Agent for Testing.
Provides tutoring without requiring LLM API calls.
Can be upgraded to real LLM agent later.
"""
from typing import Dict, List, Optional
from enum import Enum
from ..services.curriculum import CurriculumService


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
        
        # Load curriculum to be context-aware
        try:
            self.curriculum = CurriculumService.load_curriculum(module_id)
        except:
            self.curriculum = None
    
    def get_welcome_message(self) -> str:
        """Initial greeting when session starts - context-aware based on curriculum"""
        if not self.curriculum:
            return f"Ahoy {self.student_name}! Welcome aboard! Let's start learning!"
        
        # Get module info
        module_title = self.curriculum.get('title', 'Learning Module')
        module_description = self.curriculum.get('description', '')
        
        # Get some vocabulary words to mention
        vocab = self.curriculum.get('content', {}).get('vocabulary', [])
        if vocab and len(vocab) >= 3:
            sample_words = [v['word'] for v in vocab[:3]]
            words_text = f"words like {', '.join(sample_words)}"
        else:
            words_text = "new vocabulary"
        
        # Generate context-appropriate greeting
        greeting = f"Ahoy there, {self.student_name}! Welcome to {module_title}! "
        greeting += f"Today we'll be learning {words_text}. "
        greeting += "Ready to set sail on this learning adventure? ⚓"
        
        return greeting
    
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
    
    def get_activity_intro(self, activity_type: str, difficulty: str) -> str:
        """Get introduction message for starting an activity"""
        intros = {
            'multiple_choice': f"Let's practice with multiple choice! I'll show you some definitions and you pick the right word.",
            'fill_in_the_blank': f"Time for fill in the blank! Drag the words to complete the definitions.",
            'spelling': f"Let's work on spelling! I'll give you definitions and you spell the words.",
            'bubble_pop': f"Ready for Bubble Pop? Click on bubbles to identify correct and incorrect spellings!",
            'fluent_reading': f"Let's practice reading fluently! Read along as the text streams across the screen."
        }
        
        base_intro = intros.get(activity_type, "Let's practice!")
        
        if difficulty in ['hard', '5']:
            return f"{base_intro} This is a challenging level - you've got this!"
        elif difficulty in ['medium', '4']:
            return f"{base_intro} This is a good level for you!"
        else:
            return f"{base_intro} Let's start with the basics!"
    
    def get_activity_feedback(self, activity_type: str, score: int, total: int, percentage: float) -> str:
        """Get feedback message after completing an activity"""
        if percentage >= 90:
            feedback = f"Excellent work! You got {score} out of {total} correct ({percentage:.0f}%)! You're really mastering this!"
        elif percentage >= 80:
            feedback = f"Great job! You got {score} out of {total} correct ({percentage:.0f}%)! Keep up the good work!"
        elif percentage >= 70:
            feedback = f"Good effort! You got {score} out of {total} correct ({percentage:.0f}%)! You're making progress!"
        elif percentage >= 60:
            feedback = f"Nice try! You got {score} out of {total} correct ({percentage:.0f}%)! Keep practicing!"
        else:
            feedback = f"You got {score} out of {total} correct ({percentage:.0f}%). Don't worry - practice makes perfect!"
        
        return feedback
