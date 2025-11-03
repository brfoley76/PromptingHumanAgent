#!/usr/bin/env python3
"""
Terminal-based test client for the Agentic Learning Platform.
Tests the multiplication quiz with Socratic dialogue.
"""
import sys
from pathlib import Path
from typing import Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_db, get_db, Student, Session, ActivityAttempt, ChatMessage
from src.services.curriculum import CurriculumService
from src.services.activity import MultiplicationActivity
from src.agents.agent_factory import AgentFactory
from src.config import config
import json


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TerminalUI:
    """Terminal user interface for the multiplication quiz"""
    
    def __init__(self):
        self.db = next(get_db())
        self.student = None
        self.session = None
        self.activity = None
        self.agent = None
        self.module_id = "math_mult_001"
    
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}{text}{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.END}\n")
    
    def print_separator(self):
        """Print separator line"""
        print(f"{Colors.CYAN}{'─' * 60}{Colors.END}")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")
    
    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {text}{Colors.END}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.YELLOW}{text}{Colors.END}")
    
    def print_agent(self, text: str):
        """Print agent message"""
        print(f"{Colors.BLUE}🤖 Agent: {Colors.END}{text}")
    
    def get_input(self, prompt: str) -> str:
        """Get user input with colored prompt"""
        return input(f"{Colors.BOLD}{prompt}{Colors.END}")
    
    def register_student(self):
        """Register or get student"""
        self.print_header("Multiplication Practice")
        name = self.get_input("Welcome! What's your name? ")
        
        # Create student in database
        self.student = Student(name=name, grade_level=3)
        self.db.add(self.student)
        self.db.commit()
        
        print(f"\nNice to meet you, {name}!")
        return name
    
    def start_session(self):
        """Initialize learning session"""
        # Create session in database
        self.session = Session(
            student_id=self.student.student_id,
            module_id=self.module_id
        )
        self.db.add(self.session)
        self.db.commit()
        
        # Initialize activity
        self.activity = MultiplicationActivity(self.module_id, num_problems=5)
        
        # Initialize agent using factory (auto-selects LLM or simple based on config)
        print()
        self.agent = AgentFactory.create_activity_agent(self.student.name, self.module_id)
        
        # Show welcome message
        print()
        self.print_agent(self.agent.get_welcome_message())
        input(f"\n{Colors.BOLD}Press Enter to start...{Colors.END}")
    
    def run_quiz(self):
        """Run the multiplication quiz"""
        while not self.activity.is_complete():
            self.run_question()
    
    def run_question(self):
        """Run a single question with retry logic"""
        problem = self.activity.get_current_problem()
        problem_num = self.activity.get_problem_number()
        total = self.activity.get_total_problems()
        
        self.print_separator()
        print(f"\n{Colors.BOLD}Question {problem_num} of {total}{Colors.END}\n")
        
        # First attempt
        answer = self.get_answer(problem)
        is_correct, feedback_type = self.activity.submit_answer(answer, is_retry=False)
        
        if is_correct:
            # Correct on first try
            response = self.agent.get_correct_response(problem, is_retry=False)
            self.print_success(response.message)
            self.show_score()
            self.activity.next_problem()
        else:
            # Wrong on first try - start Socratic dialogue
            self.handle_error_with_dialogue(problem, answer)
    
    def get_answer(self, problem: Dict) -> int:
        """Get student's answer to a problem"""
        while True:
            try:
                answer_str = self.get_input(f"What is {problem['expression']}? ")
                return int(answer_str)
            except ValueError:
                self.print_error("Please enter a number.")
    
    def handle_error_with_dialogue(self, problem: Dict, wrong_answer: int):
        """Handle incorrect answer with Socratic dialogue"""
        # Step 1: Acknowledge error
        print()
        response = self.agent.get_error_introduction(problem, wrong_answer)
        self.print_agent(response.message)
        
        # Step 2: Ask for reasoning
        print()
        response = self.agent.ask_for_reasoning(problem, wrong_answer)
        self.print_agent(response.message)
        explanation = self.get_input("> ")
        
        # Step 3: Provide hint
        print()
        response = self.agent.provide_hint(problem, wrong_answer, explanation)
        self.print_agent(response.message)
        
        # Step 4: Allow retry
        print()
        retry_answer = self.get_answer(problem)
        is_correct, feedback_type = self.activity.submit_answer(retry_answer, is_retry=True)
        
        print()
        if is_correct:
            # Correct on retry
            response = self.agent.get_correct_response(problem, is_retry=True)
            self.print_success(response.message)
        else:
            # Still wrong - provide explanation
            self.print_error("Not quite.")
            print()
            response = self.agent.provide_full_explanation(problem)
            self.print_agent(response.message)
        
        self.show_score()
        self.activity.next_problem()
    
    def show_score(self):
        """Display current score"""
        score, total = self.activity.get_score()
        attempted = self.activity.get_problem_number()
        print(f"\n{Colors.BOLD}Score: {score}/{attempted}{Colors.END}")
    
    def show_final_results(self):
        """Display final results"""
        results = self.activity.get_results()
        
        self.print_separator()
        self.print_header("Final Results")
        
        print(f"{Colors.BOLD}You got {results['score']} out of {results['total']} correct!{Colors.END}")
        print(f"That's {results['percentage']}%!\n")
        
        # Agent final feedback
        response = self.agent.get_final_feedback(results['score'], results['total'])
        self.print_agent(response.message)
        
        # Store in database
        self.store_results(results)
    
    def store_results(self, results: Dict):
        """Store results in database"""
        attempt = ActivityAttempt(
            session_id=self.session.session_id,
            student_id=self.student.student_id,
            module=self.module_id,
            activity="multiplication_quiz",
            score=results['score'],
            total=results['total'],
            difficulty="easy",
            tuning_settings=json.dumps(self.activity.get_tuning_settings()),
            item_results=json.dumps(results['item_results'])
        )
        self.db.add(attempt)
        self.db.commit()
        
        print(f"\n{Colors.GREEN}Results saved to database!{Colors.END}")
    
    def run(self):
        """Main run loop"""
        try:
            # Register student
            name = self.register_student()
            
            # Start session
            self.start_session()
            
            # Run quiz
            self.run_quiz()
            
            # Show results
            self.show_final_results()
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Quiz interrupted. Goodbye!{Colors.END}")
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.END}")
            import traceback
            traceback.print_exc()
        finally:
            self.db.close()


def main():
    """Main entry point"""
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Run terminal UI
    ui = TerminalUI()
    ui.run()


if __name__ == "__main__":
    main()
