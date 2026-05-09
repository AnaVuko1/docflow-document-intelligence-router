"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, validator, ConfigDict


# ===== Base Schemas =====
class BaseSchema(BaseModel):
    """Base schema with common configurations."""
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ===== Pipeline Schemas =====
class PipelineBase(BaseSchema):
    """Base pipeline schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    definition: Dict[str, Any] = Field(..., description="YAML pipeline definition as JSON")
    is_active: bool = Field(default=True, description="Whether pipeline is active")


class PipelineCreate(PipelineBase):
    """Schema for creating a pipeline."""
    pass


class PipelineUpdate(BaseSchema):
    """Schema for updating a pipeline."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Pipeline(PipelineBase):
    """Pipeline response schema."""
    id: int
    version: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ===== Document Schemas =====
class DocumentBase(BaseSchema):
    """Base document schema."""
    filename: str = Field(..., min_length=1, max_length=255)
    original_filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., description="Path to uploaded file")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: Optional[str] = None


class DocumentCreate(BaseSchema):
    """Schema for creating a document (upload)."""
    content: Optional[str] = Field(None, description="Direct text content (alternative to file upload)")


class Document(DocumentBase):
    """Document response schema."""
    id: int
    content: Optional[str] = None
    document_type: Optional[str] = None
    classification_confidence: Optional[float] = Field(None, ge=0, le=1)
    status: str
    error_message: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class DocumentUploadResponse(BaseSchema):
    """Response for document upload."""
    document: Document
    upload_url: Optional[str] = Field(None, description="URL for direct upload (if supported)")


# ===== Job Schemas =====
class JobBase(BaseSchema):
    """Base job schema."""
    pipeline_id: int
    document_id: int


class JobCreate(JobBase):
    """Schema for creating a job."""
    pass


class Job(JobBase):
    """Job response schema."""
    id: int
    status: str
    current_step: Optional[str] = None
    progress: int = Field(..., ge=0, le=100)
    extracted_data: Optional[Dict[str, Any]] = None
    validated_data: Optional[Dict[str, Any]] = None
    transformed_data: Optional[Dict[str, Any]] = None
    output_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Relationships (optional)
    pipeline: Optional[Pipeline] = None
    document: Optional[Document] = None


class JobRunRequest(BaseSchema):
    """Request to run a pipeline job."""
    document_id: Optional[int] = Field(None, description="Existing document ID")
    content: Optional[str] = Field(None, description="Direct text content")
    pipeline_id: Optional[int] = Field(None, description="Pipeline ID (if not in URL)")


# ===== Extraction Result Schemas =====
class ExtractionResultBase(BaseSchema):
    """Base extraction result schema."""
    step_type: str
    step_name: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ExtractionResult(ExtractionResultBase):
    """Extraction result response schema."""
    id: int
    job_id: int
    created_at: datetime


# ===== Connector Schemas =====
class ConnectorConfig(BaseSchema):
    """Connector configuration schema."""
    type: str = Field(..., description="Connector type: csv, json, sqlite, webhook")
    config: Dict[str, Any] = Field(default_factory=dict)


class ConnectorLogBase(BaseSchema):
    """Base connector log schema."""
    connector_type: str
    connector_config: Dict[str, Any]
    success: bool
    output_path: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None


class ConnectorLog(ConnectorLogBase):
    """Connector log response schema."""
    id: int
    job_id: int
    executed_at: datetime


# ===== Classification Schemas =====
class ClassificationRequest(BaseSchema):
    """Request for document classification."""
    content: str = Field(..., description="Document text content")
    candidate_types: Optional[List[str]] = Field(
        None,
        description="Optional list of candidate document types"
    )


class ClassificationResult(BaseSchema):
    """Classification result."""
    document_type: str
    confidence: float = Field(..., ge=0, le=1)
    detected_keywords: List[str] = Field(default_factory=list)
    alternative_types: List[Dict[str, Any]] = Field(default_factory=list)


# ===== Extraction Schemas =====
class FieldExtractionConfig(BaseSchema):
    """Field extraction configuration."""
    name: str
    pattern: Optional[str] = None  # For regex extraction
    extractor: Optional[str] = None  # For template/LLM extraction
    description: Optional[str] = None
    required: bool = True


class ExtractionRequest(BaseSchema):
    """Request for field extraction."""
    content: str
    fields: List[FieldExtractionConfig]
    strategy: str = Field("regex", description="Extraction strategy: regex, template, llm")


class ExtractionResponse(BaseSchema):
    """Response from field extraction."""
    fields: Dict[str, Any] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    raw_matches: Dict[str, List[str]] = Field(default_factory=dict)
    errors: Dict[str, str] = Field(default_factory=dict)


# ===== Validation Schemas =====
class ValidationRule(BaseSchema):
    """Validation rule definition."""
    field: str
    rule: str  # Python expression or function name
    message: Optional[str] = None
    severity: str = Field("error", description="error, warning, info")


class ValidationRequest(BaseSchema):
    """Request for data validation."""
    data: Dict[str, Any]
    rules: List[ValidationRule]


class ValidationResult(BaseSchema):
    """Validation result."""
    valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


# ===== Transformation Schemas =====
class FieldMapping(BaseSchema):
    """Field mapping for transformation."""
    source: str
    target: str
    transform: Optional[str] = None  # Transformation function name


class FormatConversion(BaseSchema):
    """Format conversion specification."""
    field: str
    format: str  # date, float, integer, boolean, etc.
    params: Optional[Dict[str, Any]] = None


class TransformationRequest(BaseSchema):
    """Request for data transformation."""
    data: Dict[str, Any]
    mappings: Optional[Dict[str, str]] = None  # Simple field renaming
    field_mappings: Optional[List[FieldMapping]] = None  # Complex mappings
    formats: Optional[List[FormatConversion]] = None


class TransformationResponse(BaseSchema):
    """Transformation response."""
    transformed_data: Dict[str, Any]
    applied_transformations: List[Dict[str, Any]] = Field(default_factory=list)
    errors: Dict[str, str] = Field(default_factory=dict)


# ===== Dashboard Schemas =====
class DashboardStats(BaseSchema):
    """Dashboard statistics."""
    total_pipelines: int
    active_pipelines: int
    total_documents: int
    total_jobs: int
    jobs_by_status: Dict[str, int]
    success_rate: float = Field(..., ge=0, le=1)
    average_processing_time_ms: Optional[float] = None
    recent_jobs: List[Job] = Field(default_factory=list)
    top_pipelines: List[Dict[str, Any]] = Field(default_factory=list)


class PipelineStats(BaseSchema):
    """Pipeline-specific statistics."""
    pipeline_id: int
    pipeline_name: str
    total_jobs: int
    success_count: int
    failure_count: int
    average_processing_time_ms: Optional[float] = None
    last_execution: Optional[datetime] = None


# ===== Error Schemas =====
class ErrorResponse(BaseSchema):
    """Standard error response."""
    error: str
    details: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


# ===== API Response Schemas =====
class PaginatedResponse(BaseSchema):
    """Base paginated response."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class SuccessResponse(BaseSchema):
    """Standard success response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None