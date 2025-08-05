from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio

from models import ChatRequest, ChatResponse
from graph_builder import chat_graph
from dependencies import get_or_create_user_id, profile_manager, zep_manager
from services.chat_service import extract_and_store_topics_async
from logging_config import get_logger
from status_manager import queue_status

router = APIRouter()
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user_id: str = Depends(get_or_create_user_id)):
    try:
        logger.debug(f"Chat request: {request}")

        messages_for_state = []
        for m in request.messages:
            if m.role == "user":
                messages_for_state.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                messages_for_state.append(AIMessage(content=m.content))
            elif m.role == "system":
                messages_for_state.append(SystemMessage(content=m.content))

        state = {
            "messages": messages_for_state,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "personality": request.personality.model_dump() if request.personality else None,
            "current_module": None,
            "module_results": {},
            "workflow_context": {},
            "user_id": user_id,
            "thread_id": request.thread_id,
        }

        if request.personality:
            profile_manager.update_personality(user_id, request.personality.model_dump())

        try:
            # Motivation system
            pass  # activity triggered from main app if available
        except Exception as e:
            logger.warning(f"Failed to trigger user activity for motivation system: {str(e)}")

        result = await chat_graph.ainvoke(state)

        if "error" in result:
            raise Exception(result["error"])

        assistant_message = result["messages"][-1]

        if len(request.messages) > 0:
            user_message = request.messages[-1].content
            try:
                asyncio.create_task(
                    zep_manager.store_conversation_turn(
                        user_id=user_id,
                        user_message=user_message,
                        ai_response=assistant_message.content,
                        thread_id=result.get("thread_id"),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store conversation in Zep: {str(e)}")

        if result.get("thread_id") and len(request.messages) > 0:
            try:
                asyncio.create_task(
                    extract_and_store_topics_async(
                        state=result,
                        user_id=user_id,
                        thread_id=result["thread_id"],
                        conversation_context=request.messages[-1].content[:200]
                        + ("..." if len(request.messages[-1].content) > 200 else ""),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to start background topic extraction: {str(e)}")

        response_obj = ChatResponse(
            response=assistant_message.content,
            model=request.model,
            usage={},
            module_used=result.get("current_module", "unknown"),
            routing_analysis=result.get("routing_analysis"),
            user_id=user_id,
            thread_id=result.get("thread_id"),
            suggested_topics=[],
            follow_up_questions=result.get("workflow_context", {}).get("follow_up_questions", []),
        )
        queue_status(result.get("thread_id"), "Complete")
        return response_obj
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_models():
    from config import get_available_models, get_default_model

    available_models = get_available_models()
    default_model = get_default_model()

    return {"models": available_models, "default_model": default_model}


@router.get("/personality-presets")
async def get_personality_presets():
    return {
        "presets": {
            "helpful": {"style": "helpful", "tone": "friendly"},
            "professional": {"style": "expert", "tone": "professional"},
            "casual": {"style": "conversational", "tone": "casual"},
            "creative": {"style": "creative", "tone": "enthusiastic"},
            "concise": {"style": "concise", "tone": "direct"},
        }
    }
