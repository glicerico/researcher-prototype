import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://yourapp.com").split(",")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

# Router model - cheaper model for routing decisions
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")

# Perplexity configuration for web search
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")


# PubMed API configuration (email recommended but not required)
PUBMED_EMAIL = os.getenv("PUBMED_EMAIL", "researcher@example.com")

# Semantic Scholar API key (optional, increases rate limits)
# OpenAlex API doesn't require an API key

# Zep configuration
ZEP_API_KEY = os.getenv("ZEP_API_KEY")
ZEP_ENABLED = os.getenv("ZEP_ENABLED", "false").lower() == "true"

# Topic Expansion (Phase 1 - debug) configuration
EXPANSION_ENABLED = os.getenv("EXPANSION_ENABLED", "false").lower() == "true"
ZEP_SEARCH_LIMIT = int(os.getenv("ZEP_SEARCH_LIMIT", "10"))
ZEP_SEARCH_RERANKER = os.getenv("ZEP_SEARCH_RERANKER", "cross_encoder")
EXPLORATION_PER_ROOT_MAX = int(os.getenv("EXPLORATION_PER_ROOT_MAX", "2"))
EXPANSION_MIN_SIMILARITY = float(os.getenv("EXPANSION_MIN_SIMILARITY", "0.35"))
EXPANSION_MAX_PARALLEL = int(os.getenv("EXPANSION_MAX_PARALLEL", "2"))

# Expansion LLM (Phase 3)
EXPANSION_LLM_ENABLED = os.getenv("EXPANSION_LLM_ENABLED", "true").lower() == "true"
EXPANSION_LLM_MODEL = os.getenv("EXPANSION_LLM_MODEL", "gpt-4o-mini")
EXPANSION_LLM_MAX_TOKENS = int(os.getenv("EXPANSION_LLM_MAX_TOKENS", "800"))
EXPANSION_LLM_TEMPERATURE = float(os.getenv("EXPANSION_LLM_TEMPERATURE", "0.2"))
EXPANSION_LLM_SUGGESTION_LIMIT = int(os.getenv("EXPANSION_LLM_SUGGESTION_LIMIT", "6"))

# LangSmith tracing configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "researcher-prototype")

# Other models that can be supported
SUPPORTED_MODELS = {
    "gpt-4o-mini": {
        "name": "GPT-4o Mini", 
        "provider": "OpenAI"
    },
    "gpt-4o": {
        "name": "GPT-4o", 
        "provider": "OpenAI"
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo", 
        "provider": "OpenAI"
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo", 
        "provider": "OpenAI"
    },
}

def get_available_models():
    """Get list of available models based on configuration."""
    return SUPPORTED_MODELS.copy()

def get_default_model():
    """Get the default model, ensuring it's available."""
    default = DEFAULT_MODEL
    available = get_available_models()
    
    if default not in available:
        # Fallback to first available model if default is not available
        default = next(iter(available.keys())) if available else DEFAULT_MODEL
    
    return default

# Message management configuration
MAX_MESSAGES_IN_STATE = int(os.getenv("MAX_MESSAGES_IN_STATE", "4"))

# Topic extraction configuration
TOPIC_EXTRACTION_MODEL = os.getenv("TOPIC_EXTRACTION_MODEL", "gpt-4o-mini")
TOPIC_MIN_CONFIDENCE = float(os.getenv("TOPIC_MIN_CONFIDENCE", "0.8"))
TOPIC_MAX_SUGGESTIONS = int(os.getenv("TOPIC_MAX_SUGGESTIONS", "3"))
TOPIC_EXTRACTION_TEMPERATURE = float(os.getenv("TOPIC_EXTRACTION_TEMPERATURE", "0.3"))
TOPIC_EXTRACTION_MAX_TOKENS = int(os.getenv("TOPIC_EXTRACTION_MAX_TOKENS", "800"))

# Autonomous Research Engine configuration
RESEARCH_ENGINE_ENABLED = os.getenv("RESEARCH_ENGINE_ENABLED", "false").lower() == "true"
RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "gpt-4o-mini")
RESEARCH_QUALITY_THRESHOLD = float(os.getenv("RESEARCH_QUALITY_THRESHOLD", "0.6"))
RESEARCH_MAX_TOPICS_PER_USER = int(os.getenv("RESEARCH_MAX_TOPICS_PER_USER", "3"))
RESEARCH_FINDINGS_RETENTION_DAYS = int(os.getenv("RESEARCH_FINDINGS_RETENTION_DAYS", "30"))

# Search Results Configuration
SEARCH_RESULTS_LIMIT = 10  # Standard limit for all search API calls

# Motivation system configuration
MOTIVATION_CHECK_INTERVAL = int(os.getenv("MOTIVATION_CHECK_INTERVAL", "60"))
MOTIVATION_THRESHOLD = float(os.getenv("MOTIVATION_THRESHOLD", "2.0"))  # Conservative default
MOTIVATION_BOREDOM_RATE = float(os.getenv("MOTIVATION_BOREDOM_RATE", "0.0005"))
MOTIVATION_CURIOSITY_DECAY = float(os.getenv("MOTIVATION_CURIOSITY_DECAY", "0.0002"))
MOTIVATION_TIREDNESS_DECAY = float(os.getenv("MOTIVATION_TIREDNESS_DECAY", "0.0002"))
MOTIVATION_SATISFACTION_DECAY = float(os.getenv("MOTIVATION_SATISFACTION_DECAY", "0.0002"))

# Topic-level motivation parameters
TOPIC_MOTIVATION_THRESHOLD = float(os.getenv("TOPIC_MOTIVATION_THRESHOLD", "0.5"))
TOPIC_ENGAGEMENT_WEIGHT = float(os.getenv("TOPIC_ENGAGEMENT_WEIGHT", "0.3"))
TOPIC_QUALITY_WEIGHT = float(os.getenv("TOPIC_QUALITY_WEIGHT", "0.2"))
TOPIC_STALENESS_SCALE = float(os.getenv("TOPIC_STALENESS_SCALE", "0.0001"))  # Scale factor for staleness time

# Admin interface configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change this in production!
ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "your-secret-key-change-in-production")
ADMIN_JWT_ALGORITHM = os.getenv("ADMIN_JWT_ALGORITHM", "HS256")
ADMIN_JWT_EXPIRE_MINUTES = int(os.getenv("ADMIN_JWT_EXPIRE_MINUTES", "480"))  # 8 hours
