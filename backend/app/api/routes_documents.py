"""API routes for document generation"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
import logging

from app.core.auth import verify_api_key
from app.models.requests import DocumentRequest
from app.models.responses import JobResponse, JobStatus
from app.services.jobs import get_job_manager
from app.services.generation.documents import get_document_service
from app.agents.document_agent import get_document_agent

router = APIRouter()
logger = logging.getLogger(__name__)


async def generate_document_task(job_id: str, request: DocumentRequest):
    """Background task for document generation"""
    job_manager = get_job_manager()
    doc_service = get_document_service()
    doc_agent = get_document_agent()

    try:
        job_manager.start_job(job_id)

        # Get document structure from agent if needed
        if request.template is None:
            structure = await doc_agent.generate_document_structure(
                document_type=request.document_type,
                requirements=request.data.get("requirements") if request.data else None,
            )

        # Generate document
        file_path = await doc_service.generate_invoice(
            job_id=job_id, data=request.data, format=request.format
        )

        # Mark job as complete
        job_manager.complete_job(
            job_id,
            {
                "document_type": request.document_type,
                "format": request.format,
                "file": str(file_path.name),
            },
        )

    except Exception as e:
        logger.error(f"Document job {job_id} failed: {e}", exc_info=True)
        job_manager.fail_job(job_id, str(e))


@router.post("/documents/generate", response_model=JobResponse)
async def generate_document(
    request: DocumentRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a synthetic document.

    Args:
        request: Document generation request
        api_key: API key for authentication

    Returns:
        Job response with job ID
    """
    try:
        # Create job
        job_manager = get_job_manager()
        job_id = job_manager.create_job()

        # Start generation in background
        background_tasks.add_task(generate_document_task, job_id, request)

        return JobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message=f"Document generation job created for {request.document_type}",
        )

    except Exception as e:
        logger.error(f"Failed to create document generation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{job_id}/download")
async def download_document(job_id: str, api_key: str = Depends(verify_api_key)):
    """
    Download generated document.

    Args:
        job_id: Job identifier
        api_key: API key for authentication

    Returns:
        File download response
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != JobStatus.SUCCEEDED:
        raise HTTPException(
            status_code=400, detail=f"Job is not complete. Current status: {job['status']}"
        )

    # Get file path from summary
    summary = job.get("summary", {})
    file_name = summary.get("file")

    if not file_name:
        raise HTTPException(status_code=404, detail="Document file not found in job summary")

    doc_service = get_document_service()
    file_path = doc_service.base_dir / job_id / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    return FileResponse(path=file_path, filename=file_name, media_type="application/octet-stream")
