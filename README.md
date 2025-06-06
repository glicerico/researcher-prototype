# AI Chatbot Web App

A simple chatbot web application with a React frontend and a flexible backend using LangGraph and an LLM model.

## Features

- Modern React-based user interface
- Clean, responsive web interface
- Backend built with FastAPI and LangGraph
- Uses OpenAI's o4-mini model by default
- Component-based architecture for easy extensibility
- Debug mode for troubleshooting
- Multi-user support with individual chat histories
- Customizable AI personality (style and tone)
- Persistent data storage for conversations and user settings

## User Guide

### User Management

The application supports multiple users:
- **Create new users** via the user dropdown menu
- **Switch between users** easily with the dropdown
- Each user has their own conversation history and settings

### Personality Customization

Customize the AI assistant's behavior:
- **Communication Style**: Choose between helpful, concise, expert, creative, or friendly
- **Tone**: Set the tone to friendly, professional, casual, enthusiastic, or direct
- **Quick Presets**: Apply pre-defined combinations with a single click

### Conversation Features

- Real-time responses from the AI assistant
- Conversations are automatically saved
- User interface displays typing indicators
- System messages adapt based on personality settings

### Data Persistence

All user data and conversations are stored locally and persist between sessions, including:
- User profiles and display names
- Personality settings
- Conversation history

Data is stored in the `backend/storage_data` directory in JSON format. If you want to back up your data, you can copy this directory. Note that this directory is not tracked by version control.

### Zep Memory (Optional)

Enables advanced memory with knowledge graphs that automatically extract and store facts from conversations. 

When enabled, ZEP provides conversational context to key nodes in the processing pipeline:
- **Router**: Better routing decisions based on conversation history
- **Search Optimizer**: More contextually relevant search queries  
- **Analysis Refiner**: Enhanced analysis tasks informed by prior discussions
- **Integrator**: Maintains conversational continuity and references previous topics

To enable, add `ZEP_API_KEY` and set `ZEP_ENABLED=true` in your `.env` file. 
Get an API key at [getzep.com](https://www.getzep.com/).
The system gracefully degrades when ZEP is unavailable, ensuring uninterrupted operation.

## Autonomous Research Engine

The application includes a powerful autonomous research engine that automatically conducts background research on topics you're interested in. This system operates independently of your chat sessions, continuously finding new information and insights.

### How It Works

1. **Topic Discovery**: As you chat, the system identifies research-worthy topics from your conversations
2. **Topic Subscription**: You can mark topics as "active research" to enable autonomous research
3. **Background Research**: Every 2 hours (configurable), the system automatically researches your subscribed topics
4. **Quality Assessment**: Research findings are evaluated for relevance, recency, depth, credibility, and novelty
5. **Deduplication**: The system avoids storing duplicate information by comparing against existing findings
6. **Intelligent Storage**: Only high-quality, unique findings are stored for your review

### Motivation-Driven Research

Instead of relying on a fixed timer, the research engine uses a simple motivation
model. Internal drives like **boredom** and **curiosity** grow when the system is
idle or when you discuss new topics. **Tiredness** and **satisfaction** counter
these drives after heavy research. When the combined motivation crosses a
threshold, a new research cycle starts automatically. The rates and threshold can
be adjusted via environment variables.

### Using the Research Engine

#### Managing Research Topics

After any conversation, you'll see suggested research topics in the side panel. For each topic, you can:

- **Subscribe**: Click the "🔬 Research this topic" button to enable autonomous research
- **View Details**: See the topic description and why it was suggested
- **Unsubscribe**: Remove topics you're no longer interested in
- **Immediate Research**: When you have active research topics, use the "🚀 Research Now" button to trigger research immediately, bypassing the motivation system

Research findings include:
- **Summary**: Key insights and main points
- **Quality Scores**: Ratings for recency, relevance, depth, credibility, and novelty
- **Source URLs**: Links to original sources when available
- **Research Time**: When the research was conducted
- **Key Insights**: Bullet points of important discoveries

### Best Practices

- **Start Small**: Begin with 1-2 research topics to see how the system works
- **Quality Threshold**: Lower the threshold (e.g., 0.4) to get more findings, raise it (e.g., 0.8) for only the highest quality
- **Topic Specificity**: More specific topics (e.g., "GPT-4 performance benchmarks") yield better results than broad ones (e.g., "AI")
- **Regular Review**: Check your findings periodically and unsubscribe from topics that are no longer relevant

The research engine provides detailed logging with 🔬 emojis to help track research activities. All research operations are also traced through LangSmith if enabled.

## Setup

### Prerequisites

- Python 3.9+
- Node.js 14+ and npm
- OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   API_HOST=0.0.0.0
   API_PORT=8000
   DEFAULT_MODEL=gpt-4o-mini
   ```

5. Start the backend server:
   ```
   python app.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd chatbot-react
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. Open your browser and navigate to `http://localhost:3000` to view the chatbot.

## Project Structure

- `backend/`: Contains the FastAPI application and LangGraph implementation
  - `app.py`: Main FastAPI application
  - `graph_builder.py`: LangGraph builder that creates the processing graph
  - `research_graph_builder.py`: LangGraph builder for autonomous research workflow
  - `autonomous_research_engine.py`: Main autonomous research engine using LangGraph
  - `nodes/`: Modular node components used to build the graph
    - **Chat nodes**: `initializer_node.py`, `router_node.py`, `search_node.py`, etc.
    - **Research nodes**: `research_initializer_node.py`, `research_query_generator_node.py`, `research_quality_assessor_node.py`, `research_deduplication_node.py`, `research_storage_node.py`
  - `tests/`: Unit and integration tests
    - `unit/`: Unit tests for individual components
    - `integration/`: Integration tests requiring external services
  - `models.py`: Pydantic models for request/response
  - `llm_models.py`: Pydantic models for structured LLM outputs (including research models)
  - `prompts.py`: Centralized prompts used throughout the system (chat + research)
  - `config.py`: Configuration settings
  - `requirements.txt`: Python dependencies
- `chatbot-react/`: Contains the React frontend
  - `src/components/`: React components
  - `src/services/`: API services
  - `src/styles/`: CSS files
  - `src/App.jsx`: Main application component
  - `src/index.js`: Entry point

## Development

### Adding New Models

To add new models, update the SUPPORTED_MODELS dictionary in backend/config.py.

### Extending the Backend

The backend is designed to be flexible for future extensions:

- Add new nodes to the `nodes/` directory
- Modify graph structure in `graph_builder.py`
- Customize system prompts in `prompts.py`
- Add new API endpoints in `app.py`

### Testing

The backend includes a structured testing framework using pytest:

- Unit tests in `backend/tests/unit/`
- Integration tests in `backend/tests/integration/`
- Run tests with the provided script:
  ```
  cd backend
  source venv/bin/activate
  ./run_tests.sh         # Run unit tests only
  ./run_tests.sh --all   # Run unit and integration tests
  ./run_tests.sh --coverage  # Run tests with coverage report
  ```

Integration tests that require API keys will be skipped automatically if the keys are not available.

### Logging and Debugging

The application uses a centralized logging system to provide consistent log information across all components:

#### Log Levels

- **INFO**: Default log level for development, shows the main flow through the graph with emojis for visual distinction
- **DEBUG**: More detailed logs for troubleshooting specific issues
- **WARNING**: Problems that don't stop execution but may need attention
- **ERROR**: Critical issues that prevent proper functionality

#### LangSmith Tracing

The application supports LangSmith tracing for detailed monitoring and debugging of the LangGraph flow:

- **Enable Tracing**: Set `LANGCHAIN_TRACING_V2=true` and add your LangSmith API key in the `.env` file
- **View Traces**: Access the `/traces` endpoint to see recent traces and get links to the LangSmith UI
- **Trace Details**: Each trace includes timing, status, and links to detailed visualizations
- **Project Organization**: Traces are organized by project name (default: "researcher-prototype")

#### Enabling Debug Mode

You can enable more verbose logging in three ways:

1. **At application startup**: Modify the call to `configure_logging()` in `app.py`:
   ```python
   # Change from
   logger = configure_logging()
   # To
   logger = configure_logging(level=logging.DEBUG)
   ```

2. **During runtime**: When you encounter an issue, add this code to a route handler or the Python REPL:
   ```python
   from logging_config import enable_debug_logging
   enable_debug_logging()
   ```

3. **Using the debug endpoint**: The application provides a `/debug` endpoint that can be used to diagnose routing issues without executing the full graph:
   ```
   POST http://localhost:8000/debug
   ```
   with the same body format as the `/chat` endpoint.

#### Viewing Log Output

The application logs to the console by default with this format:
```
HH:MM:SS | LEVEL | LOGGER_NAME | MESSAGE
```

Each component of the graph uses emojis in logs for better visual identification:
- 🔄 Initializer: Initial setup and state preparation
- 🔀 Router: Message classification and routing
- 🔬 Search Optimizer: Refines user queries for search
- 🔍 Search: Web search related operations
- 🧩 Analyzer: Complex analysis operations
- 🧠 Integrator: Central reasoning component
- ✨ Renderer: Response formatting and enhancement
- ⚡ Flow: Transitions between components
- 🔬 Research Engine: Autonomous research operations (initializer, query generator, quality assessor, deduplication, storage)

#### Tracing Message Processing

The application includes detailed logging to trace a user's message through the entire processing pipeline:

1. **Input Capture**: User message content is logged when first received
2. **Router Analysis**: Shows which module was selected to handle the message and why
3. **Module Processing**: Each module logs its input and output
4. **Response Generation**: The final response is logged before being sent to the user

Example log sequence for a complete message flow:
```
12:34:56 | INFO | backend.graph | 🔀 Router: Processing user message: "What's the weather like today?"
12:34:57 | INFO | backend.graph | 🔀 Router: Selected module 'search' (complexity: 3) for message: "What's the weather like today?"
12:34:57 | INFO | backend.graph | ⚡ Flow: Routing to 'search' module
12:34:57 | INFO | backend.graph | 🔍 Search: Searching for: "What's the weather like today?"
12:34:59 | INFO | backend.graph | 🔍 Search: Result received: "Currently in your area, it's 72°F and sunny with light winds from the west..."
12:35:00 | INFO | backend.graph | 🧠 Integrator: Processing all contextual information
12:35:02 | INFO | backend.graph | 🧠 Integrator: Generated response: "The current weather is 72°F and sunny with light winds from the west..."
12:35:03 | INFO | backend.graph | ✨ Renderer: Produced formatted response: "It's currently 72°F and sunny with light winds from the west..."
```

This detailed logging helps you:
- Track exactly how each message is processed
- Identify which module handled a particular request
- Debug issues where messages are routed incorrectly
- See the transformation from user input to AI response

#### Customizing Logging

The logging system can be further customized in `logging_config.py`:
- Add file handlers to write logs to a file
- Customize the log format
- Set different log levels for different components

### Visualizing the LangGraph

The project includes a built-in visualization feature for the LangGraph. To generate a PNG diagram:

```bash
# Navigate to the backend directory
cd backend

# Activate the virtual environment
source venv/bin/activate  # On Linux/Mac

# Run the graph_builder.py module directly
python graph_builder.py
```

This will create a `graph.png` file in the current directory that shows the LangGraph structure. The visualization is generated using LangGraph's built-in visualization capabilities with Graphviz.

Requirements:
- Graphviz must be installed on your system: `sudo apt-get install graphviz`
- Make sure you've installed all Python dependencies from `requirements.txt` which includes the necessary packages for visualization

> **Note**: Always run `graph_builder.py` from within the activated virtual environment to ensure all dependencies are available.

The visualization is useful for:
- Understanding the flow of the application
- Debugging graph structure issues
- Documenting the architecture
- Seeing how different nodes connect

Simply run `python graph_builder.py` whenever you make changes to the graph structure to generate an updated visualization.

### Extending the Frontend

The React frontend is component-based, making it easy to add new features:

- Add new components in src/components/
- Add new API services in src/services/
- Modify the main App component in src/App.jsx

### Building for Production

#### Backend

The backend can be deployed using various methods:

- Docker
- Gunicorn with Uvicorn workers
- Cloud platforms like Heroku, AWS, or Google Cloud

#### Frontend  

To build the React frontend for production:

```
cd chatbot-react
npm run build
```

This creates a build directory with optimized production files that can be served by any static file server.

## License

GPLv3

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Make sure your OpenAI API key is correctly set in the `.env` file
   - Verify that your API key is active and has sufficient credits
   - Check backend logs for specific error messages

2. **Frontend Not Connecting to Backend**
   - Ensure the backend server is running on port 8000
   - Check that you don't have CORS issues (in browser developer console)
   - Verify the API URL in `chatbot-react/src/services/api.js` is correct

3. **User Settings Not Updating**
   - User settings are loaded when the dropdown is opened
   - If you update settings in one tab, you may need to refresh other tabs
   - Click the refresh button in the user dropdown to manually reload user data

4. **Missing Storage Data**
   - If `backend/storage_data` is missing, it will be created automatically on first run
   - If you're using a fresh clone of the repository, you'll need to create users again

5. **Diagnosing Processing Issues**
   - Use the visual emoji indicators in logs to trace message flow (🔀 🔬 🔍 🧩 🧠 ✨)
   - Enable debug logging using `enable_debug_logging()` function
   - Use the `/debug` endpoint to test message routing without full processing
   - For LLM API issues, check the error messages in the logs which will indicate rate limits, token limits, or API key problems

For more technical issues, check the console logs in both the browser and the terminal running the backend server. The application's logging system provides detailed information about the internal flow and any errors that occur.

