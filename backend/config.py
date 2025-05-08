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

# Router model - cheaper model for routing decisions
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-3.5-turbo")

# Other models that can be supported
SUPPORTED_MODELS = {
    "gpt-4o-mini": "OpenAI GPT-4o-mini",
    "gpt-4o": "OpenAI GPT-4o",
    "gpt-3.5-turbo": "OpenAI GPT-3.5-Turbo",
    # Add more models as needed
} 