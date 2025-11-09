"""API routes for dataset replication"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
import pandas as pd
import logging
import uuid
from pathlib import Path

from app.core.auth import verify_api_key
from app.core.config import settings
from app.models.requests import ReplicationConfig
from app.models.responses import JobResponse, DatasetProfile, JobStatus
from app.services.jobs import get_job_manager
from app.services.pii.detector import get_pii_detector
from app.services.pii.replacer import get_pii_replacer
from app.agents.replication_agent import get_replication_agent

# Lazy import SDV to avoid crashes during module import
def get_sdv_replicator():
    """Lazy import SDV to avoid crashes during module import"""
    try:
        from app.services.generation.sdv_wrapper import get_sdv_replicator as _get_sdv
        return _get_sdv()
    except (ImportError, SystemError, OSError, Exception):
        raise NotImplementedError("SDV temporarily disabled - use prompt-based generation instead")

router = APIRouter()
logger = logging.getLogger(__name__)

# Temporary storage for uploaded datasets
UPLOAD_DIR = Path(settings.LOCAL_ARTIFACTS_DIR) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def replicate_dataset_task(job_id: str, dataset_id: str, config: ReplicationConfig):
    """Background task for dataset replication"""
    job_manager = get_job_manager()
    sdv = get_sdv_replicator()

    try:
        job_manager.start_job(job_id)
        job_manager.update_progress(job_id, 0.1, "Loading dataset")

        # Load dataset
        dataset_path = UPLOAD_DIR / f"{dataset_id}.csv"
        df = pd.read_csv(dataset_path)

        # Detect and replace PII if requested
        if config.replace_pii:
            job_manager.update_progress(job_id, 0.2, "Detecting PII")
            detector = get_pii_detector()
            pii_map = detector.detect_in_dataframe(df)

            if pii_map:
                job_manager.update_progress(job_id, 0.3, "Replacing PII")
                replacer = get_pii_replacer()
                df = replacer.replace_in_dataframe(df, pii_map, strategy="fake")

        # Train model
        job_manager.update_progress(job_id, 0.4, f"Training {config.model_type} model")
        model_id = sdv.train_model(
            df=df, model_type=config.model_type, table_name="replicated_data"
        )

        # Generate synthetic data
        job_manager.update_progress(job_id, 0.7, "Generating synthetic data")
        synthetic_df = sdv.generate_synthetic(model_id, config.num_rows)

        # Evaluate quality
        job_manager.update_progress(job_id, 0.9, "Evaluating quality")
        quality = sdv.evaluate_quality(df, synthetic_df)

        # Save synthetic data
        output_path = Path(settings.LOCAL_ARTIFACTS_DIR) / job_id / "replicated_data.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        synthetic_df.to_csv(output_path, index=False)

        # Complete job
        job_manager.complete_job(
            job_id,
            {
                "original_rows": len(df),
                "generated_rows": len(synthetic_df),
                "quality_score": quality.get("overall_quality", 0),
                "model_type": config.model_type,
                "file": "replicated_data.csv",
            },
        )

    except Exception as e:
        logger.error(f"Replication job {job_id} failed: {e}", exc_info=True)
        job_manager.fail_job(job_id, str(e))


@router.post("/replication/upload")
async def upload_dataset(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """
    Upload a dataset for replication.

    Args:
        file: CSV file to upload
        api_key: API key for authentication

    Returns:
        Dataset ID for use in replication requests
    """
    try:
        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Generate dataset ID
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"

        # Save file
        file_path = UPLOAD_DIR / f"{dataset_id}.csv"
        content = await file.read()
        file_path.write_bytes(content)

        logger.info(f"Dataset uploaded: {dataset_id} ({file.filename})")

        return {"dataset_id": dataset_id, "filename": file.filename, "size_bytes": len(content)}

    except Exception as e:
        logger.error(f"Failed to upload dataset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replication/{dataset_id}/analyze", response_model=DatasetProfile)
async def analyze_dataset(dataset_id: str, api_key: str = Depends(verify_api_key)):
    """
    Analyze an uploaded dataset.

    Args:
        dataset_id: Dataset identifier from upload
        api_key: API key for authentication

    Returns:
        Dataset profile with structure and PII detection
    """
    try:
        # Load dataset
        dataset_path = UPLOAD_DIR / f"{dataset_id}.csv"
        if not dataset_path.exists():
            raise HTTPException(status_code=404, detail="Dataset not found")

        df = pd.read_csv(dataset_path)

        # Analyze with agent
        agent = get_replication_agent()
        analysis = await agent.analyze_dataset_structure(df, "uploaded_data")

        # Detect PII
        detector = get_pii_detector()
        pii_detected = detector.detect_in_dataframe(df)

        return DatasetProfile(
            dataset_id=dataset_id,
            num_tables=1,
            total_rows=len(df),
            total_columns=len(df.columns),
            tables=[analysis],
            detected_pii={"uploaded_data": list(pii_detected.keys())} if pii_detected else None,
        )

    except Exception as e:
        logger.error(f"Failed to analyze dataset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replication/{dataset_id}/replicate", response_model=JobResponse)
async def replicate_dataset(
    dataset_id: str,
    config: ReplicationConfig,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    """
    Replicate a dataset with synthetic data.

    Args:
        dataset_id: Dataset identifier from upload
        config: Replication configuration
        api_key: API key for authentication

    Returns:
        Job response with job ID
    """
    try:
        # Check if dataset exists
        dataset_path = UPLOAD_DIR / f"{dataset_id}.csv"
        if not dataset_path.exists():
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Create job
        job_manager = get_job_manager()
        job_id = job_manager.create_job()

        # Start replication in background
        background_tasks.add_task(replicate_dataset_task, job_id, dataset_id, config)

        return JobResponse(
            job_id=job_id, status=JobStatus.QUEUED, message="Dataset replication job created"
        )

    except Exception as e:
        logger.error(f"Failed to create replication job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
