"""API routes for Server-Sent Events (SSE) streaming"""

from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
import logging

from app.core.auth import verify_api_key
from app.core.streaming import event_stream, create_sse_response
from app.services.jobs import get_job_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/generation/{job_id}/stream")
async def stream_job_progress(job_id: str, api_key: str = Depends(verify_api_key)):
    """
    Stream real-time job progress updates via Server-Sent Events.

    Clients can connect to this endpoint to receive live updates about
    job status, progress, and messages.

    Args:
        job_id: Job identifier
        api_key: API key for authentication

    Returns:
        EventSourceResponse with SSE stream
    """
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
                yield event.encode()
        except Exception as e:
            logger.error(f"Error in SSE stream for job {job_id}: {e}", exc_info=True)

    return EventSourceResponse(event_generator())
