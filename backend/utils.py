"""
Utility functions used across the application.
"""
import time
from typing import List, Optional

def get_current_datetime_str() -> str:
    """Return the current date and time as a formatted string."""
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())

def get_last_user_message(messages: List["BaseMessage"]) -> Optional[str]:
    """
    Get the content of the last user message from a list of messages.
    
    Args:
        messages: List of BaseMessage objects (typically from state["messages"])
        
    Returns:
        The content of the last HumanMessage, or None if no HumanMessage found
    """
    # Import here to avoid circular imports
    from langchain_core.messages import HumanMessage
    
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None 