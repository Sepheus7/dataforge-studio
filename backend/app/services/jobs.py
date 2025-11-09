"""Job management service for tracking generation tasks"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import asyncio
import uuid

from app.models.responses import JobStatus
from app.core.streaming import event_stream, StreamEvent


class JobManager:
    """Manages generation jobs and their lifecycle"""

    def __init__(self):
        """Initialize job manager"""
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._job_tasks: Dict[str, asyncio.Task] = {}

    def create_job(self) -> str:
        """
        Create a new job and return its ID.

        Returns:
            Job ID
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        self._jobs[job_id] = {
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "progress": 0.0,
            "message": "Job queued",
            "error": None,
            "summary": None,
        }

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job details or None if not found
        """
        return self._jobs.get(job_id)

    def start_job(self, job_id: str) -> None:
        """
        Mark a job as started.

        Args:
            job_id: Job identifier
        """
        if job_id in self._jobs:
            self._jobs[job_id].update(
                {
                    "status": JobStatus.RUNNING,
                    "started_at": datetime.utcnow(),
                    "message": "Job started",
                }
            )

            # Publish event
            asyncio.create_task(self._publish_update(job_id))

    def update_progress(self, job_id: str, progress: float, message: Optional[str] = None) -> None:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            progress: Progress value (0-1)
            message: Optional status message
        """
        if job_id in self._jobs:
            self._jobs[job_id]["progress"] = min(1.0, max(0.0, progress))
            if message:
                self._jobs[job_id]["message"] = message

            # Publish event
            asyncio.create_task(self._publish_update(job_id))

    def complete_job(self, job_id: str, summary: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark a job as successfully completed.

        Args:
            job_id: Job identifier
            summary: Optional job summary
        """
        if job_id in self._jobs:
            self._jobs[job_id].update(
                {
                    "status": JobStatus.SUCCEEDED,
                    "completed_at": datetime.utcnow(),
                    "progress": 1.0,
                    "message": "Job completed successfully",
                    "summary": summary,
                }
            )

            # Publish event and close stream
            asyncio.create_task(self._publish_update(job_id, final=True))

    def fail_job(self, job_id: str, error: str) -> None:
        """
        Mark a job as failed.

        Args:
            job_id: Job identifier
            error: Error message
        """
        if job_id in self._jobs:
            self._jobs[job_id].update(
                {
                    "status": JobStatus.FAILED,
                    "completed_at": datetime.utcnow(),
                    "message": "Job failed",
                    "error": error,
                }
            )

            # Publish event and close stream
            asyncio.create_task(self._publish_update(job_id, final=True))

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False otherwise
        """
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]
        if job["status"] in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        # Cancel task if running
        if job_id in self._job_tasks:
            task = self._job_tasks[job_id]
            if not task.done():
                task.cancel()
            del self._job_tasks[job_id]

        # Update status
        self._jobs[job_id].update(
            {
                "status": JobStatus.CANCELLED,
                "completed_at": datetime.utcnow(),
                "message": "Job cancelled",
            }
        )

        # Publish event and close stream
        asyncio.create_task(self._publish_update(job_id, final=True))

        return True

    def register_task(self, job_id: str, task: asyncio.Task) -> None:
        """
        Register an asyncio task for a job.

        Args:
            job_id: Job identifier
            task: Asyncio task
        """
        self._job_tasks[job_id] = task

    async def _publish_update(self, job_id: str, final: bool = False) -> None:
        """
        Publish job update to event stream.

        Args:
            job_id: Job identifier
            final: Whether this is the final update
        """
        import logging
        logger = logging.getLogger(__name__)
        
        job = self._jobs.get(job_id)
        if not job:
            return

        has_subs = event_stream.has_subscribers(job_id)
        logger.info(f"📡 Publishing update for {job_id}: progress={job['progress']:.0%}, has_subscribers={has_subs}")
        
        event_data = {
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Include result in final update (rename summary -> result for frontend)
        if final and job.get("summary"):
            event_data["result"] = job["summary"]
        
        # Include error if present
        if job.get("error"):
            event_data["error"] = job["error"]
        
        event = StreamEvent(
            data=event_data,
            event="progress",
        )

        sub_count = await event_stream.publish(job_id, event)
        logger.info(f"📨 Event sent to {sub_count} subscribers (result={'Yes' if event_data.get('result') else 'No'})")

        if final:
            await event_stream.close_stream(job_id)

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> int:
        """
        Remove completed jobs older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of jobs removed
        """
        now = datetime.utcnow()
        to_remove = []

        for job_id, job in self._jobs.items():
            completed_at = job.get("completed_at")
            if completed_at and (now - completed_at).total_seconds() > max_age_seconds:
                to_remove.append(job_id)

        for job_id in to_remove:
            del self._jobs[job_id]
            if job_id in self._job_tasks:
                del self._job_tasks[job_id]

        return len(to_remove)


# Global job manager instance
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get or create the global job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
