"""
Agent Factory - Creates appropriate agent based on configuration.
Handles fallback from LLM to simple agent if LLM is not configured.
"""
from typing import Union
from ..config import config
from .simple_agent import SimpleAgent, TutorAgent as SimpleTutorAgent, ActivityAgent as SimpleActivityAgent
from .llm_agent import LLMAgent, TutorAgent as LLMTutorAgent, ActivityAgent as LLMActivityAgent


class AgentFactory:
    """Factory for creating agents with automatic fallback"""
    
    @staticmethod
    def create_activity_agent(student_name: str, module_id: str, 
                             force_type: str = None) -> Union[SimpleActivityAgent, LLMActivityAgent]:
        """
        Create an activity agent based on configuration.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
            force_type: Force 'simple' or 'llm' agent type, overriding config
            
        Returns:
            Activity agent instance (LLM if configured, Simple as fallback)
        """
        agent_type = force_type or config.AGENT_TYPE
        
        if agent_type == "llm" and config.has_llm_configured():
            try:
                print("✓ Using LLM-powered agent")
                return LLMActivityAgent(student_name, module_id)
            except Exception as e:
                print(f"⚠ LLM agent initialization failed: {e}")
                print("↳ Falling back to simple rule-based agent")
                return SimpleActivityAgent(student_name, module_id)
        else:
            if agent_type == "llm":
                print("⚠ LLM requested but not configured (missing API key)")
                print("↳ Using simple rule-based agent")
            else:
                print("✓ Using simple rule-based agent")
            return SimpleActivityAgent(student_name, module_id)
    
    @staticmethod
    def create_tutor_agent(student_name: str, module_id: str,
                          activity_state: dict = None,
                          force_type: str = None) -> Union[SimpleTutorAgent, LLMTutorAgent]:
        """
        Create a tutor agent based on configuration.
        
        Args:
            student_name: Name of the student
            module_id: Curriculum module ID
            activity_state: Optional dict with activity availability info
            force_type: Force 'simple' or 'llm' agent type, overriding config
            
        Returns:
            Tutor agent instance (LLM if configured, Simple as fallback)
        """
        agent_type = force_type or config.AGENT_TYPE
        
        if agent_type == "llm" and config.has_llm_configured():
            try:
                return LLMTutorAgent(student_name, module_id, activity_state=activity_state)
            except Exception as e:
                print(f"⚠ LLM agent initialization failed: {e}")
                print("↳ Falling back to simple rule-based agent")
                return SimpleTutorAgent(student_name, module_id)
        else:
            return SimpleTutorAgent(student_name, module_id)
    
    @staticmethod
    def get_available_agent_types() -> list:
        """Get list of available agent types"""
        types = ["simple"]
        if config.has_llm_configured():
            types.append("llm")
        return types
    
    @staticmethod
    def print_agent_status():
        """Print current agent configuration status"""
        print(f"\n{'='*60}")
        print("Agent Configuration")
        print(f"{'='*60}")
        print(f"Default Agent Type: {config.AGENT_TYPE}")
        print(f"LLM Provider: {config.LLM_PROVIDER}")
        print(f"LLM Model: {config.MODEL_NAME}")
        print(f"LLM Configured: {'Yes' if config.has_llm_configured() else 'No'}")
        
        if config.AGENT_TYPE == "llm" and not config.has_llm_configured():
            print(f"\n⚠ WARNING: LLM agent selected but API key not configured!")
            print(f"  Set OPENAI_API_KEY in .env file or environment")
            print(f"  Will use simple rule-based agent as fallback")
        
        print(f"{'='*60}\n")
