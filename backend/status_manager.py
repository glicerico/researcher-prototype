import asyncio
from typing import Dict, AsyncGenerator
import time

_status_queues: Dict[str, asyncio.Queue] = {}
_last_status_time: Dict[str, float] = {}
_MIN_STATUS_INTERVAL = 0.3  # Minimum 300ms between status updates


def _get_queue(session_id: str) -> asyncio.Queue:
    """Get or create a queue for the given session."""
    if session_id not in _status_queues:
        _status_queues[session_id] = asyncio.Queue()
    return _status_queues[session_id]


async def publish_status(session_id: str, message: str) -> None:
    """Publish a status message for the session with throttling."""
    queue = _get_queue(session_id)
    
    # Add throttling to prevent status updates from being too rapid
    current_time = time.time()
    last_time = _last_status_time.get(session_id, 0)
    
    if current_time - last_time < _MIN_STATUS_INTERVAL:
        # Wait a bit to space out the status updates
        await asyncio.sleep(_MIN_STATUS_INTERVAL - (current_time - last_time))
    
    _last_status_time[session_id] = time.time()
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
        _last_status_time.pop(session_id, None)


def queue_status(session_id: str, message: str) -> None:
    """Schedule a status message without awaiting."""
    if not session_id:
        return
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    asyncio.create_task(publish_status(session_id, message))
