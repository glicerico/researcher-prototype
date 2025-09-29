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

# Topic Expansion Pipeline configuration
ZEP_SEARCH_LIMIT = int(os.getenv("ZEP_SEARCH_LIMIT", "10"))
ZEP_SEARCH_RERANKER = os.getenv("ZEP_SEARCH_RERANKER", "cross_encoder")
EXPLORATION_PER_ROOT_MAX = int(os.getenv("EXPLORATION_PER_ROOT_MAX", "2"))  # Keep at 2 since LLM now generates fewer, higher quality topics
EXPANSION_MIN_SIMILARITY = float(os.getenv("EXPANSION_MIN_SIMILARITY", "0.35"))
def _clamp_float(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo

# Clamp an integer value to the range [lo, hi]. Returns lo if conversion fails.
def _clamp_int(v: int, lo: int = 0, hi: int = 1_000_000) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except Exception:
        return lo

EXPANSION_MAX_PARALLEL = _clamp_int(int(os.getenv("EXPANSION_MAX_PARALLEL", "2")), 1, 64)

# Expansion LLM selection and augmentation - always enabled for quality
# EXPANSION_LLM_ENABLED removed - LLM is always used for topic expansion
EXPANSION_LLM_MODEL = os.getenv("EXPANSION_LLM_MODEL", "gpt-4o-mini")
EXPANSION_LLM_CONFIDENCE_THRESHOLD = _clamp_float(float(os.getenv("EXPANSION_LLM_CONFIDENCE_THRESHOLD", "0.6")), 0.0, 1.0)
EXPANSION_LLM_TIMEOUT_SECONDS = _clamp_int(int(os.getenv("EXPANSION_LLM_TIMEOUT_SECONDS", "30")), 1, 120)

# LLM hyperparameters - internal model tuning constants
EXPANSION_LLM_MAX_TOKENS = 800              # Token limit for expansion LLM calls
EXPANSION_LLM_TEMPERATURE = 0.2             # Temperature for expansion LLM calls
EXPANSION_LLM_SUGGESTION_LIMIT = 3          # Maximum topics to generate per expansion

# Expansion lifecycle and depth management
EXPANSION_MAX_DEPTH = _clamp_int(int(os.getenv("EXPANSION_MAX_DEPTH", "2")), 1, 10)

# Internal expansion lifecycle constants (rarely changed)
EXPANSION_ENGAGEMENT_WINDOW_DAYS = 7        # Days to look back for engagement scoring
EXPANSION_PROMOTE_ENGAGEMENT = 0.35         # Engagement threshold to enable child expansions
EXPANSION_RETIRE_ENGAGEMENT = 0.1           # Engagement threshold to retire topics
EXPANSION_MIN_QUALITY = 0.6                 # Minimum quality threshold for promotion
EXPANSION_BACKOFF_DAYS = 7                  # Days to back off after low engagement
EXPANSION_RETIRE_TTL_DAYS = 30              # Days before retiring inactive expansions

# Zep search configuration - operational defaults
ZEP_SEARCH_TIMEOUT_SECONDS = 5              # Timeout for Zep API calls
ZEP_SEARCH_RETRIES = 2                      # Number of retries for failed calls

# Clamp similarity threshold
EXPANSION_MIN_SIMILARITY = _clamp_float(EXPANSION_MIN_SIMILARITY, 0.0, 1.0)

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
MOTIVATION_BOREDOM_RATE = float(os.getenv("MOTIVATION_BOREDOM_RATE", "0.0002"))
MOTIVATION_CURIOSITY_DECAY = float(os.getenv("MOTIVATION_CURIOSITY_DECAY", "0.0002"))
MOTIVATION_TIREDNESS_DECAY = float(os.getenv("MOTIVATION_TIREDNESS_DECAY", "0.0002"))
MOTIVATION_SATISFACTION_DECAY = float(os.getenv("MOTIVATION_SATISFACTION_DECAY", "0.0002"))

# Topic-level motivation parameters
TOPIC_MOTIVATION_THRESHOLD = float(os.getenv("TOPIC_MOTIVATION_THRESHOLD", "0.5"))
TOPIC_ENGAGEMENT_WEIGHT = float(os.getenv("TOPIC_ENGAGEMENT_WEIGHT", "0.3"))
TOPIC_QUALITY_WEIGHT = float(os.getenv("TOPIC_QUALITY_WEIGHT", "0.2"))
TOPIC_STALENESS_SCALE = float(os.getenv("TOPIC_STALENESS_SCALE", "0.0001"))  # Scale factor for staleness time

# Engagement scoring constants - internal algorithm tuning
ENGAGEMENT_RESEARCH_WEIGHT = 2.0           # Weight for research findings interaction
ENGAGEMENT_ANALYTICS_WEIGHT = 0.5          # Weight for general analytics  
ENGAGEMENT_RECENT_BONUS_RATE = 0.2         # Bonus per recent read
ENGAGEMENT_RECENT_BONUS_MAX = 0.5          # Max recent bonus
ENGAGEMENT_VOLUME_BONUS_RATE = 0.1         # Bonus per total finding
ENGAGEMENT_VOLUME_BONUS_MAX = 0.3          # Max volume bonus
ENGAGEMENT_BOOKMARK_BONUS_RATE = 0.15      # Bonus per bookmark
ENGAGEMENT_BOOKMARK_BONUS_MAX = 0.45       # Max bookmark bonus
ENGAGEMENT_INTEGRATION_BONUS_RATE = 0.2    # Bonus per integration
ENGAGEMENT_INTEGRATION_BONUS_MAX = 0.6     # Max integration bonus
ENGAGEMENT_SCORE_MAX = 2.0                 # Cap total engagement score

# Research timing constants - operational defaults
RESEARCH_CYCLE_SLEEP_INTERVAL = 300        # Sleep between research cycles (seconds)
RESEARCH_TOPIC_DELAY = 1.0                 # Delay between topics (seconds)  
RESEARCH_MANUAL_DELAY = 0.5                # Delay in manual research (seconds)
RESEARCH_MAX_TOKENS = 2000                 # Max tokens for research LLM calls
STATUS_MIN_INTERVAL = 0.3                  # Minimum seconds between status updates

# Admin interface configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change this in production!
ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "your-secret-key-change-in-production")
ADMIN_JWT_ALGORITHM = os.getenv("ADMIN_JWT_ALGORITHM", "HS256")
ADMIN_JWT_EXPIRE_MINUTES = int(os.getenv("ADMIN_JWT_EXPIRE_MINUTES", "480"))  # 8 hours
