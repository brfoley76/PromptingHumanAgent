"""
Token counting utility for managing LLM context windows.
Uses tiktoken for accurate token counting.
"""
import tiktoken
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage


class TokenCounter:
    """
    Utility for counting tokens in messages and managing context windows.
    """
    
    # Token limits
    MAX_TOKENS_WARNING = 150000
    MAX_TOKENS_LIMIT = 180000
    MAX_TOKENS_HARD_LIMIT = 190000
    
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize token counter with model-specific encoding.
        
        Args:
            model_name: Name of the model (for encoding selection)
        """
        # Use cl100k_base encoding for Claude models (similar to GPT-4)
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback to a common encoding
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def count_message_tokens(self, message: BaseMessage) -> int:
        """
        Count tokens in a LangChain message.
        
        Args:
            message: LangChain message object
            
        Returns:
            Number of tokens
        """
        # Count content tokens
        content_tokens = self.count_tokens(str(message.content))
        
        # Add overhead for message formatting (role, etc.)
        # Approximate: 4 tokens per message for formatting
        return content_tokens + 4
    
    def count_messages_tokens(self, messages: List[BaseMessage]) -> int:
        """
        Count total tokens in a list of messages.
        
        Args:
            messages: List of LangChain messages
            
        Returns:
            Total number of tokens
        """
        return sum(self.count_message_tokens(msg) for msg in messages)
    
    def check_token_limit(self, messages: List[BaseMessage], new_prompt: str = "") -> Dict[str, Any]:
        """
        Check if messages are within token limits.
        
        Args:
            messages: List of messages to check
            new_prompt: Optional new prompt to add
            
        Returns:
            Dict with status, token_count, and warning/error messages
        """
        total_tokens = self.count_messages_tokens(messages)
        
        if new_prompt:
            total_tokens += self.count_tokens(new_prompt) + 4  # +4 for message overhead
        
        result = {
            "token_count": total_tokens,
            "status": "ok",
            "message": None
        }
        
        if total_tokens >= self.MAX_TOKENS_HARD_LIMIT:
            result["status"] = "error"
            result["message"] = f"Token limit exceeded: {total_tokens} tokens (max: {self.MAX_TOKENS_HARD_LIMIT})"
        elif total_tokens >= self.MAX_TOKENS_LIMIT:
            result["status"] = "critical"
            result["message"] = f"Approaching token limit: {total_tokens} tokens (limit: {self.MAX_TOKENS_LIMIT})"
        elif total_tokens >= self.MAX_TOKENS_WARNING:
            result["status"] = "warning"
            result["message"] = f"High token usage: {total_tokens} tokens (warning threshold: {self.MAX_TOKENS_WARNING})"
        
        return result
    
    def truncate_messages(self, messages: List[BaseMessage], max_tokens: int) -> List[BaseMessage]:
        """
        Truncate messages to fit within token limit.
        Keeps system message and most recent messages.
        
        Args:
            messages: List of messages to truncate
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated list of messages
        """
        if not messages:
            return []
        
        # Always keep system message if present
        system_msg = None
        other_messages = messages
        
        if isinstance(messages[0], SystemMessage):
            system_msg = messages[0]
            other_messages = messages[1:]
        
        # Start with system message tokens
        current_tokens = self.count_message_tokens(system_msg) if system_msg else 0
        
        # Add messages from most recent, working backwards
        kept_messages = []
        for msg in reversed(other_messages):
            msg_tokens = self.count_message_tokens(msg)
            if current_tokens + msg_tokens <= max_tokens:
                kept_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        # Reconstruct with system message first
        result = []
        if system_msg:
            result.append(system_msg)
        result.extend(kept_messages)
        
        return result


# Global instance
_token_counter = None


def get_token_counter(model_name: str = "claude-3-5-sonnet-20241022") -> TokenCounter:
    """
    Get or create global token counter instance.
    
    Args:
        model_name: Model name for encoding
        
    Returns:
        TokenCounter instance
    """
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter(model_name)
    return _token_counter
