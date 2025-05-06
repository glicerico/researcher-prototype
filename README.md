# AI Chatbot Web App

A simple chatbot web application with a React frontend and a flexible backend using LangGraph and an LLM model.

## Features

- Modern React-based user interface
- Clean, responsive web interface
- Backend built with FastAPI and LangGraph
- Uses OpenAI's o4-mini model by default
- Component-based architecture for easy extensibility
- Debug mode for troubleshooting


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

