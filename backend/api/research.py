from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
import time

from dependencies import get_or_create_user_id, profile_manager, research_manager, zep_manager, _motivation_config_override
from services.autonomous_research_engine import initialize_autonomous_researcher
from services.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


class MotivationConfigUpdate(BaseModel):
    threshold: Optional[float] = None
    boredom_rate: Optional[float] = None
    curiosity_decay: Optional[float] = None
    tiredness_decay: Optional[float] = None
    satisfaction_decay: Optional[float] = None


@router.get("/research/findings/{user_id}")
async def get_research_findings(
    user_id: str,
    topic_name: Optional[str] = Query(None, description="Filter by topic name"),
    unread_only: bool = Query(False, description="Only return unread findings"),
):
    """Get research findings for a user, optionally filtered by topic or read status."""
    try:
        # Use the new API method from research_manager
        findings = research_manager.get_research_findings_for_api(user_id, topic_name, unread_only)

        return {
            "success": True,
            "user_id": user_id,
            "total_findings": len(findings),
            "filters": {"topic_name": topic_name, "unread_only": unread_only},
            "findings": findings,
        }

    except Exception as e:
        logger.error(f"Error getting research findings for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research findings: {str(e)}")


@router.post("/research/findings/{finding_id}/mark_read")
async def mark_research_finding_read(finding_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Mark a research finding as read."""
    try:
        success = research_manager.mark_finding_as_read(user_id, finding_id)

        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")

        return {"success": True, "message": f"Marked finding {finding_id} as read", "finding_id": finding_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking finding as read for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error marking finding as read: {str(e)}")


@router.post("/research/findings/{finding_id}/integrate")
async def integrate_research_finding(finding_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Integrate a research finding into the knowledge graph."""
    try:
        # First get the finding to make sure it exists and get its content
        findings = research_manager.get_research_findings_for_api(user_id, None, False)
        finding = None
        
        for f in findings:
            if f.get("finding_id") == finding_id:
                finding = f
                break
        
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")
            
        if finding.get("integrated"):
            return {
                "success": True, 
                "message": "Finding is already integrated",
                "finding_id": finding_id,
                "was_already_integrated": True
            }

        # Submit key insights to Zep for automatic entity/relationship extraction
        key_insights = finding.get("key_insights", [])
        if not key_insights:
            # If no key insights, use the findings summary as content
            key_insights = [finding.get("findings_summary", "No summary available")]
        
        try:
            # Use Zep's content submission for entity extraction
            zep_success = await zep_manager.store_research_finding(
                user_id=user_id,
                topic_name=finding.get("topic_name", "Unknown Topic"),
                key_insights=key_insights,
                finding_id=finding_id
            )
            
            if not zep_success:
                logger.warning(f"Failed to store research finding in Zep for finding {finding_id}")
        
        except Exception as e:
            logger.error(f"Error submitting content to Zep: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error integrating with knowledge graph: {str(e)}")

        # Mark the finding as integrated
        integration_success = research_manager.mark_finding_as_integrated(user_id, finding_id)
        
        if not integration_success:
            logger.warning(f"Added to knowledge graph but failed to mark finding {finding_id} as integrated")
        
        return {
            "success": True,
            "message": f"Successfully submitted finding to knowledge graph for entity extraction",
            "finding_id": finding_id,
            "topic_name": finding.get("topic_name"),
            "key_insights_submitted": len(key_insights),
            "zep_integration_success": zep_success,
            "integration_marked": integration_success,
            "was_already_integrated": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error integrating finding {finding_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error integrating finding: {str(e)}")


@router.delete("/research/findings/{finding_id}")
async def delete_research_finding(finding_id: str, user_id: str = Depends(get_or_create_user_id)):
    """Delete a specific research finding."""
    try:
        result = research_manager.delete_research_finding(user_id, finding_id)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "message": "Successfully deleted research finding",
            "deleted_finding": result["deleted_finding"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting research finding {finding_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting research finding: {str(e)}")


@router.delete("/research/findings/topic/{topic_name}")
async def delete_all_topic_findings(topic_name: str, user_id: str = Depends(get_or_create_user_id)):
    """Delete all research findings for a specific topic."""
    try:
        result = research_manager.delete_all_topic_findings(user_id, topic_name)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "message": f"Successfully deleted all findings for topic '{topic_name}'",
            "topic_name": result["topic_name"],
            "findings_deleted": result["findings_deleted"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all findings for topic '{topic_name}' for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting topic findings: {str(e)}")


@router.get("/research/status")
async def get_research_engine_status(request: Request):
    """Get the current status of the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher"):
            status = request.app.state.autonomous_researcher.get_status()
            return status
        else:
            return {"enabled": False, "running": False, "error": "Autonomous researcher not initialized"}

    except Exception as e:
        logger.error(f"Error getting research engine status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research status: {str(e)}")


@router.get("/research/debug/active-topics")
async def get_debug_active_topics():
    """Debug endpoint to see active research topics across all users."""
    try:
        debug_info = {"total_users": 0, "users_with_active_topics": 0, "total_active_topics": 0, "user_breakdown": []}

        # Get all users
        all_users = profile_manager.list_users()
        debug_info["total_users"] = len(all_users)

        for user_id in all_users:
            try:
                active_topics = research_manager.get_active_research_topics(user_id)
                if active_topics:
                    debug_info["users_with_active_topics"] += 1
                    debug_info["total_active_topics"] += len(active_topics)

                    debug_info["user_breakdown"].append(
                        {
                            "user_id": user_id,
                            "active_topics_count": len(active_topics),
                            "topics": [
                                {
                                    "name": topic.get("topic_name"),
                                    "description": (
                                        topic.get("description", "")[:100] + "..."
                                        if len(topic.get("description", "")) > 100
                                        else topic.get("description", "")
                                    ),
                                    "last_researched": topic.get("last_researched"),
                                    "research_count": topic.get("research_count", 0),
                                }
                                for topic in active_topics
                            ],
                        }
                    )

            except Exception as e:
                logger.error(f"Error getting active topics for user {user_id}: {str(e)}")
                continue

        return debug_info

    except Exception as e:
        logger.error(f"Error getting debug active topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting debug info: {str(e)}")


@router.get("/research/debug/config-override")
async def get_config_override():
    """Debug endpoint to see what's in the config override."""
    return {"override": _motivation_config_override}


@router.post("/research/debug/clear-override")
async def clear_config_override():
    """Debug endpoint to clear the config override."""
    global _motivation_config_override
    _motivation_config_override = {}
    return {"success": True, "message": "Config override cleared"}


@router.get("/research/debug/motivation")
async def get_motivation_status(request: Request):
    """Debug endpoint to check motivation system status."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation

            # Only tick if the research engine is actually running
            # This ensures drives only evolve when the engine is active
            if researcher.is_running:
                motivation.tick()

            return {
                "motivation_system": {
                    "boredom": round(motivation.boredom, 4),
                    "curiosity": round(motivation.curiosity, 4),
                    "tiredness": round(motivation.tiredness, 4),
                    "satisfaction": round(motivation.satisfaction, 4),
                    "impetus": round(motivation.impetus(), 4),
                    "threshold": motivation.drives.threshold,
                    "should_research": motivation.should_research(),
                    "time_since_last_tick": round(time.time() - motivation.last_tick, 2),
                },
                "research_engine": {
                    "enabled": researcher.enabled,
                    "running": researcher.is_running,
                    "check_interval": researcher.check_interval,
                },
                "drive_rates": {
                    "boredom_rate": motivation.drives.boredom_rate,
                    "curiosity_decay": motivation.drives.curiosity_decay,
                    "tiredness_decay": motivation.drives.tiredness_decay,
                    "satisfaction_decay": motivation.drives.satisfaction_decay,
                },
            }
        else:
            return {"error": "Autonomous researcher not available"}

    except Exception as e:
        logger.error(f"Error getting motivation status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting motivation status: {str(e)}")


@router.post("/research/debug/trigger-user-activity")
async def trigger_user_activity(request: Request):
    """Debug endpoint to simulate user activity (increases curiosity)."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            researcher.motivation.on_user_activity()

            return {
                "success": True,
                "message": "User activity triggered",
                "new_motivation_state": {
                    "boredom": round(researcher.motivation.boredom, 4),
                    "curiosity": round(researcher.motivation.curiosity, 4),
                    "impetus": round(researcher.motivation.impetus(), 4),
                    "should_research": researcher.motivation.should_research(),
                },
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error triggering user activity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering user activity: {str(e)}")


@router.post("/research/debug/adjust-drives")
async def adjust_motivation_drives(
    request: Request,
    boredom: Optional[float] = None,
    curiosity: Optional[float] = None,
    tiredness: Optional[float] = None,
    satisfaction: Optional[float] = None,
):
    """Debug endpoint to manually set motivation drive values for testing."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation

            old_values = {
                "boredom": motivation.boredom,
                "curiosity": motivation.curiosity,
                "tiredness": motivation.tiredness,
                "satisfaction": motivation.satisfaction,
            }

            # Update provided values
            if boredom is not None:
                motivation.boredom = max(0.0, min(1.0, boredom))
            if curiosity is not None:
                motivation.curiosity = max(0.0, min(1.0, curiosity))
            if tiredness is not None:
                motivation.tiredness = max(0.0, min(1.0, tiredness))
            if satisfaction is not None:
                motivation.satisfaction = max(0.0, min(1.0, satisfaction))

            new_values = {
                "boredom": motivation.boredom,
                "curiosity": motivation.curiosity,
                "tiredness": motivation.tiredness,
                "satisfaction": motivation.satisfaction,
            }

            return {
                "success": True,
                "message": "Motivation drives adjusted",
                "old_values": old_values,
                "new_values": new_values,
                "impetus": round(motivation.impetus(), 4),
                "should_research": motivation.should_research(),
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error adjusting motivation drives: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adjusting drives: {str(e)}")


@router.post("/research/debug/update-config")
async def update_motivation_config(request: Request, config: MotivationConfigUpdate):
    """Debug endpoint to update motivation system configuration parameters."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation
            drives_config = motivation.drives

            # Check if this is a complete config replacement (all parameters provided)
            all_params_provided = all(
                getattr(config, param) is not None
                for param in ["threshold", "boredom_rate", "curiosity_decay", "tiredness_decay", "satisfaction_decay"]
            )

            if all_params_provided:
                # Complete replacement - clear override and set new values
                global _motivation_config_override
                _motivation_config_override = {}

            # Update provided values
            if config.threshold is not None:
                value = max(0.1, min(10.0, config.threshold))
                drives_config.threshold = value
                _motivation_config_override["threshold"] = value
            if config.boredom_rate is not None:
                value = max(0.0, min(0.1, config.boredom_rate))
                drives_config.boredom_rate = value
                _motivation_config_override["boredom_rate"] = value
            if config.curiosity_decay is not None:
                value = max(0.0, min(0.1, config.curiosity_decay))
                drives_config.curiosity_decay = value
                _motivation_config_override["curiosity_decay"] = value
            if config.tiredness_decay is not None:
                value = max(0.0, min(0.1, config.tiredness_decay))
                drives_config.tiredness_decay = value
                _motivation_config_override["tiredness_decay"] = value
            if config.satisfaction_decay is not None:
                value = max(0.0, min(0.1, config.satisfaction_decay))
                drives_config.satisfaction_decay = value
                _motivation_config_override["satisfaction_decay"] = value

            return {
                "success": True,
                "message": "Motivation configuration updated",
                "impetus": round(motivation.impetus(), 4),
                "should_research": motivation.should_research(),
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error updating motivation config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@router.post("/research/debug/simulate-research-completion")
async def simulate_research_completion(request: Request, quality_score: float = 0.7):
    """Debug endpoint to simulate research completion with specified quality."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher

            old_state = {
                "boredom": researcher.motivation.boredom,
                "curiosity": researcher.motivation.curiosity,
                "tiredness": researcher.motivation.tiredness,
                "satisfaction": researcher.motivation.satisfaction,
            }

            researcher.motivation.on_research_completed(quality_score)

            new_state = {
                "boredom": researcher.motivation.boredom,
                "curiosity": researcher.motivation.curiosity,
                "tiredness": researcher.motivation.tiredness,
                "satisfaction": researcher.motivation.satisfaction,
            }

            return {
                "success": True,
                "message": f"Research completion simulated with quality {quality_score}",
                "quality_score": quality_score,
                "old_state": old_state,
                "new_state": new_state,
                "impetus": round(researcher.motivation.impetus(), 4),
                "should_research": researcher.motivation.should_research(),
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error simulating research completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error simulating research completion: {str(e)}")


@router.post("/research/trigger/{user_id}")
async def trigger_research_for_user(request: Request, user_id: str):
    """Manually trigger research for a specific user (for testing/debugging)."""
    try:
        if hasattr(request.app.state, "autonomous_researcher"):
            result = await request.app.state.autonomous_researcher.trigger_research_for_user(user_id)
            return result
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering research for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering research: {str(e)}")


@router.post("/research/control/start")
async def start_research_engine(request: Request):
    """Start the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            # Enable and start
            request.app.state.autonomous_researcher.enable()
            await request.app.state.autonomous_researcher.start()
            return {
                "success": True,
                "message": "Autonomous research engine started successfully",
                "status": request.app.state.autonomous_researcher.get_status(),
            }
        else:
            # Try to initialize if not available
            try:
                logger.info("🔬 Re-initializing Autonomous Research Engine...")
                request.app.state.autonomous_researcher = initialize_autonomous_researcher(
                    profile_manager, research_manager, _motivation_config_override
                )
                request.app.state.autonomous_researcher.enable()
                await request.app.state.autonomous_researcher.start()
                logger.info("🔬 Autonomous Research Engine re-initialized and started successfully")
                return {
                    "success": True,
                    "message": "Autonomous research engine initialized and started successfully",
                    "status": request.app.state.autonomous_researcher.get_status(),
                }
            except Exception as e:
                logger.error(f"🔬 Failed to initialize/start Autonomous Research Engine: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to start research engine: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting research engine: {str(e)}")


@router.post("/research/control/stop")
async def stop_research_engine(request: Request):
    """Stop the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            # Stop and disable
            await request.app.state.autonomous_researcher.stop()
            request.app.state.autonomous_researcher.disable()
            return {
                "success": True,
                "message": "Autonomous research engine stopped successfully",
                "status": request.app.state.autonomous_researcher.get_status(),
            }
        else:
            return {
                "success": True,
                "message": "Autonomous research engine was not running",
                "status": {"enabled": False, "running": False, "error": "Research engine not initialized"},
            }

    except Exception as e:
        logger.error(f"Error stopping research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping research engine: {str(e)}")


@router.post("/research/control/restart")
async def restart_research_engine(request: Request):
    """Restart the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            # Stop first
            await request.app.state.autonomous_researcher.stop()
            # Then enable and start again
            request.app.state.autonomous_researcher.enable()
            await request.app.state.autonomous_researcher.start()
            return {
                "success": True,
                "message": "Autonomous research engine restarted successfully",
                "status": request.app.state.autonomous_researcher.get_status(),
            }
        else:
            # Try to initialize if not available
            try:
                logger.info("🔬 Initializing Autonomous Research Engine for restart...")
                request.app.state.autonomous_researcher = initialize_autonomous_researcher(
                    profile_manager, research_manager, _motivation_config_override
                )
                request.app.state.autonomous_researcher.enable()
                await request.app.state.autonomous_researcher.start()
                logger.info("🔬 Autonomous Research Engine initialized and started successfully")
                return {
                    "success": True,
                    "message": "Autonomous research engine initialized and started successfully",
                    "status": request.app.state.autonomous_researcher.get_status(),
                }
            except Exception as e:
                logger.error(f"🔬 Failed to initialize/restart Autonomous Research Engine: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to restart research engine: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restarting research engine: {str(e)}")


@router.get("/topics/user/{user_id}/research")
async def get_active_research_topics(user_id: str):
    """Get all active research topics for a user."""
    try:
        active_topics = research_manager.get_active_research_topics(user_id)

        # Format for API response
        api_topics = []
        for topic in active_topics:
            api_topics.append(
                {
                    "topic_name": topic.get("topic_name"),
                    "description": topic.get("description"),
                    "session_id": topic.get("session_id"),
                    "research_enabled_at": topic.get("research_enabled_at"),
                    "last_researched": topic.get("last_researched"),
                    "research_count": topic.get("research_count", 0),
                    "confidence_score": topic.get("confidence_score", 0.0),
                }
            )

        return {
            "success": True,
            "user_id": user_id,
            "active_research_topics": api_topics,
            "total_count": len(api_topics),
        }

    except Exception as e:
        logger.error(f"Error getting active research topics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting active research topics: {str(e)}")


@router.put("/topics/topic/{topic_id}/research")
async def enable_disable_research_by_topic_id(
    topic_id: str,
    enable: bool = Query(True, description="True to enable, False to disable"),
    user_id: str = Depends(get_or_create_user_id),
):
    """Enable or disable research for a topic by its unique ID (safer than index-based operations)."""
    try:
        # Use the safe ID-based method to update research status
        result = research_manager.update_topic_research_status_by_id(user_id, topic_id, enable)

        if result["success"]:
            updated_topic = result["updated_topic"]
            action = "enabled" if enable else "disabled"
            return {
                "success": True,
                "message": f"Research {action} for topic: {updated_topic['topic_name']}",
                "topic": {
                    "topic_id": updated_topic["topic_id"],
                    "name": updated_topic["topic_name"],
                    "description": updated_topic["description"],
                    "session_id": updated_topic["session_id"],
                    "is_active_research": enable,
                },
            }
        else:
            # Map specific errors to appropriate HTTP status codes
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating research status for topic ID {topic_id}, user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating research status: {str(e)}")
