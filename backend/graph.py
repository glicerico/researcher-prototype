from typing import Dict, List, Annotated, TypedDict, Sequence, Optional, Union, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import config
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
import os
from pathlib import Path

# Import our storage components
from storage.storage_manager import StorageManager
from storage.user_manager import UserManager
from storage.conversation_manager import ConversationManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize storage components
storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_data")
storage_manager = StorageManager(storage_dir)
user_manager = UserManager(storage_manager)
conversation_manager = ConversationManager(storage_manager, user_manager)


class ChatState(TypedDict):
    messages: Annotated[List[Dict[str, str]], "The messages in the conversation"]
    model: Annotated[str, "The model to use for the conversation"]
    temperature: Annotated[float, "The temperature to use for generation"]
    max_tokens: Annotated[int, "The maximum number of tokens to generate"]
    personality: Annotated[Optional[Dict[str, Any]], "User's personality configuration"]
    current_module: Annotated[Optional[str], "The current active module"]
    module_results: Annotated[Dict[str, Any], "Results from different modules"]
    orchestrator_state: Annotated[Dict[str, Any], "State maintained by the orchestrator"]
    user_id: Annotated[Optional[str], "The ID of the current user"]
    conversation_id: Annotated[Optional[str], "The ID of the current conversation"]


def create_chat_graph():
    """Create a LangGraph for chat processing with an orchestrator."""
    
    # Define the orchestrator node
    def orchestrator_node(state: ChatState) -> ChatState:
        """Central coordinator that routes messages to appropriate modules."""
        logger.debug(f"Orchestrator node received state: {state}")
        
        # Initialize orchestrator state if it doesn't exist
        if "orchestrator_state" not in state or not state["orchestrator_state"]:
            state["orchestrator_state"] = {}
        
        # Initialize module_results if it doesn't exist
        if "module_results" not in state or not state["module_results"]:
            state["module_results"] = {}
            
        # Initialize personality if it doesn't exist
        if "personality" not in state or not state["personality"]:
            state["personality"] = {"style": "helpful", "tone": "friendly"}
        
        # Handle user management - create or get user
        user_id = state.get("user_id")
        if not user_id or not user_manager.user_exists(user_id):
            # Create a new user if needed
            user_id = user_manager.create_user({
                "created_from": "chat_graph",
                "initial_personality": state.get("personality", {})
            })
            state["user_id"] = user_id
            logger.info(f"Created new user: {user_id}")
        else:
            # Update personality from stored preferences if not explicitly provided
            if not state.get("personality"):
                state["personality"] = user_manager.get_personality(user_id)
                logger.debug(f"Loaded personality for user {user_id}: {state['personality']}")
                
        # Handle conversation management
        conversation_id = state.get("conversation_id")
        if not conversation_id or not conversation_manager.get_conversation(user_id, conversation_id):
            # Create a new conversation
            conversation_id = conversation_manager.create_conversation(user_id, {
                "name": f"Conversation {conversation_manager.list_conversations(user_id).__len__() + 1}",
                "model": state.get("model", config.DEFAULT_MODEL)
            })
            state["conversation_id"] = conversation_id
            logger.info(f"Created new conversation: {conversation_id} for user: {user_id}")
            
            # Add any existing messages to the conversation
            for message in state.get("messages", []):
                conversation_manager.add_message(
                    user_id, 
                    conversation_id,
                    message.get("role"),
                    message.get("content"),
                    message.get("metadata", {})
                )
        
        # Get the last user message
        last_message = None
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                last_message = msg["content"]
                break
                
        if not last_message:
            state["current_module"] = "chat"  # Default to chat module if no user message
            return state
            
        # Simple routing logic - can be enhanced with more sophisticated intent detection
        if "search" in last_message.lower() or "find" in last_message.lower():
            state["current_module"] = "search"
        elif "analyze" in last_message.lower() or "data" in last_message.lower():
            state["current_module"] = "analyzer"
        else:
            state["current_module"] = "chat"
            
        logger.debug(f"Orchestrator routed to module: {state['current_module']}")
        return state
    
    # Define the chat module node
    def chat_node(state: ChatState) -> ChatState:
        """Process the chat using the specified model."""
        logger.debug(f"Chat node received state: {state}")
        model = state.get("model", config.DEFAULT_MODEL)
        temperature = state.get("temperature", 0.7)
        max_tokens = state.get("max_tokens", 1000)
        personality = state.get("personality", {})
        
        # Create system message based on personality if available
        system_message_content = "You are a helpful assistant."
        if personality:
            style = personality.get("style", "helpful")
            tone = personality.get("tone", "friendly")
            system_message_content = f"You are a {style} assistant. Please respond in a {tone} tone."
        
        # Initialize the model
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=config.OPENAI_API_KEY
        )
        
        # Convert dict messages to LangChain message objects
        langchain_messages = []
        
        # Add system message first
        langchain_messages.append(SystemMessage(content=system_message_content))
        
        for msg in state["messages"]:
            role = msg["role"]
            content = msg["content"]
            
            # Skip system messages as we've already added our own
            if role == "system":
                continue
                
            # Trim whitespace from content
            if isinstance(content, str):
                content = content.strip()
            
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                logger.warning(f"Unknown message role: {role}")
        
        try:
            logger.debug(f"Sending messages to LLM: {langchain_messages}")
            
            # Ensure we have at least one message
            if not langchain_messages:
                raise ValueError("No valid messages to send to the model")
            
            response = llm.invoke(langchain_messages)
            logger.debug(f"Received response: {response}")
            
            # Create the response message
            assistant_message = {
                "role": "assistant", 
                "content": response.content,
                "metadata": {"model": model, "module": "chat"}
            }
            
            # Add the response to the messages in state
            state["messages"].append(assistant_message)
            
            # Store the result in module_results
            state["module_results"]["chat"] = response.content
            
            # Save the response to conversation history
            user_id = state.get("user_id")
            conversation_id = state.get("conversation_id")
            if user_id and conversation_id:
                conversation_manager.add_message(
                    user_id,
                    conversation_id,
                    "assistant",
                    response.content,
                    {"model": model, "module": "chat"}
                )
            
        except Exception as e:
            logger.error(f"Error in chat_node: {str(e)}", exc_info=True)
            # Add an error message to the state
            state["error"] = str(e)
        
        return state
        
    # Define the search module node (placeholder for demonstration)
    def search_node(state: ChatState) -> ChatState:
        """Search module that handles search-related queries."""
        logger.debug(f"Search node received state: {state}")
        
        # In a real implementation, this would connect to a search engine or database
        # For now, we'll simulate a search response
        
        # Get the last user message
        last_message = None
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                last_message = msg["content"]
                break
        
        # Generate a simulated search response
        search_response = f"I searched for information about '{last_message}' and found some relevant results. [This is a simulated search response]"
        
        # Create the response message
        assistant_message = {
            "role": "assistant", 
            "content": search_response,
            "metadata": {"module": "search"}
        }
        
        # Add the response to the messages in state
        state["messages"].append(assistant_message)
        
        # Store the result in module_results
        state["module_results"]["search"] = search_response
        
        # Save the response to conversation history
        user_id = state.get("user_id")
        conversation_id = state.get("conversation_id")
        if user_id and conversation_id:
            conversation_manager.add_message(
                user_id,
                conversation_id,
                "assistant",
                search_response,
                {"module": "search"}
            )
        
        return state
        
    # Define the analyzer module node (placeholder for demonstration)
    def analyzer_node(state: ChatState) -> ChatState:
        """Analyzer module that processes data-related queries."""
        logger.debug(f"Analyzer node received state: {state}")
        
        # In a real implementation, this would analyze data
        # For now, we'll simulate an analysis response
        
        # Get the last user message
        last_message = None
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                last_message = msg["content"]
                break
        
        # Generate a simulated analysis response
        analysis_response = f"I analyzed the data related to '{last_message}' and found some interesting patterns. [This is a simulated analysis response]"
        
        # Create the response message
        assistant_message = {
            "role": "assistant", 
            "content": analysis_response,
            "metadata": {"module": "analyzer"}
        }
        
        # Add the response to the messages in state
        state["messages"].append(assistant_message)
        
        # Store the result in module_results
        state["module_results"]["analyzer"] = analysis_response
        
        # Save the response to conversation history
        user_id = state.get("user_id")
        conversation_id = state.get("conversation_id")
        if user_id and conversation_id:
            conversation_manager.add_message(
                user_id,
                conversation_id,
                "assistant",
                analysis_response,
                {"module": "analyzer"}
            )
        
        return state
    
    # Define the router function for conditional branching
    def router(state: ChatState) -> str:
        """Route to the appropriate module based on the current_module state."""
        return state["current_module"]
    
    # Create the graph
    builder = StateGraph(ChatState)
    
    # Add the nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("chat", chat_node)
    builder.add_node("search", search_node)
    builder.add_node("analyzer", analyzer_node)
    
    # Set the entry point
    builder.set_entry_point("orchestrator")
    
    # Add edges with conditional routing
    builder.add_conditional_edges(
        "orchestrator",
        router,
        {
            "chat": "chat",
            "search": "search",
            "analyzer": "analyzer"
        }
    )
    
    # Set all processing nodes to end
    builder.add_edge("chat", END)
    builder.add_edge("search", END)
    builder.add_edge("analyzer", END)
    
    # Compile the graph
    graph = builder.compile()
    
    return graph


# Create a singleton instance of the graph
chat_graph = create_chat_graph() 