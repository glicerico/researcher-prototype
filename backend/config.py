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
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")

# Perplexity configuration for web search
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")

# LangSmith tracing configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "researcher-prototype")

# Other models that can be supported
SUPPORTED_MODELS = {
    "gpt-4o-mini": "OpenAI GPT-4o-mini",
    "gpt-4o": "OpenAI GPT-4o",
    # Add more models as needed
} 