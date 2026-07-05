import asyncio
import json
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class EventManager:
    def __init__(self):
        # Maps user_id str -> Set of asyncio.Queue
        self.listeners: Dict[str, Set[asyncio.Queue]] = {}

    def subscribe(self, user_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if user_id not in self.listeners:
            self.listeners[user_id] = set()
        self.listeners[user_id].add(queue)
        logger.info(
            f"User {user_id} subscribed to SSE events. Active connections: {len(self.listeners[user_id])}"
        )
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        if user_id in self.listeners:
            self.listeners[user_id].discard(queue)
            if not self.listeners[user_id]:
                del self.listeners[user_id]
            logger.info(f"User {user_id} unsubscribed from SSE events.")

    async def publish(self, user_id: str, event_type: str, data: dict):
        if user_id not in self.listeners:
            return

        # Format the event as a Server-Sent Event (SSE)
        # SSE syntax:
        # event: {event_type}\n
        # data: {json_data}\n\n
        event_str = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        # Notify all active SSE listeners for this user
        logger.info(
            f"Publishing event '{event_type}' to user {user_id} ({len(self.listeners[user_id])} listeners)"
        )
        for queue in list(self.listeners[user_id]):
            await queue.put(event_str)


event_manager = EventManager()
