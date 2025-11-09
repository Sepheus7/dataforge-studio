"""Pydantic models for API requests"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    """Request for generating data from natural language prompt"""

    prompt: str = Field(..., description="Natural language description of desired data")
    size_hint: Optional[Dict[str, int]] = Field(
        default=None, description="Optional hints for number of rows per table"
    )
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible generation")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for conversation continuity")


class SchemaRequest(BaseModel):
    """Request for generating data from explicit schema"""

    schema: Dict[str, Any] = Field(..., description="Data schema definition")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible generation")


class DocumentRequest(BaseModel):
    """Request for generating synthetic documents"""

    document_type: str = Field(
        ..., description="Type of document (invoice, contract, report, etc.)"
    )
    template: Optional[str] = Field(default=None, description="Template name or custom template")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Data to populate document")
    count: int = Field(default=1, ge=1, le=1000, description="Number of documents to generate")
    format: str = Field(default="pdf", description="Output format (pdf, docx, json)")


class ReplicationRequest(BaseModel):
    """Request for replicating an existing dataset"""

    dataset_id: str = Field(..., description="ID of uploaded dataset")
    num_rows: int = Field(..., ge=1, description="Number of synthetic rows to generate")
    model_type: str = Field(
        default="gaussian_copula", description="Synthesizer model type (gaussian_copula, ctgan)"
    )
    replace_pii: bool = Field(default=True, description="Whether to detect and replace PII")
    preserve_relationships: bool = Field(
        default=True, description="Preserve foreign key relationships in multi-table datasets"
    )


class ReplicationConfig(BaseModel):
    """Configuration for dataset replication"""

    num_rows: int = Field(..., ge=1, description="Number of rows to generate")
    model_type: str = Field(default="gaussian_copula")
    replace_pii: bool = Field(default=True)
    preserve_relationships: bool = Field(default=True)
    quality_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum quality score (0-1)"
    )


class SchemaValidationRequest(BaseModel):
    """Request to validate a schema"""

    schema: Dict[str, Any] = Field(..., description="Schema to validate")


class TableSchema(BaseModel):
    """Schema definition for a single table"""

    name: str
    rows: int = Field(ge=1, le=1_000_000)
    primary_key: Optional[str] = None
    foreign_keys: Optional[List[Dict[str, str]]] = None
    columns: List[Dict[str, Any]]


class DataSchema(BaseModel):
    """Complete data schema definition"""

    seed: Optional[int] = None
    tables: List[TableSchema]
