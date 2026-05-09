"""
SQLAlchemy database models for DocFlow.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Pipeline(Base):
    """Pipeline definition model."""
    
    __tablename__ = "pipelines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False)  # YAML pipeline definition as JSON
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    jobs = relationship("Job", back_populates="pipeline", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Pipeline(id={self.id}, name='{self.name}')>"


class Document(Base):
    """Document model for uploaded files."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=True)
    
    # Content fields
    content = Column(Text, nullable=True)  # Extracted text content
    document_type = Column(String(100), nullable=True)  # Classified type
    classification_confidence = Column(Float, nullable=True)  # 0-1
    
    # Status
    status = Column(String(50), default="uploaded", nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    jobs = relationship("Job", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}')>"


class Job(Base):
    """Processing job model."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Status tracking
    status = Column(String(50), default="pending", nullable=False)
    current_step = Column(String(100), nullable=True)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    
    # Results
    extracted_data = Column(JSON, nullable=True)  # Raw extracted data
    validated_data = Column(JSON, nullable=True)  # Validated data
    transformed_data = Column(JSON, nullable=True)  # Transformed data
    output_results = Column(JSON, nullable=True)  # Connector results
    
    # Errors
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    pipeline = relationship("Pipeline", back_populates="jobs")
    document = relationship("Document", back_populates="jobs")
    
    def __repr__(self) -> str:
        return f"<Job(id={self.id}, status='{self.status}', pipeline_id={self.pipeline_id})>"


class ExtractionResult(Base):
    """Detailed extraction results for audit trail."""
    
    __tablename__ = "extraction_results"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    # Step information
    step_type = Column(String(50), nullable=False)  # classify, extract, validate, transform, route
    step_name = Column(String(100), nullable=True)
    
    # Input/output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Metrics
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    
    # Errors
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    job = relationship("Job", foreign_keys=[job_id])
    
    def __repr__(self) -> str:
        return f"<ExtractionResult(id={self.id}, step_type='{self.step_type}', success={self.success})>"


class ConnectorLog(Base):
    """Connector execution logs."""
    
    __tablename__ = "connector_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    connector_type = Column(String(50), nullable=False)  # csv, json, sqlite, webhook
    connector_config = Column(JSON, nullable=False)
    
    # Execution
    success = Column(Boolean, default=True, nullable=False)
    output_path = Column(String(512), nullable=True)  # File path or URL
    response_data = Column(JSON, nullable=True)
    
    # Errors
    error_message = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Timing
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    job = relationship("Job", foreign_keys=[job_id])
    
    def __repr__(self) -> str:
        return f"<ConnectorLog(id={self.id}, connector_type='{self.connector_type}', success={self.success})>"