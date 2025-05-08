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
  - `graph.py`: LangGraph implementation
  - `models.py`: Pydantic models for request/response
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

- Add new nodes to the LangGraph in graph.py
- Add new API endpoints in app.py

### Visualizing the LangGraph

The project includes a built-in visualization feature for the LangGraph. To generate a PNG diagram:

```bash
# Navigate to the backend directory
cd backend

# Activate the virtual environment
source venv/bin/activate  # On Linux/Mac

# Run the graph.py module directly
python graph.py
```

This will create a `graph.png` file in the current directory that shows the LangGraph structure. The visualization is generated using LangGraph's built-in visualization capabilities with Graphviz.

Requirements:
- Graphviz must be installed on your system: `sudo apt-get install graphviz`
- Make sure you've installed all Python dependencies from `requirements.txt` which includes the necessary packages for visualization

> **Note**: Always run `graph.py` from within the activated virtual environment to ensure all dependencies are available.

The visualization is useful for:
- Understanding the flow of the application
- Debugging graph structure issues
- Documenting the architecture
- Seeing how different nodes connect

Simply run `python graph.py` whenever you make changes to the graph structure to generate an updated visualization.

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

For more technical issues, check the console logs in both the browser and the terminal running the backend server.

