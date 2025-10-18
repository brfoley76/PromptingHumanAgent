"""
Configuration management for the Agentic Learning Platform.
Handles environment variables and settings.
"""
import os
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


class Config:
    """Application configuration"""
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, or none
    
    # Agent Configuration
    AGENT_TYPE: str = os.getenv("AGENT_TYPE", "simple")  # simple or llm
    AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
    AGENT_MAX_TOKENS: int = int(os.getenv("AGENT_MAX_TOKENS", "500"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./learning.db")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    @classmethod
    def has_llm_configured(cls) -> bool:
        """Check if LLM is properly configured"""
        if cls.LLM_PROVIDER == "openai":
            return cls.OPENAI_API_KEY is not None
        elif cls.LLM_PROVIDER == "anthropic":
            return cls.ANTHROPIC_API_KEY is not None
        return False
    
    @classmethod
    def get_llm_config(cls) -> dict:
        """Get LLM configuration dict"""
        return {
            "provider": cls.LLM_PROVIDER,
            "model_name": cls.MODEL_NAME,
            "temperature": cls.AGENT_TEMPERATURE,
            "max_tokens": cls.AGENT_MAX_TOKENS,
            "api_key": cls.OPENAI_API_KEY if cls.LLM_PROVIDER == "openai" else cls.ANTHROPIC_API_KEY
        }


# Global config instance
config = Config()
