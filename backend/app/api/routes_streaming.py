"""API routes for Server-Sent Events (SSE) streaming"""

from fastapi import APIRouter, HTTPException, Depends, Query, Security
from fastapi.security import APIKeyHeader
from sse_starlette.sse import EventSourceResponse
from typing import Optional
import logging
import json

from app.core.auth import api_key_header
from app.core.streaming import event_stream, create_sse_response
from app.services.jobs import get_job_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/generation/{job_id}/stream")
async def stream_job_progress(
    job_id: str,
    key: Optional[str] = Query(None, description="API key (since EventSource can't send headers)"),
    api_key_header: Optional[str] = Security(api_key_header)
):
    """
    Stream real-time job progress updates via Server-Sent Events.

    Clients can connect to this endpoint to receive live updates about
    job status, progress, and messages.
    
    Note: Since EventSource doesn't support custom headers, pass the API key
    as a query parameter: ?key=your-api-key

    Args:
        job_id: Job identifier
        key: API key via query parameter

    Returns:
        EventSourceResponse with SSE stream
    """
    # Verify API key (accepts either header or query param)
    from app.core.config import settings
    api_key = api_key_header or key
    
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=403 if api_key else 401,
            detail="Invalid or missing API key"
        )
    
    job_manager = get_job_manager()

    # Check if job exists
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info(f"Client connected to stream for job {job_id}")

    # Subscribe to events
    async def event_generator():
        try:
            async for event in event_stream.subscribe(job_id):
                # Build SSE message dict for EventSourceResponse
                # EventSourceResponse expects dict with specific keys
                message = {}
                
                if event.event:
                    message["event"] = event.event
                
                # Data must be a string
                if isinstance(event.data, str):
                    message["data"] = event.data
                else:
                    message["data"] = json.dumps(event.data)
                
                if event.id:
                    message["id"] = event.id
                    
                if event.retry:
                    message["retry"] = event.retry
                
                yield message
        except Exception as e:
            logger.error(f"Error in SSE stream for job {job_id}: {e}", exc_info=True)

    return EventSourceResponse(event_generator())
