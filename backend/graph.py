from typing import Dict, List, Annotated, TypedDict, Sequence, Optional, Union, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import config
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os
from pathlib import Path
import json
import re
import requests
import time
import inspect

# Use the centralized logging configuration
from logging_config import get_logger
logger = get_logger(__name__)

# Import our storage components
from storage.storage_manager import StorageManager
from storage.user_manager import UserManager
from storage.conversation_manager import ConversationManager

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


def get_current_datetime_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())


# Define the intelligent router node at module level
def router_node(state: ChatState) -> ChatState:
    """Uses a lightweight LLM to analyze the user's message and determine routing."""
    logger.info("🔀 Router: Analyzing message to determine processing path")
    
    # Get the last user message
    last_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_message = msg["content"]
            break
            
    if not last_message:
        state["current_module"] = "chat"  # Default to chat module if no user message found
        state["routing_analysis"] = {"decision": "chat", "reason": "No user message found"}
        logger.info("🔀 Router: No user message found, defaulting to chat module")
        return state
    
    # Log the user message for traceability (truncate if too long)
    display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
    logger.info(f"🔀 Router: Processing user message: \"{display_msg}\"")
    
    # Create a system prompt for the router
    system_prompt = f"""
    Current date and time: {get_current_datetime_str()}
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
        content = response.content
        
        # Extract JSON
        json_str = content
        if '```json' in content:
            # Extract content from code blocks if present
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
        
        # Parse the routing decision
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
        
        logger.info(f"🔀 Router: Selected module '{module}' (complexity: {complexity}) for message: \"{display_msg}\"")
        logger.debug(f"Routing reason: {reason}")
        
    except Exception as e:
        # Single exception handling for all error cases
        logger.error(f"Error in router_node: {str(e)}")
        state["current_module"] = "chat"  # Default fallback
        state["routing_analysis"] = {"decision": "chat", "reason": f"Error: {str(e)}"}
        logger.info("🔀 Router: Exception occurred, defaulting to chat module")
        
    return state


def create_chat_graph():
    """Create a LangGraph graph for orchestrating the flow of the interaction."""
    
    # Define the initializer node
    def initializer_node(state: ChatState) -> ChatState:
        """Handles user, conversation, and initial state setup."""
        logger.info("🔄 Initializer: Setting up user and conversation state")
        
        # Initialize state objects if they don't exist
        state["workflow_context"] = state.get("workflow_context", {})
        state["module_results"] = state.get("module_results", {})
        state["personality"] = state.get("personality", {"style": "helpful", "tone": "friendly"})
        
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
                
        # Handle conversation management
        conversation_id = state.get("conversation_id")
        if not conversation_id or not conversation_manager.get_conversation(user_id, conversation_id):
            # Create a new conversation
            conversation_id = conversation_manager.create_conversation(user_id, {
                "name": f"Conversation {conversation_manager.list_conversations(user_id).__len__() + 1}",
                "model": state.get("model", config.DEFAULT_MODEL)
            })
            state["conversation_id"] = conversation_id
            logger.info(f"Created new conversation: {conversation_id}")
        
        # Store the input messages in the conversation
        conversation_manager.add_messages(user_id, conversation_id, state["messages"])
        
        return state
    
    # Define the search prompt optimizer node
    def search_prompt_optimizer_node(state: ChatState) -> ChatState:
        """Refines the user's query into an optimized search query using an LLM, considering conversation context."""
        logger.info("🔍 Search Optimizer: Refining user query for search")
        current_time_str = get_current_datetime_str()
        
        # Gather recent conversation history for context (e.g., last 5 messages)
        # history_for_refinement = []
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

        # Log the user message being refined
        display_msg = last_user_message_content[:75] + "..." if len(last_user_message_content) > 75 else last_user_message_content
        logger.info(f"🔍 Search Optimizer: Refining query: \"{display_msg}\"")
        
        # Construct context: messages leading up to and including the last user message.
        num_context_messages = 5 # System + up to 4 history messages
        context_messages_for_llm = [] 
        
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

        # Instruction prompt for the optimizer LLM
        instruction_prompt = f"""
        Current date and time: {current_time_str}
        You are an expert at rephrasing user questions into effective search engine queries.
        Analyze the provided conversation history and the LATEST user question.
        Based on this context, transform the LATEST user question into a concise and keyword-focused search query
        that is likely to yield the best results from a web search engine like Perplexity.
        Focus on the core intent of the LATEST user question and use precise terminology, informed by the preceding conversation.
        Output ONLY the refined search query for the LATEST user question, with no other text or explanation.
        """
        context_messages_for_llm.append(HumanMessage(content=instruction_prompt))

        optimizer_llm = ChatOpenAI(
            model=config.ROUTER_MODEL, 
            temperature=0.0,
            max_tokens=100,
            api_key=config.OPENAI_API_KEY
        )
        
        try:
            response = optimizer_llm.invoke(context_messages_for_llm)
            refined_query = response.content.strip()
            
            # Log the refined query
            display_refined = refined_query[:75] + "..." if len(refined_query) > 75 else refined_query
            logger.info(f"🔍 Search Optimizer: Produced refined query: \"{display_refined}\"")
            
            state["workflow_context"]["refined_search_query"] = refined_query
            logger.info(f"Refined search query with context: {refined_query}")
            
        except Exception as e:
            logger.error(f"Error in search_prompt_optimizer_node (with context): {str(e)}. Using original query as fallback.")
            state["workflow_context"]["refined_search_query"] = last_user_message_content
            
        return state

    # Define the analysis task refiner node
    def analysis_task_refiner_node(state: ChatState) -> ChatState:
        """Refines the user's request into a detailed task for the analysis engine, considering conversation context."""
        logger.info("🧩 Analysis Refiner: Refining user request into analysis task")
        logger.debug("Analysis Task Refiner node refining task with context")
        current_time_str = get_current_datetime_str()
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
            
        # Log the user message being refined
        display_msg = last_user_message_content[:75] + "..." if len(last_user_message_content) > 75 else last_user_message_content
        logger.info(f"🧩 Analysis Refiner: Refining task: \"{display_msg}\"")

        num_context_messages = 5 # System + up to 4 history messages
        context_messages_for_llm = []

        system_prompt = f"""
        Current date and time: {current_time_str}
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
            
            # Log the refined task
            display_refined = refined_task[:75] + "..." if len(refined_task) > 75 else refined_task
            logger.info(f"🧩 Analysis Refiner: Produced refined task: \"{display_refined}\"")

            state["workflow_context"]["refined_analysis_task"] = refined_task
            logger.info(f"Refined analysis task with context: {refined_task}")

        except Exception as e:
            logger.error(f"Error in analysis_task_refiner_node (with context): {str(e)}. Using original request as fallback.")
            state["workflow_context"]["refined_analysis_task"] = last_user_message_content
            
        return state

    # Define the search module node (using Perplexity API for real web search)
    def search_node(state: ChatState) -> ChatState:
        """Performs web search for user queries requiring up-to-date information."""
        logger.info("🔍 Search: Preparing to search for information")
        logger.debug(f"Search node received state: {state}")
        
        # Use the refined query if available, otherwise get the last user message
        refined_query = state.get("workflow_context", {}).get("refined_search_query")
        original_user_query = None
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                original_user_query = msg["content"]
                break
        
        query_to_search = refined_query if refined_query else original_user_query

        if not query_to_search:
            state["module_results"]["search"] = {"success": False, "error": "No query found for search (neither refined nor original)."}
            return state
            
        # Log the search query
        display_msg = query_to_search[:75] + "..." if len(query_to_search) > 75 else query_to_search
        logger.info(f"🔍 Search: Searching for: \"{display_msg}\"")
        
        # Check if Perplexity API key is available
        if not config.PERPLEXITY_API_KEY:
            error_message = "Perplexity API key not configured. Please set the PERPLEXITY_API_KEY environment variable."
            logger.error(error_message)
            state["module_results"]["search"] = {"success": False, "error": error_message}
            return state
        
        try:
            # Prepare the search query
            headers = {
                "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Format the search prompt 
            perplexity_system_prompt = f"""Current date and time: {get_current_datetime_str()}. 
You are a helpful and accurate web search assistant. 
Provide comprehensive answers based on web search results."""
            perplexity_messages = [
                {"role": "system", "content": perplexity_system_prompt},
                {"role": "user", "content": query_to_search}
            ]
            
            # Prepare the API request
            payload = {
                "model": config.PERPLEXITY_MODEL,
                "messages": perplexity_messages,
                "options": {"stream": False}
            }
            
            logger.debug(f"Sending search request to Perplexity API with query: {query_to_search}")
            
            # Make the API request to Perplexity
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )
            
            # Process the response
            if response.status_code == 200:
                response_data = response.json()
                search_result = response_data["choices"][0]["message"]["content"]
                
                # Log the search result
                display_result = search_result[:75] + "..." if len(search_result) > 75 else search_result
                logger.info(f"🔍 Search: Result received: \"{display_result}\"")
                
                state["module_results"]["search"] = {
                    "success": True,
                    "result": search_result,
                    "query_used": query_to_search
                }
            else:
                # Handle API error
                error_message = f"Perplexity API request failed with status code {response.status_code}: {response.text}"
                logger.error(error_message)
                state["module_results"]["search"] = {
                    "success": False, 
                    "error": error_message,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            # Handle any exceptions
            error_message = f"Error in search_node: {str(e)}"
            logger.error(error_message, exc_info=True)
            state["module_results"]["search"] = {"success": False, "error": error_message}
        
        return state
        
    # Define the analyzer module node (placeholder for demonstration)
    def analyzer_node(state: ChatState) -> ChatState:
        """Analyzer module that processes data-related queries."""
        logger.info("🧩 Analyzer: Processing analysis request")
        
        # Get analysis task (either refined or original)
        refined_task = state.get("workflow_context", {}).get("refined_analysis_task")
        original_user_query = next((msg["content"] for msg in reversed(state["messages"]) 
                                  if msg["role"] == "user"), None)
        
        task_to_analyze = refined_task or original_user_query

        if not task_to_analyze:
            state["module_results"]["analyzer"] = {"success": False, "error": "No task found for analyzer."}
            return state
            
        # Log the task to analyze
        display_task = task_to_analyze[:75] + "..." if len(task_to_analyze) > 75 else task_to_analyze
        logger.info(f"🧩 Analyzer: Analyzing: \"{display_task}\"")

        logger.info(f"🧩 Analyzer node processing task (simulated): {task_to_analyze[:200]}...")
        
        analysis_response = f"Based on the task related to '{task_to_analyze}', I have performed a simulated analysis. [This is a simulated analysis response based on the (refined) task description]"
        
        # Log the analysis result
        display_result = analysis_response[:75] + "..." if len(analysis_response) > 75 else analysis_response
        logger.info(f"🧩 Analyzer: Analysis result: \"{display_result}\"")

        # Store the result
        state["module_results"]["analyzer"] = {
            "success": True, 
            "result": analysis_response, 
            "task_processed": task_to_analyze
        }
        
        return state
    
    # Define the router function for conditional branching
    def router(state: ChatState) -> str:
        """Route to the appropriate module based on the current_module state."""
        logger.info(f"⚡ Flow: Routing to '{state['current_module']}' module")
        return state["current_module"]
    
    # Define the Integrator node
    def integrator_node(state: ChatState) -> ChatState:
        """Core thinking component that integrates all available context and generates a response."""
        logger.info("🧠 Integrator: Processing all contextual information")
        current_time_str = get_current_datetime_str()
        model = state.get("model", config.DEFAULT_MODEL)
        temperature = state.get("temperature", 0.7)
        max_tokens = state.get("max_tokens", 1000)
        
        # Get last user message for logging
        last_message = None
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                last_message = msg["content"]
                break
                
        if last_message:
            display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
            logger.info(f"🧠 Integrator: Processing query: \"{display_msg}\"")
            
        # Create system message based on personality if available
        system_message_content = f"Current date and time: {current_time_str}."
        
        # Include the agent's role as a central reasoning component
        system_message_content += "\nYou are the central reasoning component of an AI assistant system. Your task is to integrate all available information and generate a coherent, thoughtful response."
        
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
        
        # Process the conversation history
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
        
        # Add search/analysis results after the last message, if available
        search_results = state.get("module_results", {}).get("search", {})
        if search_results.get("success", False):
            search_result_text = search_results.get("result", None)
            if search_result_text:
                # Add search results directly to the prompt
                search_msg = f"""
IMPORTANT FACTUAL INFORMATION FROM SEARCH:
==================================================
{search_result_text}
==================================================
The above information is from a current web search. Please prioritize this information in your response.
"""
                langchain_messages.append(AIMessage(content=search_msg))
                logger.info("🧠 Integrator: Added search results to prompt")
            
        analysis_results = state.get("module_results", {}).get("analyzer", {})
        if analysis_results.get("success", False):
            analysis_result_text = analysis_results.get("result", None)
            if analysis_result_text:
                # Add analysis results directly to the prompt
                analysis_msg = f"""
IMPORTANT ANALYTICAL INSIGHTS:
==================================================
{analysis_result_text}
==================================================
The above analytical insights are relevant to the user's query. Incorporate these insights into your response.
"""
                langchain_messages.append(AIMessage(content=analysis_msg))
                logger.info("🧠 Integrator: Added analytical insights to prompt")
                    
        # Log the full prompt being sent to the LLM for debugging
        prompt_log = "\n---\n".join([
            f"ROLE: {msg.type}\nCONTENT: {msg.content}"
            for msg in langchain_messages
        ])
        logger.info(f"🧠 Integrator: Full prompt being sent to LLM:\n{prompt_log}")
        
        try:
            logger.debug(f"Sending {len(langchain_messages)} messages to Integrator")
            # Create a chat model with specified parameters
            response = llm.invoke(langchain_messages)
            logger.debug(f"Received response from Integrator: {response}")
            
            # Log the response for traceability
            display_response = response.content[:75] + "..." if len(response.content) > 75 else response.content
            logger.info(f"🧠 Integrator: Generated response: \"{display_response}\"")
            
            # Store the Integrator's response in the workflow context for the renderer
            state["workflow_context"]["integrator_response"] = response.content
            
            # Also store in module_results for consistency
            state["module_results"]["integrator"] = response.content
            
        except Exception as e:
            logger.error(f"Error in integrator_node: {str(e)}", exc_info=True)
            # Store the error in workflow context
            state["workflow_context"]["integrator_error"] = str(e)
            state["workflow_context"]["integrator_response"] = f"I encountered an error processing your request: {str(e)}"
        
        return state

    # Define the Response Renderer node
    def response_renderer_node(state: ChatState) -> ChatState:
        """Post-processes the LLM output to enforce style, insert follow-up suggestions, and apply user persona settings."""
        logger.info("✨ Renderer: Post-processing final response")
        logger.debug("Response Renderer node processing output")
        current_time_str = get_current_datetime_str()
        
        # Get the raw response from the Integrator
        raw_response = state.get("workflow_context", {}).get("integrator_response", "")
        
        if not raw_response:
            error = state.get("workflow_context", {}).get("integrator_error", "Unknown error")
            logger.error(f"No response from Integrator to render. Error: {error}")
            state["messages"].append({
                "role": "assistant", 
                "content": f"I apologize, but I encountered an error generating a response: {error}",
                "metadata": {"error": True}
            })
            return state
        
        # Log the raw response
        display_raw = raw_response[:75] + "..." if len(raw_response) > 75 else raw_response
        logger.info(f"✨ Renderer: Processing raw response: \"{display_raw}\"")
        
        # Get personality settings to apply to the response
        personality = state.get("personality", {})
        style = personality.get("style", "helpful")
        tone = personality.get("tone", "friendly")
        
        # Get the active module that was used to handle the query
        module_used = state.get("current_module", "chat")
        
        # Get recent conversation history for context
        raw_messages = state.get("messages", [])
        
        # Initialize LLM for response rendering
        renderer_llm = ChatOpenAI(
            model=config.DEFAULT_MODEL,
            temperature=0.3,  # Low temperature for more consistent formatting
            max_tokens=1500,  # Allow for extra tokens for formatting and follow-ups 
            api_key=config.OPENAI_API_KEY
        )
        
        # Create a system prompt for the renderer
        system_prompt = f"""
        Current date and time: {current_time_str}
        You are the response formatting component of an AI assistant system. 
        
        Your task is to:
        1. Format and style the provided raw response according to the user's preferences.
        2. Maintain the response's original information, insights and core content.
        3. Adapt the response to a {style} style with a {tone} tone.
        4. ONLY IF the conversation context and response content warrant it, add 1-2 relevant follow-up questions.
           * Follow-up questions should ONLY be added if they naturally extend from the response content.
           * Do NOT add generic follow-up questions like "Is there anything else you'd like to know?".
           * Do NOT add follow-up questions for simple exchanges, greetings, or when the response is fully comprehensive.
        5. Include source citations or attributions from the raw response if present.
        
        The raw response was generated by the {module_used} module of the assistant.
        Preserve all factual information exactly as presented in the raw response.
        """
        
        # Prepare the messages for the renderer LLM
        renderer_messages = [
            SystemMessage(content=system_prompt),
        ]
        
        # Add the last few messages for context (if any)
        context_size = 3  # Number of recent messages to include for context
        if len(raw_messages) > 0:
            context_start = max(0, len(raw_messages) - context_size)
            for msg in raw_messages[context_start:]:
                role = msg.get("role")
                content = msg.get("content", "").strip()
                if role == "user":
                    renderer_messages.append(HumanMessage(content=f"[User Message]: {content}"))
                elif role == "assistant":
                    renderer_messages.append(AIMessage(content=f"[Assistant Response]: {content}"))
        
        # Add specific message for the raw response to be formatted
        renderer_messages.append(HumanMessage(content=f"""
        Below is the raw response from the {module_used} module to be formatted according to the specified guidelines.
        
        [Raw Response]:
        {raw_response}
        
        Please format this response in a {style} style with a {tone} tone, and add relevant follow-up questions ONLY if appropriate.
        """))
        
        try:
            # Process the response with the renderer LLM
            renderer_response = renderer_llm.invoke(renderer_messages)
            formatted_response = renderer_response.content.strip()
            
            # Log the formatted response
            display_formatted = formatted_response[:75] + "..." if len(formatted_response) > 75 else formatted_response
            logger.info(f"✨ Renderer: Produced formatted response: \"{display_formatted}\"")
            
            logger.debug(f"Renderer processed response. Original length: {len(raw_response)}, Formatted length: {len(formatted_response)}")
            
            # Create the final assistant message
            assistant_message = {
                "role": "assistant", 
                "content": formatted_response,
                "metadata": {
                    "rendered": True,
                    "style": style,
                    "tone": tone,
                    "module_used": module_used
                }
            }
            
            # Add the rendered response to the messages in state
            state["messages"].append(assistant_message)
            
            # Save the response to conversation history
            user_id = state.get("user_id")
            conversation_id = state.get("conversation_id")
            if user_id and conversation_id:
                conversation_manager.add_message(
                    user_id,
                    conversation_id,
                    "assistant",
                    formatted_response,
                    {
                        "rendered": True,
                        "style": style,
                        "tone": tone,
                        "module_used": module_used
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in response_renderer_node: {str(e)}", exc_info=True)
            # If rendering fails, use the raw response as a fallback
            state["messages"].append({
                "role": "assistant", 
                "content": raw_response,
                "metadata": {
                    "rendered": False,
                    "render_error": str(e),
                    "module_used": module_used
                }
            })
            
            # Save the raw response to conversation history as fallback
            user_id = state.get("user_id")
            conversation_id = state.get("conversation_id")
            if user_id and conversation_id:
                conversation_manager.add_message(
                    user_id,
                    conversation_id,
                    "assistant",
                    raw_response,
                    {
                        "rendered": False,
                        "render_error": str(e),
                        "module_used": module_used
                    }
                )
        
        return state

    # Build and return the graph
    builder = StateGraph(ChatState)
    
    # Add all nodes
    builder.add_node("initializer", initializer_node)
    builder.add_node("router", router_node)
    builder.add_node("search_prompt_optimizer", search_prompt_optimizer_node)
    builder.add_node("analysis_task_refiner", analysis_task_refiner_node)
    builder.add_node("search", search_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("integrator", integrator_node)
    builder.add_node("response_renderer", response_renderer_node)
    
    # Define the workflow
    builder.set_entry_point("initializer")
    builder.add_edge("initializer", "router")
    
    # From router, conditionally go to different modules
    builder.add_conditional_edges(
        "router",
        router,
        {
            "search": "search_prompt_optimizer",
            "analyzer": "analysis_task_refiner",
            "chat": "integrator" 
        }
    )
    
    # Connect the search optimization to search
    builder.add_edge("search_prompt_optimizer", "search")
    builder.add_edge("search", "integrator")
    
    # Connect the analysis refiner to analyzer
    builder.add_edge("analysis_task_refiner", "analyzer")
    builder.add_edge("analyzer", "integrator")
    
    # Connect the integrator to the response renderer
    builder.add_edge("integrator", "response_renderer")
    
    # End the graph after rendering the response
    builder.add_edge("response_renderer", END)
    
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