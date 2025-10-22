"""
LLM-powered agent using LangChain and OpenAI/Anthropic.
Provides dynamic, contextual tutoring with Socratic dialogue.
"""
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ..config import config
from ..services.curriculum import CurriculumService
from .simple_agent import AgentResponse


class LLMAgent:
    """
    LLM-powered agent that provides intelligent tutoring.
    Uses the same interface as SimpleAgent for easy swapping.
    """
    
    def __init__(self, student_name: str, module_id: str):
        """
        Initialize LLM agent with curriculum context.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
        """
        self.student_name = student_name
        self.module_id = module_id
        self.conversation_history = []
        
        # Load curriculum for context
        self.curriculum = CurriculumService.load_curriculum(module_id)
        self.vocabulary = self.curriculum.get('content', {}).get('vocabulary', [])
        self.problems = self.curriculum.get('content', {}).get('problems', [])
        
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
        
        # Build vocabulary list
        vocab_text = "\n".join([
            f"- {v['word']}: {v['definition']}" 
            for v in self.vocabulary
        ])
        
        return f"""You are a friendly, patient tutor helping {self.student_name}, a {grade_level} grade student.

CURRENT MODULE: {module_title}
{module_description}

CURRICULUM VOCABULARY:
{vocab_text}

YOUR TEACHING STYLE:
- Be warm and encouraging with a pirate theme (use "Ahoy", "matey", etc.)
- Use simple, age-appropriate language ({grade_level} grade level)
- Keep responses brief (2-3 sentences maximum)
- Help students learn vocabulary words and their meanings
- Reference the curriculum vocabulary when relevant
- Be patient and supportive
- Celebrate progress enthusiastically

IMPORTANT:
- Focus on the vocabulary and reading skills in this module
- Use the pirate theme to make learning fun
- Keep explanations simple and clear
- Encourage students to practice the exercises"""
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM with proper context and error handling.
        
        Args:
            prompt: The user prompt
            
        Returns:
            LLM response text
        """
        try:
            messages = [
                SystemMessage(content=self.system_context),
                *self.conversation_history,
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Store in history
            self.conversation_history.append(HumanMessage(content=prompt))
            self.conversation_history.append(AIMessage(content=response.content))
            
            return response.content
            
        except Exception as e:
            # Fallback to simple message if LLM fails
            print(f"LLM Error: {e}")
            return "Let me think about that..."
    
    def get_welcome_message(self) -> str:
        """Initial greeting when session starts"""
        module_title = self.curriculum.get('title', 'Learning Module')
        
        # Get a few sample words
        sample_words = []
        if len(self.vocabulary) >= 3:
            sample_words = [v['word'] for v in self.vocabulary[:3]]
        
        words_mention = f"words like {', '.join(sample_words)}" if sample_words else "new vocabulary"
        
        prompt = f"""Greet {self.student_name} warmly and welcome them to {module_title}. 
Mention that today they'll be learning {words_mention}.
Use a pirate theme (Ahoy, matey, etc.) and keep it brief and encouraging (2-3 sentences)!"""
        
        return self._call_llm(prompt)
    
    def get_correct_response(self, problem: Dict, is_retry: bool = False) -> AgentResponse:
        """Response when student answers correctly"""
        if is_retry:
            prompt = f"""{self.student_name} got {problem['expression']} correct on their second try! 
Give them enthusiastic praise for figuring it out. Keep it brief!"""
        else:
            prompt = f"""{self.student_name} correctly answered {problem['expression']} = {problem['answer']}! 
Give them enthusiastic praise. Keep it brief!"""
        
        message = self._call_llm(prompt)
        return AgentResponse(message)
    
    def get_error_introduction(self, problem: Dict, student_answer: int) -> AgentResponse:
        """Initial response when student makes an error"""
        prompt = f"""{self.student_name} answered {problem['expression']} = {student_answer}, 
but the correct answer is {problem['answer']}.

Gently acknowledge they got a different answer and let them know you'll help them think it through. 
Be warm and supportive. Keep it very brief (1-2 sentences)!"""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="none")
    
    def ask_for_reasoning(self, problem: Dict, student_answer: int) -> AgentResponse:
        """Socratic question - ask student to explain their thinking"""
        prompt = f"""Ask {self.student_name} to explain how they calculated {problem['expression']} = {student_answer}.
Use a Socratic approach - be curious about their thinking process. 
Keep it brief and friendly!"""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="none")
    
    def provide_hint(self, problem: Dict, student_answer: int, student_explanation: str) -> AgentResponse:
        """
        Provide contextual hint based on the problem and student's error.
        Uses curriculum hint but delivers it through LLM for natural language.
        """
        curriculum_hint = problem.get('hint', f"Think about {problem['a']} groups of {problem['b']}")
        
        prompt = f"""The student explained: "{student_explanation}"

The problem is {problem['expression']}.
Curriculum hint: {curriculum_hint}

Provide a helpful hint that guides them toward the answer WITHOUT giving it away.
Acknowledge their effort, give the hint, then ask them to try again.
Keep it encouraging and brief (2-3 sentences)!"""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="medium")
    
    def provide_full_explanation(self, problem: Dict) -> AgentResponse:
        """
        Provide complete explanation when student still can't get it.
        """
        explanation = problem.get('explanation', f"{problem['a']} × {problem['b']} = {problem['answer']}")
        
        prompt = f"""The student needs the full explanation for {problem['expression']}.

Curriculum explanation: {explanation}

Explain the answer clearly using simple language. 
Show them how to think about it, then encourage them to move on to the next problem.
Keep it brief and supportive!"""
        
        message = self._call_llm(prompt)
        return AgentResponse(message, hint_level="explicit")
    
    def get_final_feedback(self, score: int, total: int) -> AgentResponse:
        """Final feedback based on overall performance"""
        percentage = (score / total) * 100
        
        prompt = f"""{self.student_name} completed the multiplication quiz!
Score: {score} out of {total} ({percentage:.0f}%)

Give them encouraging final feedback based on their performance.
Celebrate what they did well and give them motivation to keep practicing.
Keep it warm and supportive (2-3 sentences)!"""
        
        message = self._call_llm(prompt)
        return AgentResponse(message)
    
    def record_message(self, sender: str, message: str):
        """Record message in conversation history"""
        # Already handled in _call_llm
        pass


class TutorAgent(LLMAgent):
    """LLM tutor agent for general session guidance"""
    pass


class ActivityAgent(LLMAgent):
    """LLM activity-specific agent for vocabulary practice"""
    
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
        
        prompt = f"""Introduce the {activity_name} activity to {self.student_name}.
Explain briefly what they'll be doing and encourage them.
Mention the difficulty level is {difficulty}.
Use pirate theme and keep it brief (1-2 sentences)!"""
        
        return self._call_llm(prompt)
    
    def get_activity_feedback(self, activity_type: str, score: int, total: int, percentage: float) -> str:
        """Get feedback message after completing an activity"""
        prompt = f"""{self.student_name} just completed {activity_type}!
Score: {score} out of {total} ({percentage:.0f}%)

Give them encouraging feedback based on their performance.
Use pirate theme and keep it brief (2-3 sentences)!"""
        
        return self._call_llm(prompt)
