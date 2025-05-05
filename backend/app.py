from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from models import ChatRequest, ChatResponse, Message
from graph import chat_graph
import config
import traceback
import logging

app = FastAPI(title="Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify the actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"message": "Chatbot API is running"}


@app.get("/models")
async def get_models():
    return {"models": config.SUPPORTED_MODELS}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Log the incoming request
        logger.debug(f"Chat request: {request}")
        
        # Prepare the state for the graph
        state = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        # Run the graph
        result = chat_graph.invoke(state)
        
        # Check if there was an error
        if "error" in result:
            error_msg = result["error"]
            logger.error(f"Error from graph: {error_msg}")
            raise Exception(error_msg)
        
        # Extract the assistant's response (the last message)
        assistant_message = result["messages"][-1]
        
        return ChatResponse(
            response=assistant_message["content"],
            model=request.model,
            usage={}  # In a real app, you might want to track token usage
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug")
async def debug(request: ChatRequest):
    """Debug endpoint to check what's happening with the request."""
    try:
        # Log the request
        print(f"Debug request: {request}")
        
        # Prepare the state for the graph (same as in chat endpoint)
        state = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        # Return the state without processing it
        return {
            "request_received": True,
            "state": state,
            "api_key_set": bool(config.OPENAI_API_KEY),  # Check if API key is set
            "model": request.model
        }
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    ) 