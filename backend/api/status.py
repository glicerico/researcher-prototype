from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from status_manager import status_events

router = APIRouter()


@router.get("/status/{thread_id}")
async def status_stream(thread_id: str):
    async def event_generator():
        async for message in status_events(thread_id):
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
