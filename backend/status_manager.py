import asyncio
from typing import Dict, AsyncGenerator

_status_queues: Dict[str, asyncio.Queue] = {}


def _get_queue(session_id: str) -> asyncio.Queue:
    """Get or create a queue for the given session."""
    if session_id not in _status_queues:
        _status_queues[session_id] = asyncio.Queue()
    return _status_queues[session_id]


async def publish_status(session_id: str, message: str) -> None:
    """Publish a status message for the session."""
    queue = _get_queue(session_id)
    await queue.put(message)


async def status_events(session_id: str) -> AsyncGenerator[str, None]:
    """Yield status messages for streaming to the client."""
    queue = _get_queue(session_id)
    try:
        while True:
            message = await queue.get()
            yield message
    except asyncio.CancelledError:
        pass
    finally:
        _status_queues.pop(session_id, None)


def queue_status(session_id: str, message: str) -> None:
    """Schedule a status message without awaiting."""
    if not session_id:
        return
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    asyncio.create_task(publish_status(session_id, message))
