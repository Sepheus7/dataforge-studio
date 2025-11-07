"""Pydantic models for API responses"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Job execution status"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResponse(BaseModel):
    """Response for job creation"""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: Optional[str] = Field(default=None, description="Status message")


class TableSummary(BaseModel):
    """Summary of a generated table"""

    name: str
    rows: int
    columns: int
    size_bytes: Optional[int] = None


class JobStatusResponse(BaseModel):
    """Detailed job status response"""

    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress (0-1)")
    message: Optional[str] = None
    error: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    tables: Optional[List[TableSummary]] = None


class DatasetProfile(BaseModel):
    """Profile of an uploaded dataset"""

    dataset_id: str
    num_tables: int
    total_rows: int
    total_columns: int
    tables: List[Dict[str, Any]]
    detected_pii: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Detected PII by table and column"
    )
    relationships: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Detected foreign key relationships"
    )


class SchemaValidationResponse(BaseModel):
    """Response for schema validation"""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    normalized_schema: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Optional[Dict[str, str]] = None


class ErrorResponse(BaseModel):
    """Error response"""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
