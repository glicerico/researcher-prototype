"""
Base definitions and imports for all node modules.
"""
import config
import os

from typing import Dict, List, Annotated, TypedDict, Optional, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Use the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

# Import from our utility module
from utils import get_current_datetime_str

# Import our storage components
from storage.storage_manager import StorageManager
from storage.user_manager import UserManager
from storage.conversation_manager import ConversationManager

# Import all prompt templates from prompts.py
from prompts import (
    # Router prompts
    ROUTER_SYSTEM_PROMPT,

    # Search prompts
    SEARCH_OPTIMIZER_SYSTEM_PROMPT,
    PERPLEXITY_SYSTEM_PROMPT,

    # Analysis prompts
    ANALYSIS_REFINER_SYSTEM_PROMPT,

    # Integrator prompts
    INTEGRATOR_SYSTEM_PROMPT,

    # Renderer prompts
    RESPONSE_RENDERER_SYSTEM_PROMPT
)

# Import all model classes from llm_models.py and models.py
from llm_models import (
    RoutingAnalysis,
    SearchQuery,
    AnalysisTask,
    FormattedResponse
)

# Initialize storage components
storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_data")
storage_manager = StorageManager(storage_dir)
user_manager = UserManager(storage_manager)
conversation_manager = ConversationManager(storage_manager, user_manager)

def convert_state_messages_to_langchain(state_messages: List[Dict[str, str]], include_system: bool = False) -> List:
    """
    Convert state messages to LangChain message objects consistently across all nodes.
    
    Args:
        state_messages: List of message dictionaries from state["messages"]
        include_system: Whether to include system messages in the conversion
        
    Returns:
        List of LangChain message objects (HumanMessage, AIMessage, SystemMessage)
    """
    langchain_messages = []
    
    for msg in state_messages:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        
        # Skip empty messages
        if not content:
            continue
            
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        elif role == "system" and include_system:
            langchain_messages.append(SystemMessage(content=content))
        # Skip system messages if include_system is False
    
    return langchain_messages

class ChatState(TypedDict):
    """Type definition for the chat state that flows through the graph."""
    messages: Annotated[List[Dict[str, str]], "The messages in the conversation"]
    langchain_messages: Annotated[Optional[List], "Converted LangChain message objects for LLM calls"]
    model: Annotated[str, "The model to use for the conversation"]
    temperature: Annotated[float, "The temperature to use for generation"]
    max_tokens: Annotated[int, "The maximum number of tokens to generate"]
    personality: Annotated[Optional[Dict[str, Any]], "User's personality configuration"]
    current_module: Annotated[Optional[str], "The current active module"]
    module_results: Annotated[Dict[str, Any], "Results from different modules"]
    workflow_context: Annotated[Dict[str, Any], "Contextual data for the current workflow execution."]
    user_id: Annotated[Optional[str], "The ID of the current user"]
    conversation_id: Annotated[Optional[str], "The ID of the current conversation"]
    routing_analysis: Annotated[Optional[Dict[str, Any]], "Analysis from the router"] 