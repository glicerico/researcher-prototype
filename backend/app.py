from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import os
import traceback
import time
from contextlib import asynccontextmanager

# Import config first to load environment variables
import config

# Import and configure logging after environment variables are loaded
from services.logging_config import configure_logging, get_logger

# Configure application logging
logger = configure_logging()

# Now import other modules that might use logging
from models import PersonalityConfig, UserSummary, UserProfile, TopicSuggestion
from pydantic import BaseModel


class MotivationConfigUpdate(BaseModel):
    threshold: Optional[float] = None
    boredom_rate: Optional[float] = None
    curiosity_decay: Optional[float] = None
    tiredness_decay: Optional[float] = None
    satisfaction_decay: Optional[float] = None


from dependencies import (
    storage_manager,
    profile_manager,
    research_manager,
    zep_manager,
    get_or_create_user_id,
    _motivation_config_override,
)
from services.autonomous_research_engine import AutonomousResearcher
from services.per_user_scheduler import PerUserScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application."""
    # Startup
    logger.info("🚀 Starting AI Chatbot API...")

    # Initialize the autonomous researcher
    try:
        logger.info("🔬 Initializing Autonomous Research Engine...")
        logger.info(f"App startup - Config override: {_motivation_config_override}")
        app.state.autonomous_researcher = AutonomousResearcher(
            profile_manager, research_manager, _motivation_config_override
        )
        logger.info("🔬 Autonomous Research Engine initialized")
    except Exception as e:
        logger.error(f"🔬 Failed to initialize Autonomous Research Engine: {str(e)}", exc_info=True)
        app.state.autonomous_researcher = None

    # Create per-user scheduler
    try:
        app.state.per_user_scheduler = PerUserScheduler(profile_manager, app.state.autonomous_researcher)
        logger.info("⏱️ Per-user scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize per-user scheduler: {str(e)}", exc_info=True)
        app.state.per_user_scheduler = None

    yield

    # Shutdown
    logger.info("🛑 Shutting down AI Chatbot API...")

    # Stop per-user scheduler
    if hasattr(app.state, "per_user_scheduler") and app.state.per_user_scheduler:
        try:
            logger.info("⏱️ Stopping per-user scheduler...")
            await app.state.per_user_scheduler.stop_all()
            logger.info("⏱️ Per-user scheduler stopped successfully")
        except Exception as e:
            logger.error(f"⏱️ Error stopping per-user scheduler: {str(e)}")


app = FastAPI(title="AI Chatbot API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # Use configurable origins from environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger = get_logger(__name__)
from api.chat import router as chat_router
from api.users import router as users_router
from api.topics import router as topics_router
from api.research import router as research_router
from api.admin import router as admin_router
from api.graph import router as graph_router
from api.status import router as status_router
from api.notifications import router as notifications_router

app.include_router(chat_router)
app.include_router(users_router)
app.include_router(topics_router)
app.include_router(research_router)
app.include_router(admin_router)
app.include_router(graph_router)
app.include_router(status_router)
app.include_router(notifications_router)

# Mount static files for diagrams
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "message": "AI Chatbot API is running",
        "autonomous_researcher": {"available": False, "enabled": False, "running": False},
    }

    # Check autonomous researcher status
    if hasattr(app.state, "autonomous_researcher") and app.state.autonomous_researcher:
        try:
            researcher_status = app.state.autonomous_researcher.get_status()
            health_status["autonomous_researcher"] = {
                "available": True,
                "enabled": researcher_status.get("enabled", False),
                "running": researcher_status.get("running", False),
                "interval_hours": researcher_status.get("research_interval_hours", 0),
                "engine_type": researcher_status.get("engine_type", "unknown"),
            }
        except Exception as e:
            health_status["autonomous_researcher"]["error"] = str(e)

    return health_status


@app.get("/zep/status")
async def zep_status():
    """Get Zep memory status."""
    try:
        return {
            "enabled": zep_manager.is_enabled(),
            "configured": config.ZEP_ENABLED,
            "api_key_set": bool(config.ZEP_API_KEY),
        }
    except Exception as e:
        logger.error(f"Error getting Zep status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting Zep status: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
