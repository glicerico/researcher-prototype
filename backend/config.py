import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

# Other models that can be supported
SUPPORTED_MODELS = {
    "gpt-4o-mini": "OpenAI GPT-4o-mini",
    "gpt-4o": "OpenAI GPT-4o",
    # Add more models as needed
} 