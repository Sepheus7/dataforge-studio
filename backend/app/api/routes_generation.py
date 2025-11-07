"""API routes for data generation"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import asyncio
import logging

from app.core.auth import verify_api_key
from app.models.requests import PromptRequest, SchemaRequest
from app.models.responses import JobResponse, JobStatusResponse, JobStatus
from app.services.jobs import get_job_manager
from app.services.generation.structured import get_structured_generator
from app.agents.schema_agent import get_schema_agent

router = APIRouter()
logger = logging.getLogger(__name__)


async def generate_data_task(job_id: str, schema: dict):
    """Background task for data generation"""
    job_manager = get_job_manager()
    generator = get_structured_generator()

    try:
        job_manager.start_job(job_id)

        # Generate data
        summary = await generator.generate_from_schema(job_id, schema)

        # Mark job as complete
        job_manager.complete_job(job_id, summary)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job_manager.fail_job(job_id, str(e))


@router.post("/generation/prompt", response_model=JobResponse)
async def generate_from_prompt(
    request: PromptRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate synthetic data from a natural language prompt.

    Uses the Schema Agent to infer a data schema from the prompt,
    then generates data matching that schema.

    Args:
        request: Prompt request with description and optional hints
        api_key: API key for authentication

    Returns:
        Job response with job ID for tracking
    """
    try:
        # Create job
        job_manager = get_job_manager()
        job_id = job_manager.create_job()

        # Infer schema using agent (in background)
        async def infer_and_generate():
            try:
                schema_agent = get_schema_agent()

                # Infer schema
                schema = await schema_agent.infer_schema(
                    prompt=request.prompt, size_hint=request.size_hint, seed=request.seed
                )

                logger.info(f"Job {job_id}: Schema inferred, starting generation")

                # Generate data
                await generate_data_task(job_id, schema)

            except Exception as e:
                logger.error(f"Job {job_id} failed during inference: {e}", exc_info=True)
                job_manager.fail_job(job_id, f"Schema inference failed: {str(e)}")

        # Start background task
        background_tasks.add_task(infer_and_generate)

        return JobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Job created - schema inference and generation starting",
        )

    except Exception as e:
        logger.error(f"Failed to create generation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generation/schema", response_model=JobResponse)
async def generate_from_schema(
    request: SchemaRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate synthetic data from an explicit schema definition.

    Args:
        request: Schema request with complete schema definition
        api_key: API key for authentication

    Returns:
        Job response with job ID for tracking
    """
    try:
        # Create job
        job_manager = get_job_manager()
        job_id = job_manager.create_job()

        # Start generation in background
        background_tasks.add_task(generate_data_task, job_id, request.schema)

        return JobResponse(
            job_id=job_id, status=JobStatus.QUEUED, message="Job created - data generation starting"
        )

    except Exception as e:
        logger.error(f"Failed to create generation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generation/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, api_key: str = Depends(verify_api_key)):
    """
    Get the status of a generation job.

    Args:
        job_id: Job identifier
        api_key: API key for authentication

    Returns:
        Job status with progress and details
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(**job)


@router.get("/generation/{job_id}/download")
async def download_artifacts(
    job_id: str,
    table_name: str = "data",
    format: str = "csv",
    api_key: str = Depends(verify_api_key),
):
    """
    Download generated artifacts.

    Args:
        job_id: Job identifier
        table_name: Name of the table to download
        format: File format (csv, json)
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

    # Get artifact path
    generator = get_structured_generator()
    artifact_path = generator.get_artifact_path(job_id, table_name, format)

    if not artifact_path or not artifact_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {table_name}.{format}")

    return FileResponse(
        path=artifact_path, filename=f"{table_name}.{format}", media_type="application/octet-stream"
    )


@router.delete("/generation/{job_id}")
async def cancel_job(job_id: str, api_key: str = Depends(verify_api_key)):
    """
    Cancel a running job.

    Args:
        job_id: Job identifier
        api_key: API key for authentication

    Returns:
        Cancellation status
    """
    job_manager = get_job_manager()

    if not job_manager.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    cancelled = job_manager.cancel_job(job_id)

    if not cancelled:
        raise HTTPException(
            status_code=400, detail="Job cannot be cancelled (already completed or failed)"
        )

    return {"job_id": job_id, "status": "cancelled"}
