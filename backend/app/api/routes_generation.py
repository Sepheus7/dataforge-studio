"""API routes for data generation"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
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
    """Background task for data generation (called after schema inference at 95%)"""
    logger.info(f"🔧 generate_data_task starting for job {job_id}")
    job_manager = get_job_manager()
    generator = get_structured_generator()

    try:
        # DON'T call start_job here - it would reset progress from 95% to 0%
        # The job is already started during schema inference
        
        logger.info(f"📊 Calling generator.generate_from_schema for job {job_id}")
        # Generate data
        summary = await generator.generate_from_schema(job_id, schema)

        logger.info(f"✅ Data generation complete for job {job_id}, completing job")
        # Mark job as complete
        job_manager.complete_job(job_id, summary)
        logger.info(f"✅ Job {job_id} marked as complete")

    except Exception as e:
        logger.error(f"❌ Job {job_id} failed: {e}", exc_info=True)
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
                # Create schema agent with job manager for progress tracking
                schema_agent = get_schema_agent()
                schema_agent.job_manager = job_manager

                # Infer schema with progress tracking and conversation memory
                schema = await schema_agent.infer_schema(
                    prompt=request.prompt,
                    size_hint=request.size_hint,
                    seed=request.seed,
                    job_id=job_id,
                    thread_id=request.thread_id
                )

                logger.info(
                    f"Job {job_id}: Schema inferred, starting generation",
                    exc_info=True
                )

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
            job_id=job_id, 
            status=JobStatus.QUEUED, 
            message="Job created - data generation starting"
        )

    except Exception as e:
        logger.error(f"Failed to create generation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generation/list")
async def list_jobs(api_key: str = Depends(verify_api_key)):
    """
    List all jobs by scanning artifacts directory.
    This discovers jobs that may not be in memory
    (e.g., after server restart).

    Args:
        api_key: API key for authentication

    Returns:
        List of job IDs with basic info
    """
    try:
        from pathlib import Path
        from app.core.config import settings, PROJECT_ROOT
        from datetime import datetime

        # Resolve artifacts directory path (may be relative or absolute)
        artifacts_path = settings.LOCAL_ARTIFACTS_DIR
        if not Path(artifacts_path).is_absolute():
            # If relative, resolve relative to project root
            artifacts_dir = PROJECT_ROOT / artifacts_path
        else:
            artifacts_dir = Path(artifacts_path)

        # Create directory if it doesn't exist
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        if not artifacts_dir.exists():
            logger.warning(f"Artifacts directory does not exist: {artifacts_dir}")
            return {"jobs": []}

        jobs = []
        job_manager = get_job_manager()

        # Scan artifacts directory for job folders
        try:
            job_dirs = list(artifacts_dir.iterdir())
        except Exception as e:
            logger.error(f"Failed to list artifacts directory: {e}")
            return {"jobs": []}

        for job_dir in job_dirs:
            if not job_dir.is_dir() or job_dir.name == "uploads":
                continue

            job_id = job_dir.name
            if not job_id.startswith("job_"):
                continue

            # Check if job has schema.json (indicates completed)
            schema_path = job_dir / "schema.json"
            if not schema_path.exists():
                continue

            # Try to get job from memory first
            job = job_manager.get_job(job_id)

            # If not in memory, reconstruct from artifacts
            if not job:
                # Find all CSV files (tables)
                csv_files = list(job_dir.glob("*.csv"))
                if not csv_files:
                    continue

                # Build table summaries
                tables = []
                total_rows = 0
                total_columns = 0

                for csv_file in csv_files:
                    table_name = csv_file.stem
                    if table_name == "schema":
                        continue

                    # Count rows (rough estimate - read first few lines)
                    try:
                        with open(csv_file, "r") as f:
                            lines = f.readlines()
                            rows = len(lines) - 1  # Subtract header
                            if rows < 0:
                                rows = 0

                            # Count columns from header
                            if lines:
                                columns = len(lines[0].strip().split(","))
                            else:
                                columns = 0
                    except Exception:
                        rows = 0
                        columns = 0

                    size_bytes = (
                        csv_file.stat().st_size if csv_file.exists() else 0
                    )
                    tables.append({
                        "name": table_name,
                        "rows": rows,
                        "columns": columns,
                        "size_bytes": size_bytes,
                    })
                    total_rows += rows
                    total_columns += columns

                # Get creation time from directory or schema file
                try:
                    created_at = datetime.fromtimestamp(
                        schema_path.stat().st_mtime
                    )
                except Exception:
                    created_at = datetime.utcnow()

                # Create job summary
                summary = {
                    "tables": tables,
                    "total_rows": total_rows,
                    "total_columns": total_columns,
                }

                # Use schema file mtime as completion time
                job = {
                    "job_id": job_id,
                    "status": JobStatus.SUCCEEDED,
                    "created_at": created_at,
                    "started_at": None,
                    "completed_at": created_at,
                    "progress": 1.0,
                    "message": "Job completed successfully",
                    "error": None,
                    "summary": summary,
                }

            # Convert to response format (rename summary -> result)
            job_response = dict(job)
            result_data = None
            if "summary" in job_response and job_response["summary"]:
                result_data = job_response["summary"]
                # Keep summary for model validation, but frontend uses result
                job_response["result"] = result_data

            # Validate and serialize using JobStatusResponse
            try:
                validated = JobStatusResponse(**job_response)
                serialized = validated.model_dump()
                # Add result field for frontend (not in model)
                if result_data:
                    serialized["result"] = result_data
                jobs.append(serialized)
            except Exception as e:
                logger.warning(f"Failed to validate job {job_id}: {e}")
                # Fallback: return as-is with result field
                if result_data:
                    job_response["result"] = result_data
                jobs.append(job_response)

        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        # Return empty list on error rather than failing
        return {"jobs": []}


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

    # Rename 'summary' to 'result' for frontend compatibility
    job_response = dict(job)
    if "summary" in job_response and job_response["summary"]:
        job_response["result"] = job_response["summary"]
    return JobStatusResponse(**job_response)


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
        raise HTTPException(
            status_code=404, 
            detail=f"Artifact not found: {table_name}.{format}"
        )

    return FileResponse(
        path=artifact_path,
        filename=f"{table_name}.{format}",
        media_type="application/octet-stream"
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
            status_code=400, 
            detail="Job cannot be cancelled (already completed or failed)"
        )

    return {"job_id": job_id, "status": "cancelled"}


@router.get("/list", tags=["generation"])
async def list_jobs(api_key: str = Depends(verify_api_key)):
    """
    List all jobs by scanning artifacts directory.
    This discovers jobs that may not be in memory
    (e.g., after server restart).

    Args:
        api_key: API key for authentication

    Returns:
        List of job IDs with basic info
    """
    try:
        from pathlib import Path
        from app.core.config import settings, PROJECT_ROOT
        from datetime import datetime

        # Resolve artifacts directory path (may be relative or absolute)
        artifacts_path = settings.LOCAL_ARTIFACTS_DIR
        if not Path(artifacts_path).is_absolute():
            # If relative, resolve relative to project root
            artifacts_dir = PROJECT_ROOT / artifacts_path
        else:
            artifacts_dir = Path(artifacts_path)

        # Create directory if it doesn't exist
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        if not artifacts_dir.exists():
            logger.warning(f"Artifacts directory does not exist: {artifacts_dir}")
            return {"jobs": []}

        jobs = []
        job_manager = get_job_manager()

        # Scan artifacts directory for job folders
        try:
            job_dirs = list(artifacts_dir.iterdir())
        except Exception as e:
            logger.error(f"Failed to list artifacts directory: {e}")
            return {"jobs": []}

        for job_dir in job_dirs:
            if not job_dir.is_dir() or job_dir.name == "uploads":
                continue

            job_id = job_dir.name
            if not job_id.startswith("job_"):
                continue

            # Check if job has schema.json (indicates completed)
            schema_path = job_dir / "schema.json"
            if not schema_path.exists():
                continue

            # Try to get job from memory first
            job = job_manager.get_job(job_id)

            # If not in memory, reconstruct from artifacts
            if not job:
                # Find all CSV files (tables)
                csv_files = list(job_dir.glob("*.csv"))
                if not csv_files:
                    continue

                # Build table summaries
                tables = []
                total_rows = 0
                total_columns = 0

                for csv_file in csv_files:
                    table_name = csv_file.stem
                    if table_name == "schema":
                        continue

                    # Count rows (rough estimate - read first few lines)
                    try:
                        with open(csv_file, "r") as f:
                            lines = f.readlines()
                            rows = len(lines) - 1  # Subtract header
                            if rows < 0:
                                rows = 0

                            # Count columns from header
                            if lines:
                                columns = len(lines[0].strip().split(","))
                            else:
                                columns = 0
                    except Exception:
                        rows = 0
                        columns = 0

                    size_bytes = (
                        csv_file.stat().st_size if csv_file.exists() else 0
                    )
                    tables.append({
                        "name": table_name,
                        "rows": rows,
                        "columns": columns,
                        "size_bytes": size_bytes,
                    })
                    total_rows += rows
                    total_columns += columns

                # Get creation time from directory or schema file
                try:
                    created_at = datetime.fromtimestamp(
                        schema_path.stat().st_mtime
                    )
                except Exception:
                    created_at = datetime.utcnow()

                # Create job summary
                summary = {
                    "tables": tables,
                    "total_rows": total_rows,
                    "total_columns": total_columns,
                }

                # Use schema file mtime as completion time
                job = {
                    "job_id": job_id,
                    "status": JobStatus.SUCCEEDED,
                    "created_at": created_at,
                    "started_at": None,
                    "completed_at": created_at,
                    "progress": 1.0,
                    "message": "Job completed successfully",
                    "error": None,
                    "summary": summary,
                }

            # Convert to response format (rename summary -> result)
            job_response = dict(job)
            result_data = None
            if "summary" in job_response and job_response["summary"]:
                result_data = job_response["summary"]
                # Keep summary for model validation, but frontend uses result
                job_response["result"] = result_data

            # Validate and serialize using JobStatusResponse
            try:
                validated = JobStatusResponse(**job_response)
                serialized = validated.model_dump()
                # Add result field for frontend (not in model)
                if result_data:
                    serialized["result"] = result_data
                jobs.append(serialized)
            except Exception as e:
                logger.warning(f"Failed to validate job {job_id}: {e}")
                # Fallback: return as-is with result field
                if result_data:
                    job_response["result"] = result_data
                jobs.append(job_response)

        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        # Return empty list on error rather than failing
        return {"jobs": []}


@router.post("/generation/cleanup")
async def cleanup_old_jobs(
    max_age_hours: int = 1,
    api_key: str = Depends(verify_api_key)
):
    """
    Clean up old completed jobs from memory.

    Args:
        max_age_hours: Maximum age in hours for jobs to keep (default: 1)
        api_key: API key for authentication

    Returns:
        Number of jobs removed
    """
    job_manager = get_job_manager()

    # Clean up jobs older than specified hours
    removed = job_manager.cleanup_old_jobs(
        max_age_seconds=max_age_hours * 3600
    )

    return {"message": f"Cleaned up {removed} old job(s)", "removed": removed}
