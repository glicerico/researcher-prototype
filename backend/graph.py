from typing import Dict, List, Annotated, TypedDict, Sequence
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import config
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    messages: Annotated[List[Dict[str, str]], "The messages in the conversation"]
    model: Annotated[str, "The model to use for the conversation"]
    temperature: Annotated[float, "The temperature to use for generation"]
    max_tokens: Annotated[int, "The maximum number of tokens to generate"]


def create_chat_graph():
    """Create a LangGraph for chat processing."""
    
    # Define the nodes
    def chat_node(state: ChatState) -> ChatState:
        """Process the chat using the specified model."""
        logger.debug(f"Chat node received state: {state}")
        model = state.get("model", config.DEFAULT_MODEL)
        temperature = state.get("temperature", 0.7)
        max_tokens = state.get("max_tokens", 1000)
        
        # Initialize the model
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=config.OPENAI_API_KEY
        )
        
        # Convert dict messages to LangChain message objects
        langchain_messages = []
        for msg in state["messages"]:
            role = msg["role"]
            content = msg["content"]
            
            # Trim whitespace from content
            if isinstance(content, str):
                content = content.strip()
            
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                logger.warning(f"Unknown message role: {role}")
        
        try:
            logger.debug(f"Sending messages to LLM: {langchain_messages}")
            
            # Ensure we have at least one message
            if not langchain_messages:
                raise ValueError("No valid messages to send to the model")
            
            response = llm.invoke(langchain_messages)
            logger.debug(f"Received response: {response}")
            
            # Add the response to the messages
            state["messages"].append({"role": "assistant", "content": response.content})
            
        except Exception as e:
            logger.error(f"Error in chat_node: {str(e)}", exc_info=True)
            # Add an error message to the state
            state["error"] = str(e)
        
        return state
    
    # Create the graph
    builder = StateGraph(ChatState)
    
    # Add the nodes
    builder.add_node("chat", chat_node)
    
    # Set the entry point
    builder.set_entry_point("chat")
    
    # Set the exit point
    builder.add_edge("chat", END)
    
    # Compile the graph
    graph = builder.compile()
    
    return graph


# Create a singleton instance of the graph
chat_graph = create_chat_graph() 