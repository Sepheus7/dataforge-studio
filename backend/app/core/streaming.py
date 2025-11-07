"""Server-Sent Events (SSE) utilities for real-time streaming"""

import asyncio
import json
from typing import AsyncGenerator, Any, Dict, Optional
from datetime import datetime


class StreamEvent:
    """Represents a Server-Sent Event"""

    def __init__(
        self,
        data: Any,
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None,
    ):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def encode(self) -> str:
        """Encode event in SSE format"""
        lines = []

        if self.id is not None:
            lines.append(f"id: {self.id}")

        if self.event is not None:
            lines.append(f"event: {self.event}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # Data can be multi-line
        data_str = json.dumps(self.data) if not isinstance(self.data, str) else self.data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        return "\n".join(lines) + "\n\n"


class EventStream:
    """Manages Server-Sent Event streams"""

    def __init__(self):
        self._subscribers: Dict[str, list[asyncio.Queue]] = {}

    async def subscribe(self, stream_id: str) -> AsyncGenerator[StreamEvent, None]:
        """
        Subscribe to a stream of events.

        Args:
            stream_id: Unique identifier for the stream

        Yields:
            StreamEvent objects as they are published
        """
        queue: asyncio.Queue = asyncio.Queue()

        # Add subscriber
        if stream_id not in self._subscribers:
            self._subscribers[stream_id] = []
        self._subscribers[stream_id].append(queue)

        try:
            # Send initial connection event
            yield StreamEvent(
                data={"status": "connected", "timestamp": datetime.utcnow().isoformat()},
                event="connect",
            )

            # Stream events from queue
            while True:
                event = await queue.get()
                if event is None:  # End of stream signal
                    break
                yield event

        finally:
            # Clean up subscriber
            if stream_id in self._subscribers:
                self._subscribers[stream_id].remove(queue)
                if not self._subscribers[stream_id]:
                    del self._subscribers[stream_id]

    async def publish(self, stream_id: str, event: StreamEvent) -> int:
        """
        Publish an event to all subscribers of a stream.

        Args:
            stream_id: Stream identifier
            event: Event to publish

        Returns:
            Number of subscribers that received the event
        """
        if stream_id not in self._subscribers:
            return 0

        count = 0
        for queue in self._subscribers[stream_id]:
            await queue.put(event)
            count += 1

        return count

    async def close_stream(self, stream_id: str) -> None:
        """
        Close a stream and notify all subscribers.

        Args:
            stream_id: Stream identifier
        """
        if stream_id not in self._subscribers:
            return

        # Send end-of-stream signal to all subscribers
        for queue in self._subscribers[stream_id]:
            await queue.put(None)

        # Clean up
        del self._subscribers[stream_id]

    def has_subscribers(self, stream_id: str) -> bool:
        """Check if a stream has any active subscribers"""
        return stream_id in self._subscribers and len(self._subscribers[stream_id]) > 0


# Global event stream instance
event_stream = EventStream()


async def create_sse_response(
    generator: AsyncGenerator[StreamEvent, None],
) -> AsyncGenerator[str, None]:
    """
    Convert StreamEvent generator to SSE formatted strings.

    Args:
        generator: Generator yielding StreamEvent objects

    Yields:
        SSE formatted strings
    """
    try:
        async for event in generator:
            yield event.encode()
    except asyncio.CancelledError:
        # Client disconnected
        pass
