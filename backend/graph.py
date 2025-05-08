from typing import Dict, List, Annotated, TypedDict, Sequence, Optional, Union, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import config
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
import os
from pathlib import Path
import json
import re
import requests
import time

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
    workflow_context: Annotated[Dict[str, Any], "Contextual data for the current workflow execution."]
    user_id: Annotated[Optional[str], "The ID of the current user"]
    conversation_id: Annotated[Optional[str], "The ID of the current conversation"]
    routing_analysis: Annotated[Optional[Dict[str, Any]], "Analysis from the router"]


# Define the intelligent router node at module level
def router_node(state: ChatState) -> ChatState:
    """Uses a lightweight LLM to analyze the message and determine routing."""
    logger.debug("Router node analyzing message")
    
    # Get the last user message
    last_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_message = msg["content"]
            break
            
    if not last_message:
        state["current_module"] = "chat"  # Default to chat module if no user message
        state["routing_analysis"] = {"decision": "chat", "reason": "No user message found"}
        return state
    
    # Create a system prompt for the router
    system_prompt = """
    You are a message router that determines the best module to handle a user's request. 
    Analyze the message and classify it into one of these categories:
    
    1. chat - General conversation, questions, or anything not fitting other categories.
    2. search - Requests to find current information from the web, search for recent facts, or retrieve up-to-date information.
       Examples: "What happened in the news today?", "Search for recent AI developments", "Find information about current technology trends"
    3. analyzer - Requests to analyze, process, summarize data or complex problem-solving.
    
    Output ONLY a JSON object with:
    - module: The chosen module name (chat, search, or analyzer)
    - reason: A brief explanation of why this module was chosen
    - complexity: Rate the complexity from 1-10 (1=very simple, 10=very complex)
    """
    
    # Initialize the GPT-3.5-Turbo model for routing
    router_llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.0,  # Keep deterministic
        max_tokens=150,   # Short response is sufficient
        api_key=config.OPENAI_API_KEY
    )
    
    try:
        # Send the message to the router model
        router_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message)
        ]
        
        response = router_llm.invoke(router_messages)
        
        # Parse the response - expect JSON format
        # Extract JSON from the response (it might be wrapped in markdown code blocks)
        content = response.content
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = content
            
        # Clean any remaining markdown or non-json text
        json_str = re.sub(r'[^{]*({.*})[^}]*', r'\1', json_str, flags=re.DOTALL)
        
        try:
            routing_data = json.loads(json_str)
            
            # Extract routing decision
            module = routing_data.get("module", "chat").lower()
            reason = routing_data.get("reason", "Default routing")
            complexity = int(routing_data.get("complexity", 5))
            
            # Validate module name
            if module not in ["chat", "search", "analyzer"]:
                module = "chat"  # Default to chat for unrecognized modules
            
            # Set the routing decision
            state["current_module"] = module
            state["routing_analysis"] = {
                "decision": module,
                "reason": reason,
                "complexity": complexity,
                "model_used": config.ROUTER_MODEL
            }
            
            logger.info(f"Router selected module: {module} (complexity: {complexity})")
            logger.debug(f"Routing reason: {reason}")
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse router response as JSON: {content}")
            state["current_module"] = "chat"  # Default fallback
            state["routing_analysis"] = {
                "decision": "chat", 
                "reason": "Error parsing router response",
                "raw_response": content
            }
    
    except Exception as e:
        logger.error(f"Error in router_node: {str(e)}")
        state["current_module"] = "chat"  # Default fallback
        state["routing_analysis"] = {"decision": "chat", "reason": f"Error: {str(e)}"}
        
    return state


def create_chat_graph():
    """Create a LangGraph graph for orchestrating the flow of the interaction."""
    
    # Define the initializer node
    def initializer_node(state: ChatState) -> ChatState:
        """Handles user, conversation, and initial state setup."""
        logger.debug(f"Initializer node received state: {state}")
        
        # Initialize workflow_context if it doesn't exist
        if "workflow_context" not in state or not state["workflow_context"]:
            state["workflow_context"] = {}
        
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
        
        return state
    
    # Define the search prompt optimizer node
    def search_prompt_optimizer_node(state: ChatState) -> ChatState:
        """Refines the user's query into an optimized search query using an LLM, considering conversation context."""
        logger.debug("Search Prompt Optimizer node refining query with context")
        
        # Gather recent conversation history for context (e.g., last 5 messages)
        # The messages in ChatState are dicts: {"role": ..., "content": ...}
        history_for_refinement = []
        raw_messages = state.get("messages", [])
        
        # Get the actual last user message to be refined
        last_user_message_content = None
        for msg in reversed(raw_messages):
            if msg.get("role") == "user":
                last_user_message_content = msg.get("content")
                break
        
        if not last_user_message_content:
            logger.warning("No user message found in search_prompt_optimizer_node. Cannot refine.")
            state["workflow_context"]["refined_search_query"] = ""
            return state

        # Construct context: last N messages (ensure not to take too many for the optimizer LLM)
        # We want the messages leading up to and including the last user message.
        num_context_messages = 5 # System + up to 4 history messages
        context_messages_for_llm = [] 
        
        # System prompt for the optimizer LLM
        system_prompt = """
        You are an expert at rephrasing user questions into effective search engine queries.
        Analyze the provided conversation history and the LATEST user question.
        Based on this context, transform the LATEST user question into a concise and keyword-focused search query
        that is likely to yield the best results from a web search engine like Perplexity.
        Focus on the core intent of the LATEST user question and use precise terminology, informed by the preceding conversation.
        Output ONLY the refined search query for the LATEST user question, with no other text or explanation.
        """
        context_messages_for_llm.append(SystemMessage(content=system_prompt))

        # Add recent history to context_messages_for_llm (HumanMessage, AIMessage)
        # Convert dict messages from state to LangChain message objects for the optimizer
        start_index = max(0, len(raw_messages) - (num_context_messages -1)) # -1 because system prompt is one
        for msg_dict in raw_messages[start_index:]:
            role = msg_dict.get("role")
            content = msg_dict.get("content", "").strip()
            if not content: # Skip empty messages
                continue
            if role == "user":
                context_messages_for_llm.append(HumanMessage(content=content))
            elif role == "assistant":
                context_messages_for_llm.append(AIMessage(content=content))
            # System messages from history are generally not passed to such an optimizer,
            # as we have a specific one for this node.

        # Ensure there's actually a human message to respond to, otherwise the LLM might be confused.
        if not any(isinstance(m, HumanMessage) for m in context_messages_for_llm):
            logger.warning("No human messages in context for search_prompt_optimizer. Using raw last user message.")
            state["workflow_context"]["refined_search_query"] = last_user_message_content
            return state
            
        optimizer_llm = ChatOpenAI(
            model=config.ROUTER_MODEL, 
            temperature=0.0,
            max_tokens=100,
            api_key=config.OPENAI_API_KEY
        )
        
        try:
            response = optimizer_llm.invoke(context_messages_for_llm)
            refined_query = response.content.strip()
            
            state["workflow_context"]["refined_search_query"] = refined_query
            logger.info(f"Refined search query with context: {refined_query}")
            
        except Exception as e:
            logger.error(f"Error in search_prompt_optimizer_node (with context): {str(e)}. Using original query as fallback.")
            state["workflow_context"]["refined_search_query"] = last_user_message_content
            
        return state

    # Define the analysis task refiner node
    def analysis_task_refiner_node(state: ChatState) -> ChatState:
        """Refines the user's request into a detailed task for the analysis engine, considering conversation context."""
        logger.debug("Analysis Task Refiner node refining task with context")

        raw_messages = state.get("messages", [])
        last_user_message_content = None
        for msg in reversed(raw_messages):
            if msg.get("role") == "user":
                last_user_message_content = msg.get("content")
                break
        
        if not last_user_message_content:
            logger.warning("No user message found in analysis_task_refiner_node. Cannot refine.")
            state["workflow_context"]["refined_analysis_task"] = ""
            return state

        num_context_messages = 5 # System + up to 4 history messages
        context_messages_for_llm = []

        system_prompt = """
        You are an expert at breaking down user requests into clear, structured analytical tasks, considering the full conversation context.
        Analyze the provided conversation history and the LATEST user request.
        Based on this context, transform the LATEST user request into a detailed task description suitable for an advanced analysis engine.
        Specify the information to be analyzed, the type of analysis required, and the desired output format if implied.
        Ensure the refined task for the LATEST user question is actionable and self-contained based on the conversation.
        Output ONLY the refined task description, with no other text or explanation.
        """
        context_messages_for_llm.append(SystemMessage(content=system_prompt))

        start_index = max(0, len(raw_messages) - (num_context_messages - 1))
        for msg_dict in raw_messages[start_index:]:
            role = msg_dict.get("role")
            content = msg_dict.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                context_messages_for_llm.append(HumanMessage(content=content))
            elif role == "assistant":
                context_messages_for_llm.append(AIMessage(content=content))

        if not any(isinstance(m, HumanMessage) for m in context_messages_for_llm):
            logger.warning("No human messages in context for analysis_task_refiner. Using raw last user message.")
            state["workflow_context"]["refined_analysis_task"] = last_user_message_content
            return state

        optimizer_llm = ChatOpenAI(
            model=config.ROUTER_MODEL, 
            temperature=0.0,
            max_tokens=300, 
            api_key=config.OPENAI_API_KEY
        )

        try:
            response = optimizer_llm.invoke(context_messages_for_llm)
            refined_task = response.content.strip()

            state["workflow_context"]["refined_analysis_task"] = refined_task
            logger.info(f"Refined analysis task with context: {refined_task}")

        except Exception as e:
            logger.error(f"Error in analysis_task_refiner_node (with context): {str(e)}. Using original request as fallback.")
            state["workflow_context"]["refined_analysis_task"] = last_user_message_content
            
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
            if not langchain_messages or len(langchain_messages) <=1: # Ensure more than just system message
                # If only system message, it means no user/assistant messages were valid to process
                # This could happen if user sends empty message or only system messages in input state.
                # Adding a specific user-facing message if appropriate, or just log and return.
                logger.warning("No valid user/assistant messages to send to the model in chat_node.")
                # Decide on a response for this case, e.g., a polite "I need more information"
                # For now, just pass through, which might result in an empty AI response if LLM is called with only system.
                # Or better, create a default response.
                if not any(m.type == 'human' for m in langchain_messages):
                     state["messages"].append({"role": "assistant", "content": "I received an empty message. How can I help you?", "metadata": {"module": "chat"}})
                     state["module_results"]["chat"] = "I received an empty message. How can I help you?"
                     return state

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
            state["error"] = str(e) # Storing general error
            # Also append a user-facing error message
            state["messages"].append({
                "role": "assistant", 
                "content": f"I encountered an error processing your request: {str(e)}", 
                "metadata": {"module":"chat", "error": True}
            })
            state["module_results"]["chat"] = {"success": False, "error": str(e)}

        return state
        
    # Define the search module node (using Perplexity API for real web search)
    def search_node(state: ChatState) -> ChatState:
        """Search module that handles search-related queries using Perplexity API, using a refined query if available."""
        logger.debug(f"Search node received state: {state}")
        
        # Use refined search query from workflow_context if available, otherwise fallback to last user message
        query_to_search = state.get("workflow_context", {}).get("refined_search_query")
        
        if not query_to_search:
            logger.warning("No refined_search_query found in workflow_context. Falling back to last user message for search.")
            last_user_message_content = None
            for msg in reversed(state["messages"]):
                if msg["role"] == "user":
                    last_user_message_content = msg["content"]
                    break
            query_to_search = last_user_message_content

        if not query_to_search: # If still no query (e.g. no user message at all)
            error_message = "No query found to search for (neither refined nor original)."
            logger.error(error_message)
            state["messages"].append({
                "role": "assistant", 
                "content": error_message,
                "metadata": {"module": "search", "error": True}
            })
            state["module_results"]["search"] = {"success": False, "error": error_message}
            return state
        
        # Check if Perplexity API key is available
        if not config.PERPLEXITY_API_KEY:
            error_message = "Perplexity API key not configured. Please set the PERPLEXITY_API_KEY environment variable."
            logger.error(error_message)
            state["messages"].append({
                "role": "assistant", 
                "content": error_message,
                "metadata": {"module": "search", "error": True}
            })
            state["module_results"]["search"] = {"success": False, "error": error_message}
            return state
        
        try:
            # Prepare the search query
            headers = {
                "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Format the search prompt FOR PERPLEXITY (system prompt here is for Perplexity's behavior)
            # The query_to_search is the user's intent, possibly refined.
            perplexity_messages = [
                {"role": "system", "content": "You are a helpful and accurate web search assistant. Provide comprehensive answers based on web search results."},
                {"role": "user", "content": query_to_search} # This is the actual search query
            ]
            
            # Prepare the API request
            payload = {
                "model": config.PERPLEXITY_MODEL,
                "messages": perplexity_messages,
                "options": { # Perplexity specific options if any, e.g. search depth, focus.
                    "stream": False 
                }
            }
            
            logger.debug(f"Sending search request to Perplexity API with query: {query_to_search}")
            
            # Make the API request to Perplexity
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                response_data = response.json()
                search_result = response_data["choices"][0]["message"]["content"]
                
                logger.debug(f"Received search response from Perplexity: {search_result[:100]}...")
                
                # Create the response message
                assistant_message = {
                    "role": "assistant", 
                    "content": search_result,
                    "metadata": {
                        "module": "search",
                        "model": config.PERPLEXITY_MODEL,
                        "original_query": query_to_search # Storing the query that was actually searched
                    }
                }
                
                # Add the response to the messages in state
                state["messages"].append(assistant_message)
                
                # Store the result in module_results
                state["module_results"]["search"] = {
                    "success": True,
                    "result": search_result,
                    "query_used": query_to_search
                }
                
                # Save the response to conversation history
                user_id = state.get("user_id")
                conversation_id = state.get("conversation_id")
                if user_id and conversation_id:
                    conversation_manager.add_message(
                        user_id,
                        conversation_id,
                        "assistant",
                        search_result,
                        {
                            "module": "search",
                            "model": config.PERPLEXITY_MODEL,
                            "query_used": query_to_search
                        }
                    )
            else:
                # Handle API error
                error_message = f"Perplexity API request failed with status code {response.status_code}: {response.text}"
                logger.error(error_message)
                
                # Format a user-friendly error message
                user_error = f"I couldn't complete the search due to an API error. Status code: {response.status_code}"
                
                state["messages"].append({
                    "role": "assistant", 
                    "content": user_error,
                    "metadata": {"module": "search", "error": True}
                })
                
                state["module_results"]["search"] = {
                    "success": False, 
                    "error": error_message,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            # Handle any exceptions
            error_message = f"Error in search_node: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            # Add an error message to the state
            state["messages"].append({
                "role": "assistant", 
                "content": f"I encountered an error while trying to search: {str(e)}",
                "metadata": {"module": "search", "error": True}
            })
            
            state["module_results"]["search"] = {"success": False, "error": error_message}
        
        return state
        
    # Define the analyzer module node (placeholder for demonstration)
    def analyzer_node(state: ChatState) -> ChatState:
        """Analyzer module that processes data-related queries, using a refined task if available."""
        logger.debug(f"Analyzer node received state: {state}")
        
        refined_task = state.get("workflow_context", {}).get("refined_analysis_task")
        original_user_query = None
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                original_user_query = msg["content"]
                break
        
        task_to_analyze = refined_task if refined_task else original_user_query

        if not task_to_analyze:
            error_message = "No task found for analyzer (neither refined nor original)."
            logger.error(error_message)
            state["messages"].append({
                "role": "assistant", 
                "content": error_message,
                "metadata": {"module": "analyzer", "error": True}
            })
            state["module_results"]["analyzer"] = {"success": False, "error": error_message}
            return state

        logger.info(f"Analyzer node would process task: {task_to_analyze[:200]}...")
        # In a real implementation, this would use 'task_to_analyze' to perform analysis
        
        analysis_response = f"I have analyzed the task related to: '{task_to_analyze}'. [This is a simulated analysis response based on the (refined) task description]"
        
        # Create the response message
        assistant_message = {
            "role": "assistant", 
            "content": analysis_response,
            "metadata": {"module": "analyzer", "task_processed": task_to_analyze}
        }
        
        # Add the response to the messages in state
        state["messages"].append(assistant_message)
        
        # Store the result in module_results
        state["module_results"]["analyzer"] = {"success": True, "result": analysis_response, "task_processed": task_to_analyze}
        
        # Save the response to conversation history
        user_id = state.get("user_id")
        conversation_id = state.get("conversation_id")
        if user_id and conversation_id:
            conversation_manager.add_message(
                user_id,
                conversation_id,
                "assistant",
                analysis_response,
                {"module": "analyzer", "task_processed": task_to_analyze}
            )
        
        return state
    
    # Define the router function for conditional branching
    def router(state: ChatState) -> str:
        """Route to the appropriate module based on the current_module state."""
        # This router now potentially routes to optimizer nodes first
        # The optimizer nodes themselves don't change current_module, so the next step
        # (search or analyzer) is determined by the original router decision.
        # The conditional edges will handle this.
        logger.debug(f"Router function routing to: {state['current_module']}")
        return state["current_module"]
    
    # Create the graph
    builder = StateGraph(ChatState)
    
    # Add the nodes
    builder.add_node("initializer", initializer_node)
    builder.add_node("router", router_node)
    builder.add_node("search_prompt_optimizer", search_prompt_optimizer_node)
    builder.add_node("analysis_task_refiner", analysis_task_refiner_node)
    builder.add_node("chat", chat_node)
    builder.add_node("search", search_node)
    builder.add_node("analyzer", analyzer_node)
    
    # Set the entry point
    builder.set_entry_point("initializer")
    
    # Define the flow: initializer -> router
    builder.add_edge("initializer", "router")
    
    # Conditional edges from router:
    # If "search", go to optimizer, then to search_node
    # If "analyzer", go to refiner, then to analyzer_node
    # If "chat", go directly to chat_node
    builder.add_conditional_edges(
        "router",
        router, # The router function determines the value of state["current_module"]
        {
            "chat": "chat",
            "search": "search_prompt_optimizer", # Route to optimizer first
            "analyzer": "analysis_task_refiner"  # Route to refiner first
        }
    )

    # Edges from optimizer/refiner to their respective processing nodes
    builder.add_edge("search_prompt_optimizer", "search")
    builder.add_edge("analysis_task_refiner", "analyzer")
    
    # Set all final processing nodes to end
    builder.add_edge("chat", END)
    builder.add_edge("search", END)
    builder.add_edge("analyzer", END)
    
    # Compile the graph
    graph = builder.compile()
    
    return graph


# Create a singleton instance of the graph
chat_graph = create_chat_graph()

def visualize_graph(output_file="graph.png"):
    """
    Generate a PNG visualization of the LangGraph using built-in functionality.
    
    Args:
        output_file: Path where to save the PNG file.
    
    Returns:
        bool: True if visualization was successful, False otherwise.
    """
    try:
        import os
        import subprocess
        
        # First, check if graphviz is installed
        try:
            subprocess.run(["dot", "-V"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: Graphviz not found. Install it with: sudo apt-get install graphviz")
            return False
            
        # Create a DOT file from the graph
        dot_file = output_file.replace('.png', '.dot')
        
        print(f"Generating visualization of LangGraph...")
        
        # Try using the built-in visualization methods
        try:
            # Method 1: Try using draw_png if available (most direct method)
            png_data = chat_graph.get_graph().draw_png()
            with open(output_file, 'wb') as f:
                f.write(png_data)
            print(f"Visualization saved to {output_file}")
            return True
        except (AttributeError, ImportError) as e:
            print(f"draw_png method not available: {str(e)}")
            
            # Method 2: Fall back to DOT format
            try:
                dot_data = chat_graph.get_graph().draw_graphviz()
                with open(dot_file, 'w') as f:
                    f.write(dot_data)
                # Use graphviz to convert to PNG
                subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
                print(f"Visualization saved to {output_file}")
                # Clean up the DOT file
                os.remove(dot_file)
                return True
            except (AttributeError, ImportError) as e:
                print(f"draw_graphviz method not available: {str(e)}")
                
                # Method 3: If all else fails, use any available method
                if hasattr(chat_graph, 'get_graph'):
                    graph_obj = chat_graph.get_graph()
                    for method_name in ['draw_png', 'draw_graphviz', 'to_dot']:
                        if hasattr(graph_obj, method_name):
                            try:
                                method = getattr(graph_obj, method_name)
                                result = method()
                                if method_name == 'draw_png':
                                    with open(output_file, 'wb') as f:
                                        f.write(result)
                                    print(f"Visualization saved to {output_file} using {method_name}")
                                    return True
                                elif method_name in ['draw_graphviz', 'to_dot']:
                                    with open(dot_file, 'w') as f:
                                        f.write(result)
                                    subprocess.run(["dot", "-Tpng", dot_file, "-o", output_file], check=True)
                                    print(f"Visualization saved to {output_file} using {method_name}")
                                    os.remove(dot_file)
                                    return True
                            except Exception as e:
                                print(f"Method {method_name} failed: {str(e)}")
                                continue
                    else:
                        print("Could not generate visualization: No suitable method found in graph object")
                else:
                    print("Could not generate visualization: Graph object not accessible")
    except Exception as e:
        print(f"Error generating visualization: {str(e)}")
    
    return False

# Automatically generate visualization whenever this module is run directly
if __name__ == "__main__":
    visualize_graph() 